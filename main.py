# ============================================================
#  ANDREW INVESTMENT SYSTEM — FastAPI Backend v3
#  동적 유니버스: S&P500 + NASDAQ100 + KOSPI200 + KOSDAQ150
# ============================================================
import os, httpx, asyncio, re, json
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

DART_API_KEY       = os.getenv("DART_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS  = [c.strip() for c in os.getenv("TELEGRAM_CHAT_IDS","").split(",") if c.strip()]
FMP_API_KEY        = os.getenv("FMP_API_KEY", "XZkyTZ3vW722F2zQTQx5454PtPGLx82o")
FMP_BASE           = "https://financialmodelingprep.com/api/v3"
TD_API_KEY         = os.getenv("Twelve_Data", os.getenv("TD_API_KEY", ""))  # Twelve Data
TD_BASE            = "https://api.twelvedata.com"

app = FastAPI(title="Andrew Investment System", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"],
)

# ── 유틸 ─────────────────────────────────────────────────────
def kst_now():
    return datetime.now(timezone.utc) + timedelta(hours=9)

def is_market_hours():
    now = kst_now()
    wd  = now.weekday()          # 0=Mon 6=Sun
    hm  = now.hour * 60 + now.minute
    kr  = wd < 5 and (9*60 <= hm <= 15*60+30)
    us  = wd < 5 and (hm >= 22*60 or hm < 5*60)
    return {"kr": kr, "us": us, "kst": now.strftime("%H:%M KST %m/%d")}

# ── 스크리너 진행 상태 ────────────────────────────────────────
_progress = {
    "kr": {"total": 0, "done": 0, "running": False, "phase": ""},
    "us": {"total": 0, "done": 0, "running": False, "phase": ""},
}
_screener_cache = {
    "kr": {"data": [], "updated": None},
    "us": {"data": [], "updated": None},
}

# ── Yahoo Finance 헬퍼 ────────────────────────────────────────
YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# FMP ticker 변환 (국장 .KS/.KQ 제거)
def to_fmp_ticker(ticker: str) -> str:
    """005930.KS → 005930.KS 그대로 (FMP는 KRX 지원), 미장은 그대로"""
    return ticker

async def td_fundamentals(ticker: str, client: httpx.AsyncClient) -> dict:
    """Twelve Data — PBR/PER/PEG/ROE 등 (국장/미장 모두 지원, 하루 800콜 무료)"""
    if not TD_API_KEY:
        return {}
    # 국장 티커 변환: 005930.KS → 005930:KRX
    if ticker.endswith(".KS"):
        td_ticker = ticker.replace(".KS", "") + ":KRX"
    elif ticker.endswith(".KQ"):
        td_ticker = ticker.replace(".KQ", "") + ":KOSDAQ"
    else:
        td_ticker = ticker

    result = {}
    try:
        url = f"{TD_BASE}/statistics?symbol={td_ticker}&apikey={TD_API_KEY}"
        r   = await client.get(url, timeout=10)
        d   = r.json()
        if d.get("status") == "error":
            return {"_td_error": d.get("message", "unknown")}
        val = d.get("valuations", {})
        fin = d.get("financials", {})
        inc = fin.get("income_statement", {})
        bal = fin.get("balance_sheet", {})
        cfl = fin.get("cash_flow", {})

        def n(v):
            try: return float(v) if v not in (None, "", "N/A", "-") else None
            except: return None

        result = {
            "priceToBook":      n(val.get("price_to_book_mrq")),
            "trailingPE":       n(val.get("pe_ratio_ttm")) or n(val.get("p_e_ratio")),
            "forwardPE":        n(val.get("forward_pe")),
            "pegRatio":         n(val.get("peg_ratio")),
            "returnOnEquity":   n(fin.get("statistics", {}).get("return_on_equity_ttm")),
            "returnOnAssets":   n(fin.get("statistics", {}).get("return_on_assets_ttm")),
            "grossMargins":     n(inc.get("gross_profit_margin_ttm")),
            "operatingMargins": n(inc.get("operating_margin_ttm")),
            "dividendYield":    n(val.get("dividend_yield")),
            "trailingAnnualDividendYield": n(val.get("dividend_yield")),
            "marketCap":        n(val.get("market_capitalization")),
            "beta":             n(val.get("beta")),
            "debtToEquity":     n(bal.get("total_debt_to_equity_mrq")),
            "currentRatio":     n(bal.get("current_ratio_mrq")),
            "revenueGrowth":    n(inc.get("quarterly_revenue_growth_yoy")),
            "earningsGrowth":   n(inc.get("quarterly_earnings_growth_yoy")),
            "freeCashflow":     n(cfl.get("levered_free_cash_flow_ttm")),
        }
    except Exception as e:
        result["_td_error"] = str(e)
    return result

def yf_get_fundamentals(ticker: str) -> dict:
    """yfinance 라이브러리 — 재무지표 (국장/미장 모두 지원)"""
    try:
        import yfinance as yf
        import math
        t    = yf.Ticker(ticker)
        info = t.info or {}
        is_kr = ticker.endswith(".KS") or ticker.endswith(".KQ")

        def g(*keys):
            """여러 후보 키 중 첫 번째 유효한 값 반환"""
            for k in keys:
                v = info.get(k)
                if v is None: continue
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)): continue
                if isinstance(v, (int, float)): return float(v)
            return None

        def pct(*keys):
            v = g(*keys)
            if v is None: return None
            return v / 100.0 if v > 1.0 else v  # 100 단위 → 소수 정규화

        price = g("currentPrice", "regularMarketPrice", "previousClose")

        # ── PBR ────────────────────────────────────────────────
        pbr = g("priceToBook")
        if pbr is None or pbr <= 0:
            bv = g("bookValue")
            if bv and bv > 0 and price and price > 0:
                pbr = round(price / bv, 3)
        # 국장 fallback: balance sheet에서 총자본 직접 계산
        if (pbr is None or pbr <= 0) and is_kr:
            try:
                shares = g("sharesOutstanding")
                bs = t.quarterly_balance_sheet
                if bs is not None and not bs.empty:
                    equity_row = None
                    for row_key in ["Stockholders Equity", "Total Equity Gross Minority Interest",
                                    "Common Stock Equity", "Total Stockholders Equity"]:
                        if row_key in bs.index:
                            equity_row = float(bs.loc[row_key].iloc[0])
                            break
                    if equity_row and equity_row > 0 and shares and shares > 0:
                        bv_per_share = equity_row / shares
                        if bv_per_share > 0 and price and price > 0:
                            pbr = round(price / bv_per_share, 3)
            except: pass
        if pbr is not None and pbr <= 0: pbr = None
        # 국장 fallback: balance sheet에서 총자본 직접 계산
        if (pbr is None or pbr <= 0) and is_kr:
            try:
                shares = g("sharesOutstanding")
                bs = t.quarterly_balance_sheet
                if bs is not None and not bs.empty:
                    equity_row = None
                    for row_key in ["Stockholders Equity","Total Equity Gross Minority Interest",
                                    "Common Stock Equity","Total Stockholders Equity"]:
                        if row_key in bs.index:
                            equity_row = float(bs.loc[row_key].iloc[0])
                            break
                    if equity_row and equity_row > 0 and shares and shares > 0:
                        bv_per_share = equity_row / shares
                        if bv_per_share > 0 and price and price > 0:
                            pbr = round(price / bv_per_share, 3)
            except: pass

        # ── PER ────────────────────────────────────────────────
        pe = g("trailingPE")
        if pe is None or pe <= 0 or pe > 2000:
            eps = g("trailingEps", "epsTrailingTwelveMonths")
            if eps and eps > 0 and price and price > 0:
                pe = round(price / eps, 2)
        # 국장 fallback: income statement TTM 합산으로 EPS 직접 계산
        if (pe is None or pe <= 0 or pe > 2000) and is_kr:
            try:
                shares = g("sharesOutstanding")
                inc = t.quarterly_income_stmt
                if inc is not None and not inc.empty:
                    net_income = None
                    for row_key in ["Net Income", "Net Income Common Stockholders",
                                    "Net Income From Continuing Operations"]:
                        if row_key in inc.index:
                            vals = [float(v) for v in inc.loc[row_key].dropna().values[:4]]
                            if vals:
                                net_income = sum(vals)
                                break
                    if net_income and net_income > 0 and shares and shares > 0:
                        eps_calc = net_income / shares
                        if eps_calc > 0 and price and price > 0:
                            pe = round(price / eps_calc, 2)
            except: pass
        if pe is not None and (pe <= 0 or pe > 2000): pe = None
        # 국장 fallback: income statement TTM 합산으로 EPS 직접 계산
        if (pe is None or pe <= 0 or pe > 2000) and is_kr:
            try:
                shares = g("sharesOutstanding")
                inc = t.quarterly_income_stmt
                if inc is not None and not inc.empty:
                    net_income = None
                    for row_key in ["Net Income","Net Income Common Stockholders",
                                    "Net Income From Continuing Operations"]:
                        if row_key in inc.index:
                            vals = [float(v) for v in inc.loc[row_key].dropna().values[:4]]
                            if vals:
                                net_income = sum(vals)
                                break
                    if net_income and net_income > 0 and shares and shares > 0:
                        eps_calc = net_income / shares
                        if eps_calc > 0 and price and price > 0:
                            pe = round(price / eps_calc, 2)
            except: pass

        # ── PEG ────────────────────────────────────────────────
        peg = g("pegRatio", "trailingPegRatio")
        # 국장: PEG가 없으면 PE / 이익성장률로 근사
        if peg is None and pe is not None:
            eg = g("earningsGrowth")
            if eg and eg > 0.01:
                peg = round(pe / (eg * 100), 3)

        # ── 배당 ───────────────────────────────────────────────
        div = pct("trailingAnnualDividendYield", "dividendYield")
        if div is None:
            dr = g("trailingAnnualDividendRate", "dividendRate")
            if dr and price and price > 0:
                div = dr / price

        # ── 부채비율 국장 스케일 보정 ───────────────────────────
        de = g("debtToEquity")
        # yfinance 국장 종목은 debtToEquity가 이미 % 단위 (예: 45 = 45%)
        # 미장은 소수 단위 (예: 1.02 = 102%)
        # → 100 초과면 이미 % 단위, 그대로 사용
        # → 10 이하면 소수 단위, ×100 해서 %로

        return {
            "priceToBook":    pbr,
            "trailingPE":     pe,
            "forwardPE":      g("forwardPE"),
            "pegRatio":       peg,
            "returnOnEquity": g("returnOnEquity"),
            "returnOnAssets": g("returnOnAssets"),
            "grossMargins":   g("grossMargins"),
            "operatingMargins": g("operatingMargins"),
            "freeCashflow":   g("freeCashflow"),
            "operatingCashflow": g("operatingCashflow"),
            "trailingAnnualDividendYield": div,
            "dividendYield":  div,
            "marketCap":      g("marketCap"),
            "beta":           g("beta"),
            "debtToEquity":   de,
            "currentRatio":   g("currentRatio"),
            "revenueGrowth":  g("revenueGrowth"),
            "earningsGrowth": g("earningsGrowth"),
            "shortRatio":     g("shortRatio"),
        }
    except Exception as e:
        return {"_yf_error": str(e)}

async def get_fundamentals_async(ticker: str) -> dict:
    """yfinance 동기 함수를 비동기로 실행"""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=4) as pool:
        return await loop.run_in_executor(pool, yf_get_fundamentals, ticker)

def _raw(d, k):
    v = d.get(k, {})
    if isinstance(v, dict): return v.get("raw")
    if isinstance(v, (int, float)): return v
    return None

async def yf_single_quote(ticker: str, client: httpx.AsyncClient) -> dict:
    """Yahoo Finance — v8 chart (가격+히스토리+기본지표) + v10 quoteSummary (심화지표)"""
    errors = []

    # ── 1) v8 chart ─────────────────────────────────────────
    price, prev, chg, hist, currency = 0, 0, 0, [], ""
    meta_fund = {}
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1mo"
        r   = await client.get(url, headers=YF_HEADERS, timeout=12)
        d   = r.json()
        res = d["chart"]["result"][0]
        meta = res["meta"]
        price    = meta.get("regularMarketPrice") or meta.get("previousClose", 0)
        prev     = meta.get("previousClose") or meta.get("chartPreviousClose", price)
        _chg     = meta.get("regularMarketChangePercent")
        chg      = round(_chg if _chg is not None else ((price - prev) / prev * 100 if prev else 0), 2)
        currency = meta.get("currency", "")
        ts   = res.get("timestamp", [])
        q    = res.get("indicators", {}).get("quote", [{}])[0]
        op   = q.get("open",  [])
        hi   = q.get("high",  [])
        lo   = q.get("low",   [])
        cl   = q.get("close", [])
        vl   = q.get("volume",[])
        hist = []
        for i, t in enumerate(ts):
            c = cl[i] if i < len(cl) else None
            if c is None: continue
            hist.append({
                "date":   datetime.fromtimestamp(t).strftime("%m/%d"),
                "open":   round(op[i], 2) if i < len(op) and op[i] else round(c, 2),
                "high":   round(hi[i], 2) if i < len(hi) and hi[i] else round(c, 2),
                "low":    round(lo[i], 2) if i < len(lo) and lo[i] else round(c, 2),
                "close":  round(c, 2),
                "volume": int(vl[i]) if i < len(vl) and vl[i] else 0,
            })
        hist = hist[-7:]

        # v8 meta에 포함된 재무지표 추출
        bv = meta.get("bookValue")             # 주당 장부가치
        eps_t = meta.get("epsTrailingTwelveMonths")
        eps_f = meta.get("epsForward")
        div_r = meta.get("dividendRate")
        div_y = meta.get("dividendYield")
        mktcap = meta.get("marketCap")

        meta_fund = {
            "priceToBook":  round(price / bv, 3) if bv and bv > 0 else None,
            "trailingPE":   round(price / eps_t, 2) if eps_t and eps_t > 0 else None,
            "forwardPE":    round(price / eps_f, 2) if eps_f and eps_f > 0 else None,
            "dividendYield": div_y,
            "trailingAnnualDividendYield": div_y or (div_r / price if div_r and price else None),
            "marketCap":    mktcap,
        }
    except Exception as e:
        errors.append(f"chart:{e}")
        return {"symbol": ticker, "_error": str(e)}

    # ── 2) yfinance — 재무지표 ─────────────────────────────
    yf_fund = await get_fundamentals_async(ticker)

    # ── 3) Twelve Data — PBR/PER/PEG 보완 ──────────────────
    td_fund = await td_fundamentals(ticker, client) if TD_API_KEY else {}

    # ── 4) 병합 — meta → yfinance → TD 순으로 덮어쓰기 ──────
    merged = {**meta_fund}
    for k, v in yf_fund.items():
        if v is not None and not k.startswith("_"):
            merged[k] = v
    for k, v in td_fund.items():  # TD가 가장 신뢰도 높음
        if v is not None and not k.startswith("_"):
            merged[k] = v

    has_deep = any(
        merged.get(k) is not None
        for k in ["returnOnEquity", "freeCashflow", "pegRatio", "operatingMargins", "priceToBook", "trailingPE"]
    )

    return {
        "symbol":   ticker,
        "regularMarketPrice": round(price, 2),
        "regularMarketChangePercent": chg,
        "currency": currency,
        "_history": hist,
        "_errors":  errors,
        "_source":  "td+yf" if (TD_API_KEY and not td_fund.get("_td_error")) else ("yfinance" if has_deep else "meta_only"),
        **merged,
    }

async def yf_batch_quote(tickers: list[str], client: httpx.AsyncClient) -> dict:
    """Yahoo Finance 배치 — v8 chart 기반 (50개씩 병렬)"""
    result = {}
    chunk_size = 20  # 병렬 처리
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i+chunk_size]
        tasks = [yf_single_quote(t, client) for t in chunk]
        quotes = await asyncio.gather(*tasks, return_exceptions=True)
        for q in quotes:
            if isinstance(q, dict) and q.get("symbol") and q.get("regularMarketPrice"):
                result[q["symbol"]] = q
        await asyncio.sleep(0.5)
    return result

async def yf_history(ticker: str, client: httpx.AsyncClient) -> list:
    """7일 히스토리"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1mo"
        r   = await client.get(url, headers=YF_HEADERS, timeout=10)
        res = r.json()["chart"]["result"][0]
        ts  = res.get("timestamp", [])
        cl  = res.get("indicators",{}).get("quote",[{}])[0].get("close",[])
        return [
            {"date": datetime.fromtimestamp(t).strftime("%m/%d"), "close": round(c, 2)}
            for t, c in zip(ts, cl) if c is not None
        ][-7:]
    except:
        return []

# ── 동적 유니버스 수집 ─────────────────────────────────────────
async def fetch_sp500_tickers(client: httpx.AsyncClient) -> list[tuple[str,str]]:
    """Yahoo Finance S&P 500 스크리너"""
    tickers = []
    try:
        # Yahoo Finance 내장 S&P 500 스크리너
        for start in range(0, 520, 100):
            url = (
                "https://query1.finance.yahoo.com/v1/finance/screener?"
                "formatted=false&lang=en-US&region=US"
            )
            payload = {
                "offset": start, "size": 100, "sortField": "marketcap",
                "sortType": "DESC", "quoteType": "EQUITY",
                "topOperator": "AND",
                "query": {
                    "operator": "AND",
                    "operands": [
                        {"operator": "EQ", "operands": ["region","us"]},
                        {"operator": "EQ", "operands": ["exchange","NMS,NYQ,NGM,NCM"]},
                    ]
                },
                "userId": "", "userIdType": "guid"
            }
            r = await client.post(url, json=payload, headers=YF_HEADERS, timeout=15)
            quotes = r.json().get("finance",{}).get("result",[{}])[0].get("quotes",[])
            for q in quotes:
                if q.get("symbol"):
                    tickers.append((q["symbol"], q.get("shortName", q["symbol"])))
            await asyncio.sleep(0.3)
    except Exception as e:
        pass
    return tickers

async def fetch_nasdaq100_tickers(client: httpx.AsyncClient) -> list[tuple[str,str]]:
    """QQQ ETF holdings → NASDAQ 100"""
    tickers = []
    try:
        url = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/QQQ?modules=topHoldings"
        r   = await client.get(url, headers=YF_HEADERS, timeout=10)
        holdings = (r.json().get("quoteSummary",{})
                            .get("result",[{}])[0]
                            .get("topHoldings",{})
                            .get("holdings",[]))
        for h in holdings:
            sym = h.get("symbol","")
            if sym:
                tickers.append((sym, h.get("holdingName", sym)))
    except:
        pass
    # fallback: 핵심 NASDAQ 종목
    if len(tickers) < 10:
        tickers = [
            ("AAPL","Apple"),("MSFT","Microsoft"),("NVDA","NVIDIA"),
            ("AMZN","Amazon"),("META","Meta"),("GOOGL","Alphabet"),
            ("TSLA","Tesla"),("AVGO","Broadcom"),("COST","Costco"),
            ("NFLX","Netflix"),("AMD","AMD"),("ADBE","Adobe"),
            ("QCOM","Qualcomm"),("TXN","Texas Instruments"),("ISRG","Intuitive Surgical"),
            ("AMAT","Applied Materials"),("MU","Micron"),("LRCX","Lam Research"),
            ("NOW","ServiceNow"),("KLAC","KLA Corp"),("PANW","Palo Alto"),
            ("SNPS","Synopsys"),("CDNS","Cadence"),("MRVL","Marvell"),
            ("ASML","ASML"),("ARM","ARM Holdings"),("CRWD","CrowdStrike"),
        ]
    return tickers

async def fetch_krx_tickers(market: str, client: httpx.AsyncClient) -> list[tuple[str,str]]:
    """KRX data API → KOSPI / KOSDAQ 종목 리스트"""
    tickers = []
    mkt_id  = "STK" if market == "kospi" else "KSQ"
    today   = kst_now().strftime("%Y%m%d")
    try:
        url  = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
        data = (
            f"bld=dbms/MDC/STAT/standard/MDCSTAT01901"
            f"&mktId={mkt_id}&trdDd={today}&share=1&money=1&csvxls_isNo=false"
        ).encode()
        headers = {
            **YF_HEADERS,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://data.krx.co.kr/",
        }
        r    = await client.post(url, content=data, headers=headers, timeout=15)
        rows = r.json().get("OutBlock_1", [])
        for row in rows:
            code = row.get("ISU_SRT_CD","")  # 6자리 코드
            name = row.get("ISU_ABBRV","")
            cap  = row.get("MKTCAP","0").replace(",","")
            if code and name:
                suffix = ".KS" if market == "kospi" else ".KQ"
                tickers.append((code + suffix, name, int(cap) if cap.isdigit() else 0))
        # 시가총액 상위 순 정렬
        tickers.sort(key=lambda x: x[2], reverse=True)
        return [(t[0], t[1]) for t in tickers[:200]]
    except Exception as e:
        pass
    # fallback: 주요 종목 하드코딩
    fallback = [
        ("005930.KS","삼성전자"),("000660.KS","SK하이닉스"),("005380.KS","현대차"),
        ("000270.KS","기아"),("035420.KS","NAVER"),("005490.KS","POSCO홀딩스"),
        ("105560.KS","KB금융"),("055550.KS","신한지주"),("086790.KS","하나금융지주"),
        ("138040.KS","메리츠금융"),("051910.KS","LG화학"),("006400.KS","삼성SDI"),
        ("373220.KS","LG에너지솔루션"),("012330.KS","현대모비스"),("033780.KS","KT&G"),
        ("017670.KS","SK텔레콤"),("030200.KS","KT"),("316140.KS","우리금융지주"),
        ("032830.KS","삼성생명"),("000810.KS","삼성화재"),("028260.KS","삼성물산"),
        ("207940.KS","삼성바이오로직스"),("068270.KS","셀트리온"),("066570.KS","LG전자"),
        ("003670.KS","포스코퓨처엠"),("247540.KS","에코프로비엠"),("042700.KS","한미반도체"),
        ("096770.KS","SK이노베이션"),("034730.KS","SK"),("003600.KS","SK케미칼"),
    ] if market == "kospi" else [
        ("035720.KQ","카카오"),("247540.KQ","에코프로비엠"),("091990.KQ","셀트리온헬스케어"),
        ("196170.KQ","알테오젠"),("263750.KQ","펄어비스"),("357780.KQ","솔브레인"),
        ("086520.KQ","에코프로"),("112040.KQ","위메이드"),("145020.KQ","휴젤"),
        ("214150.KQ","클래시스"),("039030.KQ","이오테크닉스"),("293490.KQ","카카오게임즈"),
        ("095340.KQ","ISC"),("251270.KQ","넷마블"),("178920.KQ","PI첨단소재"),
    ]
    return fallback

# ── 채점 함수 ─────────────────────────────────────────────────
def score_kr(q: dict) -> tuple[int, list]:
    """
    국장 철학 채점 (Draft 3.0)
    1. PBR 1배 이하 (25점)  — 코리아 디스카운트 안전마진
    2. ROE 10%+ (20점)       — 수익성 / 개선 추세
    3. 배당 3%+ (20점)       — 주주환원
    4. PER 저평가 (20점)     — 밸류에이션
    5. 재무건전성 (15점)     — 부채비율, 유동비율
    """
    score, crit = 0, []

    pbr  = q.get("priceToBook")
    roe  = q.get("returnOnEquity")
    div  = q.get("trailingAnnualDividendYield") or q.get("dividendYield")
    pe   = q.get("trailingPE")
    peg  = q.get("pegRatio")            # 국장도 PEG 참고
    de   = q.get("debtToEquity")        # 부채비율 (%)
    cr   = q.get("currentRatio")        # 유동비율
    rg   = q.get("revenueGrowth")       # 매출 성장률
    og   = q.get("operatingMargins")    # 영업이익률

    # ① PBR — 코리아 디스카운트 안전마진 (25점)
    if pbr is not None:
        if   pbr < 0.5: score+=25; crit.append({"key":"PBR","val":f"{pbr:.2f}x","pass":"pass","note":"극저평가 — 안전마진 매우 높음"})
        elif pbr < 1.0: score+=22; crit.append({"key":"PBR","val":f"{pbr:.2f}x","pass":"pass","note":"1배 이하 — 안전마진 확보"})
        elif pbr < 1.5: score+=12; crit.append({"key":"PBR","val":f"{pbr:.2f}x","pass":"warn","note":"소폭 프리미엄 — 재평가 트리거 필요"})
        else:            crit.append({"key":"PBR","val":f"{pbr:.2f}x","pass":"fail","note":"고평가 — 코리아 디스카운트 없음"})
    else: crit.append({"key":"PBR","val":"N/A","pass":"warn","note":"데이터 없음"})

    # ② ROE — 수익성 (20점)
    if roe is not None:
        r = roe * 100
        if   r >= 20: score+=20; crit.append({"key":"ROE","val":f"{r:.1f}%","pass":"pass","note":"20%+ 우수 수익성"})
        elif r >= 10: score+=15; crit.append({"key":"ROE","val":f"{r:.1f}%","pass":"pass","note":"10%+ 기준 충족"})
        elif r >=  5: score+=6;  crit.append({"key":"ROE","val":f"{r:.1f}%","pass":"warn","note":"5~10% 미흡"})
        elif r >   0: crit.append({"key":"ROE","val":f"{r:.1f}%","pass":"fail","note":"10% 미달"})
        else:          crit.append({"key":"ROE","val":f"{r:.1f}%","pass":"fail","note":"적자 — 투자 제외"})
    else: crit.append({"key":"ROE","val":"N/A","pass":"warn","note":"데이터 없음"})

    # ③ 배당 — 주주환원 (20점)
    d_yield = div * 100 if div else None
    if d_yield is not None:
        if   d_yield >= 5: score+=20; crit.append({"key":"배당수익률","val":f"{d_yield:.1f}%","pass":"pass","note":"5%+ 고배당"})
        elif d_yield >= 3: score+=17; crit.append({"key":"배당수익률","val":f"{d_yield:.1f}%","pass":"pass","note":"3%+ 기준 충족"})
        elif d_yield >= 1: score+=7;  crit.append({"key":"배당수익률","val":f"{d_yield:.1f}%","pass":"warn","note":"3% 미달"})
        else:               crit.append({"key":"배당수익률","val":f"{d_yield:.1f}%","pass":"fail","note":"사실상 무배당"})
    else: crit.append({"key":"배당수익률","val":"N/A","pass":"warn","note":"데이터 없음"})

    # ④ PER — 밸류에이션 (20점)
    if pe is not None and 0 < pe < 500:
        if   pe <  8: score+=20; crit.append({"key":"PER","val":f"{pe:.1f}x","pass":"pass","note":"극저평가 구간"})
        elif pe < 12: score+=15; crit.append({"key":"PER","val":f"{pe:.1f}x","pass":"pass","note":"저평가"})
        elif pe < 18: score+=8;  crit.append({"key":"PER","val":f"{pe:.1f}x","pass":"warn","note":"적정 수준"})
        elif pe < 25: score+=3;  crit.append({"key":"PER","val":f"{pe:.1f}x","pass":"warn","note":"다소 고평가"})
        else:          crit.append({"key":"PER","val":f"{pe:.1f}x","pass":"fail","note":"고평가"})
    else: crit.append({"key":"PER","val":"N/A","pass":"warn","note":"데이터 없음"})

    # ⑤ 재무건전성 (15점)
    fs_score = 0
    if de is not None and de > 0:
        if   de < 50:  fs_score+=8; crit.append({"key":"부채비율","val":f"{de:.0f}%","pass":"pass","note":"50% 이하 안전"})
        elif de < 150: fs_score+=4; crit.append({"key":"부채비율","val":f"{de:.0f}%","pass":"warn","note":"150% 이하"})
        else:           crit.append({"key":"부채비율","val":f"{de:.0f}%","pass":"fail","note":"과도한 부채"})
    if cr is not None:
        if   cr >= 2:  fs_score+=7; crit.append({"key":"유동비율","val":f"{cr:.1f}","pass":"pass","note":"2배+ 안전"})
        elif cr >= 1:  fs_score+=4; crit.append({"key":"유동비율","val":f"{cr:.1f}","pass":"warn","note":"1배 이상"})
        else:           crit.append({"key":"유동비율","val":f"{cr:.1f}","pass":"fail","note":"유동성 위험"})
    if de is None and cr is None:
        crit.append({"key":"재무건전성","val":"N/A","pass":"warn","note":"데이터 없음"})
    score += min(fs_score, 15)

    # 보너스: PEG + 매출 성장 + 영업이익률
    if peg is not None and 0 < peg < 3:
        if   peg < 1.0: score+=5; crit.append({"key":"PEG","val":f"{peg:.2f}","pass":"pass","note":"성장대비 저평가 보너스"})
        elif peg < 2.0: score+=3; crit.append({"key":"PEG","val":f"{peg:.2f}","pass":"warn","note":"성장 감안 적정"})
        else:            crit.append({"key":"PEG","val":f"{peg:.2f}","pass":"warn","note":"성장대비 다소 부담"})
    else:
        crit.append({"key":"PEG","val":"N/A","pass":"warn","note":"데이터 없음"})
    if rg is not None and rg > 0.05:
        score += 3
        crit.append({"key":"매출성장","val":f"+{rg*100:.1f}%","pass":"pass","note":"성장 추세 확인"})
    if og is not None and og > 0.1:
        score += 2
        crit.append({"key":"영업이익률","val":f"{og*100:.1f}%","pass":"pass","note":"10%+ 수익성"})

    return min(score, 100), crit

def score_us(q: dict) -> tuple[int, list]:
    """
    미장 철학 채점 (Draft 3.0)
    1. 해자 지표: ROE/ROIC 15%+ (25점)   — 경제적 해자 proxy
    2. FCF 성장성 (20점)                  — 진짜 현금 창출력
    3. 밸류에이션: PEG + Fwd PER (25점)  — S&P500 평균 이하
    4. 수익성 퀄리티 (15점)              — 영업이익률, 매출성장
    5. 재무건전성 (15점)                 — 부채비율, 유동비율
    """
    score, crit = 0, []

    roe  = q.get("returnOnEquity")
    roa  = q.get("returnOnAssets")
    fcf  = q.get("freeCashflow")
    ocf  = q.get("operatingCashflow")
    peg  = q.get("pegRatio")
    fpe  = q.get("forwardPE")
    tpe  = q.get("trailingPE")
    gm   = q.get("grossMargins")
    om   = q.get("operatingMargins")
    rg   = q.get("revenueGrowth")
    eg   = q.get("earningsGrowth")
    de   = q.get("debtToEquity")
    cr   = q.get("currentRatio")
    beta = q.get("beta")

    # ① 해자 지표 — ROE/ROA (25점)
    # 버핏: 지속적으로 높은 ROE = 해자의 증거
    if roe is not None:
        r = roe * 100
        if   r >= 40: score+=25; crit.append({"key":"ROE","val":f"{r:.1f}%","pass":"pass","note":"40%+ — 압도적 해자"})
        elif r >= 25: score+=20; crit.append({"key":"ROE","val":f"{r:.1f}%","pass":"pass","note":"25%+ — 강한 해자"})
        elif r >= 15: score+=13; crit.append({"key":"ROE","val":f"{r:.1f}%","pass":"pass","note":"15%+ 기준 충족"})
        elif r >=  8: score+=5;  crit.append({"key":"ROE","val":f"{r:.1f}%","pass":"warn","note":"15% 미달"})
        elif r >   0: crit.append({"key":"ROE","val":f"{r:.1f}%","pass":"fail","note":"해자 의심"})
        else:          crit.append({"key":"ROE","val":f"{r:.1f}%","pass":"fail","note":"적자"})
    else: crit.append({"key":"ROE","val":"N/A","pass":"warn","note":"데이터 없음"})

    # ② FCF — 진짜 현금 창출력 (20점)
    # 막스: 회계이익 말고 FCF로 판단
    if fcf is not None:
        if   fcf > 50e9: score+=20; crit.append({"key":"FCF","val":f"${fcf/1e9:.0f}B","pass":"pass","note":"$50B+ 압도적"})
        elif fcf > 10e9: score+=17; crit.append({"key":"FCF","val":f"${fcf/1e9:.0f}B","pass":"pass","note":"$10B+ 우수"})
        elif fcf >  2e9: score+=12; crit.append({"key":"FCF","val":f"${fcf/1e9:.1f}B","pass":"pass","note":"양호"})
        elif fcf >    0: score+=5;  crit.append({"key":"FCF","val":f"${fcf/1e6:.0f}M","pass":"warn","note":"소규모 FCF"})
        else:             crit.append({"key":"FCF","val":"음수","pass":"fail","note":"FCF 적자 — 주의"})
    elif ocf is not None and ocf > 0:
        score += 6
        crit.append({"key":"영업CFO","val":f"${ocf/1e9:.1f}B","pass":"warn","note":"FCF 없음, OCF 양호"})
    else: crit.append({"key":"FCF","val":"N/A","pass":"warn","note":"데이터 없음"})

    # ③ 밸류에이션 — PEG + Fwd PER (25점)
    # S&P500 평균 PEG ~2.0, 평균 Fwd PER ~20배 기준
    pe_score = 0
    if peg is not None and 0 < peg < 100:
        if   peg < 1.0: pe_score+=15; crit.append({"key":"PEG","val":f"{peg:.2f}","pass":"pass","note":"1.0 미만 — 성장대비 저평가"})
        elif peg < 1.5: pe_score+=11; crit.append({"key":"PEG","val":f"{peg:.2f}","pass":"pass","note":"S&P500 평균 이하"})
        elif peg < 2.5: pe_score+=6;  crit.append({"key":"PEG","val":f"{peg:.2f}","pass":"warn","note":"S&P500 평균 수준"})
        else:            crit.append({"key":"PEG","val":f"{peg:.2f}","pass":"fail","note":"성장대비 고평가"})
    else: crit.append({"key":"PEG","val":"N/A","pass":"warn","note":"데이터 없음"})

    ref_pe = fpe or tpe
    if ref_pe is not None and 0 < ref_pe < 300:
        if   ref_pe < 15: pe_score+=10; crit.append({"key":"Fwd PER","val":f"{ref_pe:.1f}x","pass":"pass","note":"저평가"})
        elif ref_pe < 22: pe_score+=7;  crit.append({"key":"Fwd PER","val":f"{ref_pe:.1f}x","pass":"pass","note":"S&P500 평균 이하"})
        elif ref_pe < 35: pe_score+=3;  crit.append({"key":"Fwd PER","val":f"{ref_pe:.1f}x","pass":"warn","note":"평균 이상"})
        else:              crit.append({"key":"Fwd PER","val":f"{ref_pe:.1f}x","pass":"fail","note":"고평가 — 완벽한 실행 가정"})
    else: crit.append({"key":"Fwd PER","val":"N/A","pass":"warn","note":"데이터 없음"})
    score += min(pe_score, 25)

    # ④ 수익성 퀄리티 (15점)
    qual_score = 0
    if om is not None:
        if   om > 0.30: qual_score+=8; crit.append({"key":"영업이익률","val":f"{om*100:.1f}%","pass":"pass","note":"30%+ 고마진 사업"})
        elif om > 0.15: qual_score+=5; crit.append({"key":"영업이익률","val":f"{om*100:.1f}%","pass":"pass","note":"15%+ 양호"})
        elif om > 0.05: qual_score+=2; crit.append({"key":"영업이익률","val":f"{om*100:.1f}%","pass":"warn","note":"저마진"})
        else:            crit.append({"key":"영업이익률","val":f"{om*100:.1f}%","pass":"fail","note":"마진 악화"})
    if eg is not None and eg > 0:
        if   eg > 0.20: qual_score+=7; crit.append({"key":"이익성장","val":f"+{eg*100:.1f}%","pass":"pass","note":"20%+ 고성장"})
        elif eg > 0.10: qual_score+=4; crit.append({"key":"이익성장","val":f"+{eg*100:.1f}%","pass":"pass","note":"10%+ 성장"})
        else:            qual_score+=2; crit.append({"key":"이익성장","val":f"+{eg*100:.1f}%","pass":"warn","note":"저성장"})
    elif eg is not None and eg <= 0:
        crit.append({"key":"이익성장","val":f"{eg*100:.1f}%","pass":"fail","note":"이익 감소"})
    score += min(qual_score, 15)

    # ⑤ 재무건전성 (15점)
    # 버핏: 레버리지 낮고 현금 풍부한 기업
    fs_score = 0
    if de is not None and de >= 0:
        if   de <  30: fs_score+=8; crit.append({"key":"부채/자본","val":f"{de:.0f}%","pass":"pass","note":"무차입 수준"})
        elif de < 100: fs_score+=5; crit.append({"key":"부채/자본","val":f"{de:.0f}%","pass":"pass","note":"건전"})
        elif de < 200: fs_score+=2; crit.append({"key":"부채/자본","val":f"{de:.0f}%","pass":"warn","note":"보통"})
        else:           crit.append({"key":"부채/자본","val":f"{de:.0f}%","pass":"fail","note":"고레버리지"})
    if cr is not None:
        if   cr >= 2:  fs_score+=7; crit.append({"key":"유동비율","val":f"{cr:.1f}","pass":"pass","note":"현금 풍부"})
        elif cr >= 1:  fs_score+=4; crit.append({"key":"유동비율","val":f"{cr:.1f}","pass":"warn","note":"적정"})
        else:           crit.append({"key":"유동비율","val":f"{cr:.1f}","pass":"fail","note":"유동성 위험"})
    if de is None and cr is None:
        crit.append({"key":"재무건전성","val":"N/A","pass":"warn","note":"데이터 없음"})
    score += min(fs_score, 15)

    return min(score, 100), crit

# ── 메인 스크리너 ─────────────────────────────────────────────
async def run_screener(market: str):
    if _progress[market]["running"]:
        return
    _progress[market]["running"] = True
    _progress[market]["done"]    = 0
    _progress[market]["total"]   = 0
    _progress[market]["phase"]   = "유니버스 수집 중"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            # 1. 유니버스 수집
            if market == "kr":
                kospi  = await fetch_krx_tickers("kospi",  client)
                kosdaq = await fetch_krx_tickers("kosdaq", client)
                universe = kospi[:200] + kosdaq[:150]
            else:
                sp500  = await fetch_sp500_tickers(client)
                nq100  = await fetch_nasdaq100_tickers(client)
                # 중복 제거
                seen = set()
                universe = []
                for t, n in sp500 + nq100:
                    if t not in seen:
                        seen.add(t); universe.append((t, n))

            tickers = [t for t, _ in universe]
            names   = {t: n for t, n in universe}
            _progress[market]["total"] = len(tickers)
            _progress[market]["phase"] = f"시세 수집 중 (총 {len(tickers)}개)"

            # 2. 배치 시세 수집
            all_quotes = {}
            async with httpx.AsyncClient(timeout=20) as c2:
                for i in range(0, len(tickers), 50):
                    chunk = tickers[i:i+50]
                    batch = await yf_batch_quote(chunk, c2)
                    all_quotes.update(batch)
                    _progress[market]["done"] = min(i+50, len(tickers))
                    await asyncio.sleep(0.2)

            # 3. 채점
            _progress[market]["phase"] = "채점 중"
            score_fn = score_kr if market == "kr" else score_us
            results  = []
            async with httpx.AsyncClient(timeout=15) as c3:
                for ticker in tickers:
                    q = all_quotes.get(ticker, {})
                    if not q.get("regularMarketPrice"):
                        continue
                    score, crit = score_fn(q)
                    # 히스토리는 이미 quote에서 가져옴
                    hist = q.get("_history", [])

                    roe = q.get("returnOnEquity")
                    div = q.get("trailingAnnualDividendYield")
                    # 점수 총평 — 항목별 상세 설명
                    passed = [c for c in crit if c["pass"] == "pass"]
                    failed = [c for c in crit if c["pass"] == "fail"]
                    warned = [c for c in crit if c["pass"] == "warn"]
                    pass_detail = ", ".join(f"{c['key']} {c['val']}" for c in passed[:3])
                    fail_detail = ", ".join(f"{c['key']} {c['val']}" for c in failed[:2])
                    warn_detail = ", ".join(f"{c['key']} {c['val']}" for c in warned[:2])

                    if score >= 75:
                        summary = (
                            f"핵심 기준 {len(passed)}개 충족 ({pass_detail}). "
                            f"Draft 3.0 기준 매수 적극 고려 구간. "
                            f"{'단, ' + warn_detail + ' 은 개선 여지 있음.' if warned else '전반적으로 우량한 상태.'}"
                        )
                    elif score >= 60:
                        summary = (
                            f"{pass_detail} 으로 긍정 신호 확인. "
                            f"그러나 {fail_detail or warn_detail} 이 기준 미달. "
                            f"추가 하락 또는 실적 개선 트리거 확인 후 분할 매수 고려."
                        )
                    elif score >= 40:
                        summary = (
                            f"{pass_detail or '일부 항목'} 은 양호하나, "
                            f"{fail_detail} 등 주요 기준 미달로 {score}점. "
                            f"현재 진입보다 추가 조정 후 재평가 권장. 워치리스트 유지."
                        )
                    else:
                        summary = (
                            f"{fail_detail or '주요 기준'} 불충족, 통과 항목 {len(passed)}개로 {score}점. "
                            f"현재 투자 철학(Draft 3.0)과 불일치. "
                            f"구조적 문제 여부 재확인 후 관망 유지. 하워드 막스: '리스크는 손실 가능성이다.'"
                        )

                    beta = q.get("beta")
                    de   = q.get("debtToEquity")
                    cr   = q.get("currentRatio")
                    og   = q.get("operatingMargins")
                    rg   = q.get("revenueGrowth")

                    results.append({
                        "ticker":     ticker,
                        "name":       names.get(ticker, q.get("shortName", ticker)),
                        "market":     market,
                        "score":      score,
                        "summary":    summary,
                        "criteria":   crit,
                        "price":      round(q.get("regularMarketPrice", 0), 2),
                        "change_pct": round(q.get("regularMarketChangePercent", 0), 2),
                        "history":    hist,
                        # 밸류에이션
                        "pbr":        q.get("priceToBook"),
                        "pe":         q.get("trailingPE"),
                        "fwd_pe":     q.get("forwardPE"),
                        "peg":        q.get("pegRatio"),
                        # 수익성
                        "roe":        round(roe*100,1) if roe else None,
                        "op_margin":  round(og*100,1) if og else None,
                        "rev_growth": round(rg*100,1) if rg else None,
                        # 배당/현금흐름
                        "div_yield":  round(div*100,2) if div else None,
                        "fcf":        q.get("freeCashflow"),
                        # 재무건전성
                        "debt_equity": round(de,1) if de else None,
                        "cur_ratio":   round(cr,2) if cr else None,
                        # 리스크/기타
                        "beta":       round(beta,2) if beta else None,
                        "mktcap":     q.get("marketCap"),
                        "currency":   q.get("currency",""),
                    })

            results.sort(key=lambda x: x["score"], reverse=True)
            _screener_cache[market]["data"]    = results
            _screener_cache[market]["updated"] = kst_now().isoformat()
            _progress[market]["phase"] = f"완료 — {len(results)}개 종목"

    except Exception as e:
        _progress[market]["phase"] = f"오류: {e}"
    finally:
        _progress[market]["running"] = False

# ── 스케줄러 ─────────────────────────────────────────────────
def _schedule_refresh():
    mh = is_market_hours()
    if mh["kr"]: asyncio.create_task(run_screener("kr"))
    if mh["us"]: asyncio.create_task(run_screener("us"))

@app.on_event("startup")
async def startup():
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    sch = AsyncIOScheduler()
    sch.add_job(_schedule_refresh, "interval", minutes=30)
    sch.start()
    asyncio.create_task(run_screener("kr"))
    asyncio.create_task(run_screener("us"))

# ── 스크리너 엔드포인트 ───────────────────────────────────────

@app.get("/chart/{ticker}")
async def get_chart(ticker: str, range: str = "1mo", interval: str = "1d"):
    """주가 차트 OHLCV — range: 1d/5d/1mo/3mo/6mo/1y, interval: 5m/1h/1d/1wk"""
    range_interval_map = {
        "1d": "5m", "5d": "1h", "1mo": "1d",
        "3mo": "1d", "6mo": "1d", "1y": "1wk",
    }
    if interval == "1d" and range in range_interval_map:
        interval = range_interval_map[range]
    try:
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
               f"?interval={interval}&range={range}")
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(url, headers=YF_HEADERS)
        d    = r.json()
        res  = d["chart"]["result"][0]
        meta = res["meta"]
        ts   = res.get("timestamp", [])
        q    = res.get("indicators", {}).get("quote", [{}])[0]
        op, hi, lo, cl, vl = (q.get(k, []) for k in ("open","high","low","close","volume"))

        fmt = "%H:%M" if interval in ("1m","5m","15m","30m","1h") else "%m/%d"
        candles = []
        for i, t in enumerate(ts):
            c = cl[i] if i < len(cl) else None
            if c is None: continue
            candles.append({
                "date":   datetime.fromtimestamp(t).strftime(fmt),
                "open":   round(op[i], 2) if i < len(op) and op[i] else round(c, 2),
                "high":   round(hi[i], 2) if i < len(hi) and hi[i] else round(c, 2),
                "low":    round(lo[i], 2) if i < len(lo) and lo[i] else round(c, 2),
                "close":  round(c, 2),
                "volume": int(vl[i]) if i < len(vl) and vl[i] else 0,
            })
        price = meta.get("regularMarketPrice") or (candles[-1]["close"] if candles else 0)
        prev  = meta.get("previousClose") or meta.get("chartPreviousClose", price)
        return {
            "status": "ok", "ticker": ticker,
            "price": round(price, 2), "prev": round(prev, 2),
            "change_pct": round(meta.get("regularMarketChangePercent") or ((price - prev) / prev * 100 if prev else 0), 2),
            "currency": meta.get("currency", ""),
            "range": range, "interval": interval,
            "candles": candles,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}



@app.get("/yf/bs/{ticker}")
async def yf_bs_debug(ticker: str):
    """balance sheet row 이름 확인용"""
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor
    import asyncio
    def get_bs():
        t = yf.Ticker(ticker)
        result = {}
        try:
            bs = t.quarterly_balance_sheet
            result["bs_rows"] = list(bs.index) if bs is not None and not bs.empty else []
            result["bs_sample"] = {str(k): float(bs.loc[k].iloc[0]) for k in list(bs.index)[:10] if not bs.loc[k].isna().all()} if bs is not None and not bs.empty else {}
        except Exception as e:
            result["bs_error"] = str(e)
        try:
            inc = t.quarterly_income_stmt
            result["inc_rows"] = list(inc.index) if inc is not None and not inc.empty else []
            result["inc_sample"] = {str(k): float(inc.loc[k].iloc[0]) for k in list(inc.index)[:10] if not inc.loc[k].isna().all()} if inc is not None and not inc.empty else {}
        except Exception as e:
            result["inc_error"] = str(e)
        info = t.info or {}
        result["shares"] = info.get("sharesOutstanding")
        result["price"]  = info.get("currentPrice") or info.get("regularMarketPrice")
        return result
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        data = await loop.run_in_executor(pool, get_bs)
    return {"ticker": ticker, "data": data}

@app.get("/yf/debug/{ticker}")
async def yf_debug(ticker: str):
    """yfinance 원본 info 필드 전체 확인"""
    import yfinance as yf
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def get_raw():
        t = yf.Ticker(ticker)
        info = t.info or {}
        # 밸류에이션 관련 필드만 추출
        keys = [
            "priceToBook","bookValue","currentPrice","regularMarketPrice",
            "trailingPE","forwardPE","trailingEps","forwardEps",
            "pegRatio","trailingPegRatio",
            "returnOnEquity","returnOnAssets",
            "grossMargins","operatingMargins","profitMargins",
            "freeCashflow","operatingCashflow",
            "trailingAnnualDividendYield","dividendYield","dividendRate",
            "marketCap","beta","debtToEquity","currentRatio",
            "revenueGrowth","earningsGrowth",
            "fiftyTwoWeekHigh","fiftyTwoWeekLow",
            "shortRatio","sharesOutstanding",
        ]
        return {k: info.get(k) for k in keys}

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        raw = await loop.run_in_executor(pool, get_raw)
    parsed = await get_fundamentals_async(ticker)
    return {"ticker": ticker, "raw_info": raw, "parsed": parsed}

@app.get("/screener/test/{ticker}")
async def test_ticker(ticker: str):
    """단일 종목 디버그"""
    async with httpx.AsyncClient() as client:
        data = await yf_single_quote(ticker, client)
    return {"ticker": ticker, "data": data}

@app.get("/screener/debug/{market}")
async def screener_debug(market: str):
    """스크리너 상태 확인"""
    p = _progress.get(market, {})
    return {
        "progress": p,
        "cached_count": len(_screener_cache.get(market,{}).get("data",[])),
        "updated": _screener_cache.get(market,{}).get("updated"),
        "market_hours": is_market_hours(),
    }

@app.get("/screener/progress/{market}")
async def get_progress(market: str):
    p = _progress.get(market, {})
    return {
        "running": p.get("running", False),
        "phase":   p.get("phase",""),
        "total":   p.get("total", 0),
        "done":    p.get("done",  0),
        "pct":     round(p["done"]/p["total"]*100) if p.get("total") else 0,
        "cached":  len(_screener_cache.get(market,{}).get("data",[])),
        "updated": _screener_cache.get(market,{}).get("updated"),
    }

@app.get("/screener/{market}")
async def get_screener(market: str, force: bool = False):
    if market not in ("kr","us"):
        return {"status":"error","message":"market must be kr or us"}
    if force and not _progress[market]["running"]:
        asyncio.create_task(run_screener(market))
        return {"status":"ok","running":True,"phase":"스크리닝 시작됨","data":_screener_cache[market]["data"],"count":len(_screener_cache[market]["data"]),"total":0,"done":0}
    p = _progress[market]
    return {
        "status":  "ok",
        "count":   len(_screener_cache[market]["data"]),
        "updated": _screener_cache[market]["updated"],
        "running": p["running"],
        "phase":   p["phase"],
        "total":   p["total"],
        "done":    p["done"],
        "pct":     round(p["done"]/p["total"]*100) if p.get("total") else 0,
        "market_hours": is_market_hours()[market],
        "data":    _screener_cache[market]["data"],
    }

# ── 마켓 데이터 ───────────────────────────────────────────────
MARKET_TICKERS = {
    "sp500":"^GSPC","nasdaq":"^IXIC","dow":"^DJI",
    "kospi":"^KS11","kosdaq":"^KQ11",
    "usdkrw":"KRW=X","usdjpy":"JPY=X",
    "us10y":"^TNX","us2y":"^IRX",
    "gold":"GC=F","wti":"CL=F","copper":"HG=F",
}

async def fetch_quote(sym: str, client: httpx.AsyncClient) -> dict:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=2d"
        r   = await client.get(url, headers=YF_HEADERS, timeout=8)
        m   = r.json()["chart"]["result"][0]["meta"]
        p   = m.get("regularMarketPrice") or m.get("previousClose", 0)
        pv  = m.get("previousClose") or m.get("chartPreviousClose", p)
        chg = m.get("regularMarketChangePercent")  # Yahoo가 직접 제공하는 값 사용
        if chg is None and pv:
            chg = (p - pv) / pv * 100
        return {"price": round(p,4), "prev": round(pv,4),
                "change_pct": round(chg or 0, 2),
                "currency": m.get("currency","")}
    except:
        return {"price": None, "change_pct": None}

@app.get("/market/overview")
async def market_overview():
    async with httpx.AsyncClient() as c:
        res = {}
        for k, s in MARKET_TICKERS.items():
            res[k] = await fetch_quote(s, c)
    return {"status":"ok","updated":kst_now().isoformat(),"data":res}

async def fetch_quote_hist(sym: str, client: httpx.AsyncClient) -> dict:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=7d"
        r   = await client.get(url, headers=YF_HEADERS, timeout=10)
        res = r.json()["chart"]["result"][0]
        m   = res["meta"]
        p   = m.get("regularMarketPrice") or m.get("previousClose",0)
        pv  = m.get("previousClose") or m.get("chartPreviousClose",p)
        chg = m.get("regularMarketChangePercent")
        if chg is None and pv:
            chg = (p - pv) / pv * 100
        ts  = res.get("timestamp",[])
        cl  = res.get("indicators",{}).get("quote",[{}])[0].get("close",[])
        hist = [{"date":datetime.fromtimestamp(t).strftime("%m/%d"),"close":round(c,2)}
                for t,c in zip(ts,cl) if c is not None][-7:]
        return {"price":round(p,2),"prev":round(pv,2),
                "change_pct":round(chg or 0,2),
                "currency":m.get("currency",""),"history":hist}
    except:
        return {"price":None,"change_pct":None,"history":[]}

@app.get("/market/stocks")
async def market_stocks():
    STOCKS = {
        "005930.KS":"삼성전자","000660.KS":"SK하이닉스","005380.KS":"현대차",
        "AAPL":"Apple","MSFT":"Microsoft","NVDA":"NVIDIA","GOOGL":"Alphabet",
    }
    async with httpx.AsyncClient() as c:
        res = {}
        for tk, nm in STOCKS.items():
            d = await fetch_quote_hist(tk, c)
            d["name"] = nm
            res[tk] = d
    return {"status":"ok","updated":kst_now().isoformat(),"data":res}

# ── DART 공시 ─────────────────────────────────────────────────
DART_WATCH = {
    "005930":"삼성전자","000660":"SK하이닉스","005380":"현대차",
    "035420":"NAVER","051910":"LG화학","006400":"삼성SDI",
    "207940":"삼성바이오로직스","005490":"POSCO홀딩스","035720":"카카오","000270":"기아",
}

@app.get("/dart/recent")
async def dart_recent(days: int = 7):
    end   = kst_now().strftime("%Y%m%d")
    start = (kst_now() - timedelta(days=days)).strftime("%Y%m%d")
    results = []
    async with httpx.AsyncClient(timeout=10) as c:
        for code, name in DART_WATCH.items():
            try:
                r = await c.get(
                    "https://opendart.fss.or.kr/api/list.json",
                    params={"crtfc_key":DART_API_KEY,"corp_code":code,
                            "bgn_de":start,"end_de":end,"page_count":5},
                )
                d = r.json()
                if d.get("status") == "000":
                    for item in d.get("list",[]):
                        results.append({
                            "company": name,
                            "title":   item.get("report_nm",""),
                            "date":    item.get("rcept_dt",""),
                            "url":     f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no','')}",
                            "type":    "major" if any(k in item.get("report_nm","") for k in ["실적","배당","유상증자","합병","분할"]) else "normal",
                        })
            except: pass
            await asyncio.sleep(0.2)
    results.sort(key=lambda x: x["date"], reverse=True)
    return {"status":"ok","count":len(results),"data":results}

# ── 뉴스 RSS ─────────────────────────────────────────────────
RSS_FEEDS = [
    {"name":"한국경제","url":"https://www.hankyung.com/feed/economy"},
    {"name":"한국경제","url":"https://www.hankyung.com/feed/finance"},
    {"name":"매일경제","url":"https://www.mk.co.kr/rss/30000001/"},
    {"name":"매일경제","url":"https://www.mk.co.kr/rss/30100041/"},
    {"name":"연합뉴스","url":"https://www.yna.co.kr/rss/economy.xml"},
]

def parse_rss(xml: str, src: str) -> list:
    import re
    items, raw_items = [], re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)
    for raw in raw_items[:6]:
        def g(tag): m=re.search(rf"<{tag}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>",raw,re.DOTALL); return m.group(1).strip() if m else ""
        title = re.sub(r"<[^>]+>","",g("title")).strip()
        desc  = re.sub(r"<[^>]+>","",g("description")).strip()[:120]
        if title:
            items.append({"source":src,"title":title,"link":g("link"),
                          "date":g("pubDate"),"desc":desc})
    return items

@app.get("/news/rss")
async def news_rss():
    all_news = []
    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as c:
        for f in RSS_FEEDS:
            try:
                r = await c.get(f["url"], headers={"User-Agent":"Mozilla/5.0"})
                all_news.extend(parse_rss(r.text, f["name"]))
            except: pass
    return {"status":"ok","count":len(all_news),"data":all_news}

# ── Telegram ─────────────────────────────────────────────────
@app.get("/telegram/messages")
async def telegram_messages(limit: int = 20):
    if not TELEGRAM_BOT_TOKEN:
        return {"status":"error","message":"TELEGRAM_BOT_TOKEN not set"}
    msgs = []
    async with httpx.AsyncClient(timeout=10) as c:
        for chat_id in TELEGRAM_CHAT_IDS:
            try:
                r = await c.get(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                    params={"limit":limit},
                )
                for upd in r.json().get("result",[]):
                    msg = upd.get("message") or upd.get("channel_post",{})
                    if msg: msgs.append({"chat_id":chat_id,"text":msg.get("text",""),"date":msg.get("date",0)})
            except: pass
    return {"status":"ok","data":msgs}

# ── 브리핑 ───────────────────────────────────────────────────
@app.get("/briefing/morning")
async def briefing_morning():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    return {"status":"ok","type":"morning","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:5],"news":news["data"][:8]}

@app.get("/briefing/closing")
async def briefing_closing():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    return {"status":"ok","type":"closing","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:10],"news":news["data"][:6]}

@app.get("/briefing/weekend")
async def briefing_weekend():
    news = await news_rss()
    dart = await dart_recent(days=3)
    return {"status":"ok","type":"weekend","generated_at":kst_now().isoformat(),
            "news":news["data"],"disclosures":dart["data"][:8]}

# ── 루트 / 앱 서빙 ───────────────────────────────────────────
@app.get("/")
def root():
    return {"status":"running","version":"4.1","chart_endpoint":True,"twelve_data":True}


@app.get("/manifest.json")
async def serve_manifest():
    from fastapi.responses import JSONResponse
    return JSONResponse({
        "name": "ANDREW Investment System",
        "short_name": "ANDREW",
        "description": "개인 투자 철학 기반 주식 스크리닝 시스템",
        "start_url": "/app",
        "display": "standalone",
        "background_color": "#0a0a0a",
        "theme_color": "#00ff88",
        "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}]
    })

@app.get("/sw.js")
async def serve_sw():
    from fastapi.responses import Response
    sw = b"self.addEventListener('install',e=>{self.skipWaiting();});self.addEventListener('activate',e=>{self.clients.claim();});self.addEventListener('fetch',e=>{e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});"
    return Response(content=sw, media_type="application/javascript")

@app.get("/icon.svg")
async def serve_icon():
    from fastapi.responses import Response
    svg = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
<rect width="192" height="192" rx="40" fill="#0a0a0a"/>
<text x="96" y="95" font-family="monospace" font-size="80" font-weight="bold" fill="#00ff88" text-anchor="middle">A</text>
<text x="96" y="140" font-family="monospace" font-size="16" fill="#666" text-anchor="middle">ANDREW</text>
</svg>'''
    return Response(content=svg, media_type="image/svg+xml")

@app.get("/app")
async def serve_app():
    return FileResponse("andrew.html", media_type="text/html")
