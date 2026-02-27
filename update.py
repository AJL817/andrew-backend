import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
msrc = os.path.join(REPO, "main.py")
mtmp = os.path.join(REPO, "main.tmp")

with open(msrc, "r", encoding="utf-8") as f:
    mc = f.read()

# dart_financials 함수에서 하드코딩 없으면 DART API로 자동 조회하도록 교체
old = '''async def dart_financials(ticker: str, client: httpx.AsyncClient) -> dict:
    """DART 사업보고서에서 ROE, 부채비율, 영업이익률 등 직접 계산"""
    if not DART_API_KEY:
        return {}
    corp_code = KR_TICKER_TO_CORP.get(ticker, "")
    if not corp_code:
        return {}'''

new = '''_dart_corp_cache: dict = {}

async def dart_financials(ticker: str, client: httpx.AsyncClient) -> dict:
    """DART 사업보고서에서 ROE, 부채비율, 영업이익률 등 직접 계산"""
    if not DART_API_KEY:
        return {}
    # 캐시 확인
    if ticker in _dart_corp_cache:
        corp_code = _dart_corp_cache[ticker]
    else:
        # 하드코딩 우선, 없으면 DART company API로 자동 조회
        corp_code = KR_TICKER_TO_CORP.get(ticker, "")
        if not corp_code:
            stock_code = ticker.split(".")[0]  # "251270.KQ" → "251270"
            try:
                r = await client.get(
                    "https://opendart.fss.or.kr/api/company.json",
                    params={"crtfc_key": DART_API_KEY, "stock_code": stock_code},
                    timeout=8,
                )
                d = r.json()
                if d.get("status") == "000":
                    corp_code = d.get("corp_code", "")
            except:
                pass
        _dart_corp_cache[ticker] = corp_code
    if not corp_code:
        return {}'''

if old in mc:
    mc = mc.replace(old, new)
    print("✅ dart_financials 동적 조회 추가")
else:
    print("❌ 패턴 없음")

with open(mtmp, "w", encoding="utf-8") as f:
    f.write(mc)
os.replace(mtmp, msrc)

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "fix: dart_financials dynamic corp_code via DART company API"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료! 재스크리닝:")
print("https://andrew-backend-production.up.railway.app/screener/kr?force=true")
