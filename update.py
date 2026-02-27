import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
src  = os.path.join(REPO, "main.py")
tmp  = os.path.join(REPO, "main_new.py")

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

# balance sheet 디버그 엔드포인트 추가
debug_endpoint = '''
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

'''

# /yf/debug 엔드포인트 앞에 삽입
marker = '@app.get("/yf/debug/{ticker}")'
if marker in content and "/yf/bs/" not in content:
    content = content.replace(marker, debug_endpoint + marker)
    print("✅ 디버그 엔드포인트 추가됨")
else:
    print("⚠️  이미 있거나 위치 못찾음")

with open(tmp, "w", encoding="utf-8") as f:
    f.write(content)
os.replace(tmp, src)
print("✅ main.py 저장")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "debug: balance sheet row names for KR stocks"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("🚀 완료! 배포 후: https://andrew-backend-production.up.railway.app/yf/bs/005930.KS")
