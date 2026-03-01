import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
msrc = os.path.join(REPO, "main.py")
mtmp = os.path.join(REPO, "main.tmp")
reqs = os.path.join(REPO, "requirements.txt")

# ── 1. requirements.txt에 anthropic 추가 ─────────────────────
with open(reqs, "r", encoding="utf-8") as f:
    req_content = f.read()

if "anthropic" not in req_content:
    with open(reqs, "a", encoding="utf-8") as f:
        f.write("\nanthropic\n")
    print("✅ requirements.txt에 anthropic 추가")
else:
    print("⏭️  anthropic 이미 있음")

# ── 2. main.py 수정 ──────────────────────────────────────────
with open(msrc, "r", encoding="utf-8") as f:
    mc = f.read()

# 2-1. ANTHROPIC_API_KEY 변수 추가 (FMP_API_KEY 줄 뒤에)
old_fmp = 'FMP_API_KEY        = os.getenv("FMP_API_KEY", "XZkyTZ3vW722F2zQTQx5454PtPGLx82o")'
new_fmp = '''FMP_API_KEY        = os.getenv("FMP_API_KEY", "XZkyTZ3vW722F2zQTQx5454PtPGLx82o")
ANTHROPIC_API_KEY  = os.getenv("Anthropic_KEY", "")'''

if old_fmp in mc and "ANTHROPIC_API_KEY" not in mc:
    mc = mc.replace(old_fmp, new_fmp)
    print("✅ ANTHROPIC_API_KEY 변수 추가")
else:
    print("⏭️  ANTHROPIC_API_KEY 이미 있음")

# 2-2. AI 분석 함수 추가 (브리핑 섹션 바로 앞에)
ai_function = '''
# ── AI 시황 분석 ──────────────────────────────────────────────
async def claude_analyze(briefing_type: str, market_data: dict, news: list, disclosures: list) -> str:
    """Claude API로 시황 분석 텍스트 생성"""
    if not ANTHROPIC_API_KEY:
        return "⚠️ ANTHROPIC_API_KEY가 설정되지 않았습니다."
    try:
        import anthropic as ac
        client = ac.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

        # 시장 데이터 요약
        mkt = market_data if isinstance(market_data, dict) else {}
        sp500  = mkt.get("SP500",  {})
        nasdaq = mkt.get("NASDAQ", {})
        kospi  = mkt.get("KOSPI",  {})
        kosdaq = mkt.get("KOSDAQ", {})
        usdkrw = mkt.get("USD/KRW",{})
        gold   = mkt.get("GOLD",   {})
        wti    = mkt.get("WTI",    {})
        us10y  = mkt.get("US10Y",  {})
        vix    = mkt.get("VIX",    {})

        def fmt(d):
            p = d.get("price", "—")
            c = d.get("change", "—")
            return f"{p} ({c}%)"

        market_summary = f"""
S&P500: {fmt(sp500)} | 나스닥: {fmt(nasdaq)}
코스피: {fmt(kospi)} | 코스닥: {fmt(kosdaq)}
USD/KRW: {fmt(usdkrw)} | VIX: {fmt(vix)}
금: {fmt(gold)} | WTI: {fmt(wti)} | 미10년물: {fmt(us10y)}
"""

        news_summary = "\\n".join([
            f"- [{n.get('source','')}] {n.get('title','')}"
            for n in news[:8]
        ])

        dart_summary = "\\n".join([
            f"- {d.get('company','')} | {d.get('title','')}"
            for d in disclosures[:5]
        ])

        if briefing_type == "morning":
            prompt = f"""너는 Andrew의 전담 투자 어시스턴트야. Andrew는 SNU 경영학과 2학년으로 글로벌 헤지펀드를 목표로 하는 투자자야.

아래 데이터를 바탕으로 오늘 아침 시황 브리핑을 작성해줘.

[전날 미국 시장 & 현재 지표]
{market_summary}

[주요 뉴스]
{news_summary}

[주요 공시]
{dart_summary}

작성 형식:
1. **한줄 요약** — 오늘 시장 핵심 한 문장
2. **미국 시장 흐름** — 전날 뭐가 움직였고 왜인지 (2-3문장)
3. **한국 시장 전망** — 오늘 국장에 미칠 영향 (2-3문장)
4. **오늘 주목할 포인트** — 체크해야 할 것 2-3가지 (불릿)
5. **Andrew's Pick** — 오늘 특히 주목할 섹터/종목 한 가지와 이유

간결하고 날카롭게, 실제 트레이더처럼 써줘. 총 300자 이내."""

        elif briefing_type == "closing":
            prompt = f"""너는 Andrew의 전담 투자 어시스턴트야.

오늘 국장 마감 기준 시황을 정리해줘.

[마감 지표]
{market_summary}

[오늘 뉴스]
{news_summary}

[오늘 공시]
{dart_summary}

작성 형식:
1. **마감 한줄 요약** — 오늘 국장 핵심 한 문장
2. **오늘 국장 흐름** — 코스피/코스닥 주요 움직임과 원인 (2-3문장)
3. **수급 포인트** — 외국인/기관 눈에 띄는 움직임 (있으면)
4. **내일 주목 포인트** — 내일 체크해야 할 것 2가지
5. **총평** — Draft 3.0 철학 관점에서 오늘 시장 한 줄 평가

간결하게, 총 300자 이내."""

        else:  # weekend
            prompt = f"""너는 Andrew의 전담 투자 어시스턴트야.

주말 사설 & 이번 주 핵심 이슈를 정리해줘.

[이번 주 시장 지표]
{market_summary}

[주요 뉴스 & 사설]
{news_summary}

[주요 공시]
{dart_summary}

작성 형식:
1. **이번 주 핵심 테마** — 시장을 움직인 핵심 이슈 2가지
2. **다음 주 캘린더** — 체크해야 할 이벤트/발표 (불릿)
3. **섹터 & 종목 인사이트** — 주목할 섹터 흐름
4. **Andrew's 주말 숙제** — 이번 주말 읽어볼 것, 분석할 것 추천
5. **한 줄 전망** — Draft 3.0 관점 다음 주 시장 전망

총 400자 이내."""

        message = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"⚠️ AI 분석 실패: {str(e)}"

'''

old_briefing_header = "# ── 브리핑 ───────────────────────────────────────────────────"
if old_briefing_header in mc and "claude_analyze" not in mc:
    mc = mc.replace(old_briefing_header, ai_function + old_briefing_header)
    print("✅ claude_analyze 함수 추가")
else:
    print("⏭️  AI 함수 이미 있음")

# 2-3. 브리핑 엔드포인트에 AI 분석 결과 추가
old_morning = '''@app.get("/briefing/morning")
async def briefing_morning():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    return {"status":"ok","type":"morning","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:5],"news":news["data"][:8]}'''

new_morning = '''@app.get("/briefing/morning")
async def briefing_morning():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    ai   = await claude_analyze("morning", mkt["data"], news["data"][:8], dart["data"][:5])
    return {"status":"ok","type":"morning","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:5],"news":news["data"][:8],
            "ai_analysis":ai}'''

old_closing = '''@app.get("/briefing/closing")
async def briefing_closing():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    return {"status":"ok","type":"closing","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:10],"news":news["data"][:6]}'''

new_closing = '''@app.get("/briefing/closing")
async def briefing_closing():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    ai   = await claude_analyze("closing", mkt["data"], news["data"][:6], dart["data"][:10])
    return {"status":"ok","type":"closing","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:10],"news":news["data"][:6],
            "ai_analysis":ai}'''

old_weekend = '''@app.get("/briefing/weekend")
async def briefing_weekend():
    news = await news_rss()
    dart = await dart_recent(days=3)
    return {"status":"ok","type":"weekend","generated_at":kst_now().isoformat(),
            "news":news["data"],"disclosures":dart["data"][:8]}'''

new_weekend = '''@app.get("/briefing/weekend")
async def briefing_weekend():
    news = await news_rss()
    dart = await dart_recent(days=3)
    mkt  = await market_overview()
    ai   = await claude_analyze("weekend", mkt["data"], news["data"], dart["data"][:8])
    return {"status":"ok","type":"weekend","generated_at":kst_now().isoformat(),
            "news":news["data"],"disclosures":dart["data"][:8],
            "ai_analysis":ai}'''

changed = 0
for old, new in [(old_morning, new_morning), (old_closing, new_closing), (old_weekend, new_weekend)]:
    if old in mc:
        mc = mc.replace(old, new)
        changed += 1

print(f"✅ 브리핑 엔드포인트 {changed}/3개 수정")

with open(mtmp, "w", encoding="utf-8") as f:
    f.write(mc)
os.replace(mtmp, msrc)

# ── 3. Git push ──────────────────────────────────────────────
for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "feat: Claude AI 시황 분석 추가 (morning/closing/weekend briefing)"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료! 배포 후 테스트:")
print("https://andrew-backend-production.up.railway.app/briefing/morning")
