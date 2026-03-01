import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
msrc = os.path.join(REPO, "main.py")
mtmp = os.path.join(REPO, "main.tmp")

with open(msrc, "r", encoding="utf-8") as f:
    mc = f.read()

# ── 브리핑 엔드포인트 3개 교체 (실제 코드 기준) ─────────────
old_morning = '''@app.get("/briefing/morning")
async def briefing_morning():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    return {"status":"ok","type":"morning","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:5],"news":news["data"][:8]}
@app.get("/briefing/closing")'''

new_morning = '''@app.get("/briefing/morning")
async def briefing_morning():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    ai   = await claude_analyze("morning", mkt["data"], news["data"][:8], dart["data"][:5])
    return {"status":"ok","type":"morning","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:5],"news":news["data"][:8],
            "ai_analysis":ai}
@app.get("/briefing/closing")'''

old_closing = '''@app.get("/briefing/closing")
async def briefing_closing():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    return {"status":"ok","type":"closing","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:10],"news":news["data"][:6]}
@app.get("/briefing/weekend")'''

new_closing = '''@app.get("/briefing/closing")
async def briefing_closing():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    ai   = await claude_analyze("closing", mkt["data"], news["data"][:6], dart["data"][:10])
    return {"status":"ok","type":"closing","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:10],"news":news["data"][:6],
            "ai_analysis":ai}
@app.get("/briefing/weekend")'''

old_weekend = '''@app.get("/briefing/weekend")
async def briefing_weekend():
    news = await news_rss()
    dart = await dart_recent(days=3)
    return {"status":"ok","type":"weekend","generated_at":kst_now().isoformat(),
            "news":news["data"],"disclosures":dart["data"][:8]}
# ── 루트 / 앱 서빙 ───────────────────────────────────────────'''

new_weekend = '''@app.get("/briefing/weekend")
async def briefing_weekend():
    news = await news_rss()
    dart = await dart_recent(days=3)
    mkt  = await market_overview()
    ai   = await claude_analyze("weekend", mkt["data"], news["data"], dart["data"][:8])
    return {"status":"ok","type":"weekend","generated_at":kst_now().isoformat(),
            "news":news["data"],"disclosures":dart["data"][:8],
            "ai_analysis":ai}
# ── 루트 / 앱 서빙 ───────────────────────────────────────────'''

changed = 0
for old, new, name in [
    (old_morning, new_morning, "morning"),
    (old_closing, new_closing, "closing"),
    (old_weekend, new_weekend, "weekend"),
]:
    if old in mc:
        mc = mc.replace(old, new)
        changed += 1
        print(f"✅ /briefing/{name} 수정")
    else:
        print(f"❌ /briefing/{name} 패턴 못 찾음")

print(f"\n총 {changed}/3개 수정")

with open(mtmp, "w", encoding="utf-8") as f:
    f.write(mc)
os.replace(mtmp, msrc)
print("✅ main.py 저장 완료")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "feat: 브리핑 엔드포인트 AI 분석 추가"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료! 배포 후 테스트:")
print("https://andrew-backend-production.up.railway.app/briefing/morning")
