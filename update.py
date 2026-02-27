import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
msrc = os.path.join(REPO, "main.py")
mtmp = os.path.join(REPO, "main.tmp")

with open(msrc, "r", encoding="utf-8") as f:
    mc = f.read()

changes = 0

# ── 1) DART 함수 추가 (DART_WATCH 바로 앞) ──────────────────
dart_code = '''
# ── DART 재무제표 기반 재무지표 계산 ────────────────────────────────
KR_TICKER_TO_CORP = {
    "005930.KS":"00126380","000660.KS":"00164779","005380.KS":"00164742",
    "035420.KS":"00266961","051910.KS":"00110013","006400.KS":"00126186",
    "207940.KS":"00877059","005490.KS":"00164565","035720.KS":"00401731",
    "000270.KS":"00116757","055550.KS":"00120030","086790.KS":"00138321",
    "105560.KS":"00164603","316140.KS":"00591844","032830.KS":"00148043",
    "003550.KS":"00108819","033780.KS":"00151854","030200.KS":"00104899",
    "017670.KS":"00111785","012330.KS":"00164956","010950.KS":"00164714",
}
_dart_corp_cache: dict = {}

async def get_dart_corp_code(ticker: str, client) -> str:
    if ticker in _dart_corp_cache:
        return _dart_corp_cache[ticker]
    code = KR_TICKER_TO_CORP.get(ticker, "")
    if code:
        _dart_corp_cache[ticker] = code
        return code
    stock_code = ticker.split(".")[0]
    try:
        r = await client.get(
            "https://opendart.fss.or.kr/api/company.json",
            params={"crtfc_key": DART_API_KEY, "stock_code": stock_code},
            timeout=8,
        )
        d = r.json()
        if d.get("status") == "000":
            corp_code = d.get("corp_code", "")
            if corp_code:
                _dart_corp_cache[ticker] = corp_code
                return corp_code
    except:
        pass
    _dart_corp_cache[ticker] = ""
    return ""

async def dart_financials(ticker: str, client) -> dict:
    """DART 사업보고서 → ROE, 부채비율, 영업이익률 직접 계산"""
    if not DART_API_KEY:
        return {}
    corp_code = await get_dart_corp_code(ticker, client)
    if not corp_code:
        return {}
    result = {}
    for fs_div in ["CFS", "OFS"]:
        try:
            r = await client.get(
                "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json",
                params={"crtfc_key": DART_API_KEY, "corp_code": corp_code,
                        "bsns_year": str(kst_now().year - 1),
                        "reprt_code": "11011", "fs_div": fs_div},
                timeout=12,
            )
            d = r.json()
            if d.get("status") != "000": continue
            items = d.get("list", [])
            if not items: continue

            def get_val(keywords, sj_div):
                for item in items:
                    if item.get("sj_div") != sj_div: continue
                    nm = item.get("account_nm", "")
                    if any(k in nm for k in keywords):
                        v = item.get("thstrm_amount","").replace(",","").replace("-","").strip()
                        try: return float(v) if v else None
                        except: pass
                return None

            net_income   = get_val(["당기순이익"], "IS")
            equity       = get_val(["자본총계","지배기업 소유주 지분"], "BS")
            total_assets = get_val(["자산총계"], "BS")
            total_liab   = get_val(["부채총계"], "BS")
            revenue      = get_val(["매출액","영업수익"], "IS")
            op_income    = get_val(["영업이익"], "IS")

            if equity and equity > 0:
                if net_income: result["dart_roe"] = round(net_income / equity * 100, 2)
                if total_liab: result["dart_debt_ratio"] = round(total_liab / equity * 100, 1)
            if total_assets and total_assets > 0 and net_income:
                result["dart_roa"] = round(net_income / total_assets * 100, 2)
            if revenue and revenue > 0:
                if op_income: result["dart_op_margin"] = round(op_income / revenue * 100, 2)
                if net_income: result["dart_net_margin"] = round(net_income / revenue * 100, 2)
            result["dart_source"] = fs_div
            break
        except Exception as e:
            result["dart_error"] = str(e)
    return result

'''

if 'dart_financials' not in mc:
    mc = mc.replace('DART_WATCH = {', dart_code + 'DART_WATCH = {')
    changes += 1
    print("✅ dart_financials 함수 추가")
else:
    print("⚠️ dart_financials 이미 있음")

# ── 2) 채점 전 DART 보완 ──────────────────────────────────
old_score = '''                    score, crit = score_fn(q)
                    # 히스토리는 이미 quote에서 가져옴
                    hist = q.get("_history", [])'''
new_score = '''                    # KR 종목: DART로 빈 재무 데이터 보완
                    if market == "kr" and DART_API_KEY:
                        try:
                            dart_fin = await dart_financials(ticker, c3)
                            if dart_fin and not dart_fin.get("dart_error"):
                                if not q.get("returnOnEquity") and dart_fin.get("dart_roe"):
                                    q["returnOnEquity"] = dart_fin["dart_roe"] / 100
                                if not q.get("debtToEquity") and dart_fin.get("dart_debt_ratio"):
                                    q["debtToEquity"] = dart_fin["dart_debt_ratio"]
                                if not q.get("operatingMargins") and dart_fin.get("dart_op_margin"):
                                    q["operatingMargins"] = dart_fin["dart_op_margin"] / 100
                                if not q.get("returnOnAssets") and dart_fin.get("dart_roa"):
                                    q["returnOnAssets"] = dart_fin["dart_roa"] / 100
                        except: pass
                    score, crit = score_fn(q)
                    # 히스토리는 이미 quote에서 가져옴
                    hist = q.get("_history", [])'''

if 'dart_financials(ticker, c3)' not in mc and old_score in mc:
    mc = mc.replace(old_score, new_score)
    changes += 1
    print("✅ 스크리너 DART 보완 로직 추가")
else:
    print("⚠️ 채점 패턴 이미 있거나 없음")

print(f"총 {changes}개 변경")
with open(mtmp, "w", encoding="utf-8") as f:
    f.write(mc)
os.replace(mtmp, msrc)
print("✅ main.py 저장")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "feat: DART dynamic corp_code + financial fallback for all KR tickers"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료! 재스크리닝:")
print("https://andrew-backend-production.up.railway.app/screener/kr?force=true")
