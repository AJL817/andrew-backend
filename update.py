import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
src  = os.path.join(REPO, "main.py")
tmp  = os.path.join(REPO, "main_new.py")

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

changes = 0

# 1) version 4.1로 업데이트 (배포 확인용)
if '"version":"4.0"' in content:
    content = content.replace('"version":"4.0"', '"version":"4.1"')
    changes += 1
    print("✅ version 4.1")
elif '"version": "4.0"' in content:
    content = content.replace('"version": "4.0"', '"version": "4.1"')
    changes += 1
    print("✅ version 4.1")

# 2) balance sheet 디버그 엔드포인트
if "/yf/bs/" not in content:
    bs_debug = '''
@app.get("/yf/bs/{ticker}")
async def yf_bs_debug(ticker: str):
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor
    import asyncio
    def get_bs():
        t = yf.Ticker(ticker)
        result = {}
        try:
            bs = t.quarterly_balance_sheet
            if bs is not None and not bs.empty:
                result["bs_rows"] = list(bs.index)
                result["bs_sample"] = {str(k): float(bs.loc[k].dropna().iloc[0]) 
                                       for k in list(bs.index)[:15] 
                                       if not bs.loc[k].isna().all()}
            else:
                result["bs_rows"] = []
        except Exception as e:
            result["bs_error"] = str(e)
        try:
            inc = t.quarterly_income_stmt
            if inc is not None and not inc.empty:
                result["inc_rows"] = list(inc.index)
                result["inc_sample"] = {str(k): float(inc.loc[k].dropna().iloc[0])
                                        for k in list(inc.index)[:15]
                                        if not inc.loc[k].isna().all()}
            else:
                result["inc_rows"] = []
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
    # /yf/debug 바로 앞에 삽입
    marker = '@app.get("/yf/debug/{ticker}")'
    if marker in content:
        content = content.replace(marker, bs_debug + marker)
        changes += 1
        print("✅ /yf/bs 엔드포인트 추가")

print(f"총 {changes}개 변경")

with open(tmp, "w", encoding="utf-8") as f:
    f.write(content)
os.replace(tmp, src)
print("✅ main.py 저장")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "v4.1: add bs debug endpoint"],
    ["git", "-C", REPO, "push", "--force"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 배포 완료! 2분 후 확인:")
print("  버전확인: https://andrew-backend-production.up.railway.app/")
print("  BS확인:   https://andrew-backend-production.up.railway.app/yf/bs/005930.KS")
