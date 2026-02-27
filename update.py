import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
msrc = os.path.join(REPO, "main.py")
mtmp = os.path.join(REPO, "main.tmp")

with open(msrc, "r", encoding="utf-8") as f:
    mc = f.read()

# 핵심: 순차 DART 호출 → 병렬 사전 조회로 변경
# 채점 루프 전에 모든 KR 종목 DART 데이터를 한번에 병렬로 가져옴

old_score_block = '''            # 3. 채점
            _progress[market]["phase"] = "채점 중"
            score_fn = score_kr if market == "kr" else score_us
            results  = []
            async with httpx.AsyncClient(timeout=15) as c3:
                for ticker in tickers:
                    q = all_quotes.get(ticker, {})
                    if not q.get("regularMarketPrice"):
                        continue
                    # KR 종목: DART로 빈 재무 데이터 보완
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
                    score, crit = score_fn(q)'''

new_score_block = '''            # 3. DART 병렬 조회 (KR만, 재무 데이터 없는 종목 보완)
            dart_data = {}
            if market == "kr" and DART_API_KEY:
                _progress[market]["phase"] = "DART 재무 데이터 조회 중"
                async with httpx.AsyncClient(timeout=15) as cd:
                    tasks = {t: dart_financials(t, cd) for t in tickers}
                    for t, coro in tasks.items():
                        try:
                            dart_data[t] = await coro
                        except:
                            dart_data[t] = {}
                        await asyncio.sleep(0.05)

            # 3. 채점
            _progress[market]["phase"] = "채점 중"
            score_fn = score_kr if market == "kr" else score_us
            results  = []
            async with httpx.AsyncClient(timeout=15) as c3:
                for ticker in tickers:
                    q = all_quotes.get(ticker, {})
                    if not q.get("regularMarketPrice"):
                        continue
                    # KR 종목: DART 데이터로 빈 값 보완
                    if market == "kr" and ticker in dart_data:
                        dart_fin = dart_data[ticker]
                        if dart_fin and not dart_fin.get("dart_error"):
                            if not q.get("returnOnEquity") and dart_fin.get("dart_roe"):
                                q["returnOnEquity"] = dart_fin["dart_roe"] / 100
                            if not q.get("debtToEquity") and dart_fin.get("dart_debt_ratio"):
                                q["debtToEquity"] = dart_fin["dart_debt_ratio"]
                            if not q.get("operatingMargins") and dart_fin.get("dart_op_margin"):
                                q["operatingMargins"] = dart_fin["dart_op_margin"] / 100
                            if not q.get("returnOnAssets") and dart_fin.get("dart_roa"):
                                q["returnOnAssets"] = dart_fin["dart_roa"] / 100
                    score, crit = score_fn(q)'''

if old_score_block in mc:
    mc = mc.replace(old_score_block, new_score_block)
    print("✅ DART 병렬 조회로 변경")
else:
    print("❌ 패턴 없음")

with open(mtmp, "w", encoding="utf-8") as f:
    f.write(mc)
os.replace(mtmp, msrc)

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "perf: DART financials pre-fetch with small delay instead of sequential calls"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료! 재스크리닝:")
print("https://andrew-backend-production.up.railway.app/screener/kr?force=true")
