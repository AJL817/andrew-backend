import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Andrew Investment API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DART_API_KEY       = os.getenv("DART_API_KEY")
KIS_APP_KEY        = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET     = os.getenv("KIS_APP_SECRET")
KIS_ACCOUNT_NO     = os.getenv("KIS_ACCOUNT_NO")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_IDS  = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
ALPHA_VANTAGE_KEY  = os.getenv("ALPHA_VANTAGE_KEY")

_cache = {
    "dart": [],
    "kis_token": None,
    "kis_token_expires": None,
    "telegram_messages": [],
}

DART_BASE = "https://opendart.fss.or.kr/api"
KIS_BASE  = "https://openapivts.koreainvestment.com:29443"
TELEGRAM_BASE = "https://api.telegram.org"
AV_BASE   = "https://www.alphavantage.co/query"

MAJOR_COMPANIES = {
    "삼성전자": "00126380",
    "SK하이닉스": "00164779",
    "NAVER": "00104379",
    "LG화학": "00109961",
    "삼성SDI": "00126362",
    "현대차": "00164742",
}

# ── DART ──────────────────────────────────────────────────────

def classify_disclosure(title: str) -> str:
    if any(k in title for k in ["자사주", "배당", "유상증자", "합병", "분할"]):
        return "high"
    if any(k in title for k in ["실적", "사업보고서", "반기보고서"]):
        return "mid"
    return "normal"

@app.get("/dart/recent")
async def get_recent_disclosures(days: int = 7):
    today = datetime.now()
    start = (today - timedelta(days=days)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    results = []
    async with httpx.AsyncClient() as client:
        for name, code in MAJOR_COMPANIES.items():
            params = {
                "crtfc_key": DART_API_KEY,
                "corp_code": code,
                "bgn_de": start,
                "end_de": end,
                "sort": "date",
                "sort_mth": "desc",
            }
            r = await client.get(f"{DART_BASE}/list.json", params=params, timeout=10)
            data = r.json()
            if data.get("status") == "000":
                for d in data.get("list", [])[:3]:
                    results.append({
                        "company": name,
                        "title": d.get("report_nm"),
                        "date": d.get("rcept_dt"),
                        "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={d.get('rcept_no')}",
                        "type": classify_disclosure(d.get("report_nm", "")),
                    })
    results.sort(key=lambda x: x["date"], reverse=True)
    _cache["dart"] = results
    return {"status": "ok", "count": len(results), "data": results}

# ── KIS ───────────────────────────────────────────────────────

async def get_kis_token() -> Optional[str]:
    now = datetime.now()
    if _cache["kis_token"] and _cache["kis_token_expires"] and now < _cache["kis_token_expires"]:
        return _cache["kis_token"]
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{KIS_BASE}/oauth2/tokenP",
            json={"grant_type": "client_credentials", "appkey": KIS_APP_KEY, "appsecret": KIS_APP_SECRET},
            timeout=10,
        )
        token = r.json().get("access_token")
        if token:
            _cache["kis_token"] = token
            _cache["kis_token_expires"] = now + timedelta(hours=11)
            return token
    return None

def calc_bollinger(prices: list, window: int = 20) -> dict:
    if len(prices) < window:
        return {}
    import statistics
    recent = prices[-window:]
    sma = sum(recent) / window
    std = statistics.stdev(recent)
    return {
        "upper": round(sma + 2 * std, 0),
        "mid": round(sma, 0),
        "lower": round(sma - 2 * std, 0),
        "current": prices[-1],
        "signal": "하단접근" if prices[-1] < sma - std else "상단접근" if prices[-1] > sma + std else "중립",
    }

@app.get("/kis/price/{ticker}")
async def get_kr_stock_price(ticker: str):
    token = await get_kis_token()
    if not token:
        return {"error": "KIS 토큰 발급 실패"}
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": "FHKST01010100",
    }
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker}
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{KIS_BASE}/uapi/domestic-stock/v1/quotations/inquire-price",
            headers=headers, params=params, timeout=10,
        )
        output = r.json().get("output", {})
        return {
            "ticker": ticker,
            "current_price": output.get("stck_prpr"),
            "change_pct": output.get("prdy_ctrt"),
            "per": output.get("per"),
            "pbr": output.get("pbr"),
        }

# ── 텔레그램 ───────────────────────────────────────────────────

@app.get("/telegram/messages")
async def get_telegram_messages(limit: int = 20):
    all_messages = []
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{TELEGRAM_BASE}/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
            params={"limit": 100, "offset": -100},
            timeout=10,
        )
        for update in r.json().get("result", []):
            msg = update.get("message") or update.get("channel_post")
            if not msg:
                continue
            chat = msg.get("chat", {})
            chat_id = str(chat.get("id", ""))
            if TELEGRAM_CHAT_IDS and TELEGRAM_CHAT_IDS != [""]:
                if chat_id not in TELEGRAM_CHAT_IDS:
                    continue
            text = msg.get("text", "")
            all_messages.append({
                "chat_id": chat_id,
                "chat_title": chat.get("title", ""),
                "text": text[:200],
                "date": datetime.fromtimestamp(msg.get("date", 0)).isoformat(),
                "is_stock_related": any(k in text for k in ["공시", "실적", "매수", "매도", "급등", "배당", "주가"]),
            })
    all_messages.sort(key=lambda x: x["date"], reverse=True)
    result = all_messages[:limit]
    _cache["telegram_messages"] = result
    return {"status": "ok", "count": len(result), "data": result}

# ── Alpha Vantage ─────────────────────────────────────────────

@app.get("/us/price/{ticker}")
async def get_us_stock_price(ticker: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(AV_BASE, params={
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
            "apikey": ALPHA_VANTAGE_KEY,
        }, timeout=15)
        data = r.json().get("Global Quote", {})
        return {
            "ticker": ticker,
            "price": data.get("05. price"),
            "change_pct": data.get("10. change percent"),
        }

# ── 대시보드 ───────────────────────────────────────────────────

@app.get("/dashboard")
async def get_dashboard_data():
    return {
        "timestamp": datetime.now().isoformat(),
        "dart_cache": _cache["dart"][:5],
        "telegram_cache": _cache["telegram_messages"][:5],
    }

# ── 스케줄러 ───────────────────────────────────────────────────

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup():
    scheduler.add_job(get_recent_disclosures, "interval", minutes=30)
    scheduler.add_job(get_telegram_messages, "interval", minutes=5)
    scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()

@app.get("/")
def root():
    return {"status": "running"}

@app.get("/app")
async def serve_app():
    from fastapi.responses import FileResponse
    return FileResponse("andrew.html", media_type="text/html")