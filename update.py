import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
msrc = os.path.join(REPO, "main.py")
mtmp = os.path.join(REPO, "main.tmp")
hsrc = os.path.join(REPO, "andrew.html")
htmp = os.path.join(REPO, "andrew.tmp")
reqs = os.path.join(REPO, "requirements.txt")

# ════════════════════════════════════════
#  1. requirements.txt
# ════════════════════════════════════════
with open(reqs, "r", encoding="utf-8") as f:
    req_content = f.read()
if "anthropic" not in req_content:
    with open(reqs, "a", encoding="utf-8") as f:
        f.write("\nanthropic\n")
    print("✅ requirements.txt — anthropic 추가")
else:
    print("⏭️  anthropic 이미 있음")

# ════════════════════════════════════════
#  2. main.py
# ════════════════════════════════════════
with open(msrc, "r", encoding="utf-8") as f:
    mc = f.read()

# 2-1. ANTHROPIC_API_KEY 변수
old_fmp = 'FMP_API_KEY        = os.getenv("FMP_API_KEY", "XZkyTZ3vW722F2zQTQx5454PtPGLx82o")'
new_fmp = '''FMP_API_KEY        = os.getenv("FMP_API_KEY", "XZkyTZ3vW722F2zQTQx5454PtPGLx82o")
ANTHROPIC_API_KEY  = os.getenv("Anthropic_KEY", "")'''
if old_fmp in mc and "ANTHROPIC_API_KEY" not in mc:
    mc = mc.replace(old_fmp, new_fmp)
    print("✅ ANTHROPIC_API_KEY 변수 추가")
else:
    print("⏭️  ANTHROPIC_API_KEY 이미 있음")

# 2-2. claude_analyze 함수 + 신규 엔드포인트 (브리핑 헤더 앞에 삽입)
ai_block = '''
# ── AI 시황 분석 ──────────────────────────────────────────────
async def claude_analyze(briefing_type: str, market_data: dict, news: list, disclosures: list) -> str:
    if not ANTHROPIC_API_KEY:
        return "⚠️ ANTHROPIC_API_KEY가 설정되지 않았습니다."
    try:
        import anthropic as ac
        client = ac.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        mkt = market_data if isinstance(market_data, dict) else {}

        def fmt(key):
            v = mkt.get(key, {})
            p = v.get("price", "—")
            c = v.get("change_pct", "—")
            sign = "+" if isinstance(c, (int, float)) and c >= 0 else ""
            return f"{p} ({sign}{c}%)"

        mkt_summary = f"""S&P500: {fmt('sp500')} | 나스닥: {fmt('nasdaq')} | 다우: {fmt('dow')}
코스피: {fmt('kospi')} | 코스닥: {fmt('kosdaq')} | USD/KRW: {fmt('usdkrw')}
VIX: {fmt('vix')} | 금: {fmt('gold')} | WTI: {fmt('wti')} | 미10년물: {fmt('us10y')}"""

        news_txt  = "\\n".join([f"- [{n.get('source','')}] {n.get('title','')}" for n in news[:8]]) or "없음"
        dart_txt  = "\\n".join([f"- {d.get('company','')} | {d.get('title','')}" for d in disclosures[:5]]) or "없음"

        prompts = {
            "morning": f"""너는 Andrew의 전담 투자 어시스턴트야. Draft 3.0 철학(버핏+하워드막스+카너먼) 기반으로 분석해줘.
[시장] {mkt_summary}
[뉴스] {news_txt}
[공시] {dart_txt}
4개 섹션으로 모닝 브리핑 (한국어, 각 2-3문장):
📊 시황 변화 — 전날 미장 흐름과 오늘 주목할 변화
🔍 핵심 이슈 — 오늘 가장 중요한 이슈와 시장 영향
⚠️ 투자자 시사점 — VIX 기준 공포·탐욕 구간, 주목 섹터
💬 오늘의 한 마디 — 하워드 막스 또는 버핏 원칙으로 한 문장 요약""",

            "closing": f"""너는 Andrew의 전담 투자 어시스턴트야. 오늘 국장 마감을 Draft 3.0 관점으로 분석해줘.
[시장] {mkt_summary}
[뉴스] {news_txt}
[공시] {dart_txt}
4개 섹션 (한국어, 각 2-3문장):
📊 오늘 국장 총평 — 코스피·코스닥 흐름과 원인
🔍 오늘의 핵심 — 시장을 움직인 주요 이슈
🌏 내일 미장 포인트 — 오늘 흐름이 내일 미장에 시사하는 점
⚠️ Draft 3.0 관점 — 매수적극·분할매수·관망·회피 중 현재 구간""",

            "weekend": f"""너는 Andrew의 전담 투자 어시스턴트야. 주말 주간 정리를 Draft 3.0 관점으로 작성해줘.
[시장] {mkt_summary}
[뉴스] {news_txt}
[공시] {dart_txt}
4개 섹션 (한국어, 각 2-3문장):
📊 이번 주 시장 총평 — 주간 지수 흐름과 변화 의미
🔍 이번 주 핵심 이슈 — 가장 중요한 이슈 2-3개
📅 다음 주 주목 포인트 — 예정 이벤트와 주목 섹터
⚠️ 포트폴리오 점검 — Draft 3.0 기준 현재 사이클 위치와 대응 전략""",

            "dashboard": f"""너는 Andrew의 전담 투자 어시스턴트야. 현재 시장 전체를 한눈에 요약해줘.
[시장] {mkt_summary}
[뉴스] {news_txt}
3개 섹션 (한국어, 각 2문장, 간결하게):
📊 지금 시장 — 미국·한국 시장 현재 흐름 핵심 요약
⚠️ 리스크 레이더 — VIX·금리·환율 기준 현재 위험 신호
💡 오늘의 포인트 — Draft 3.0 관점 지금 당장 주목할 것""",

            "dart": f"""너는 Andrew의 전담 투자 어시스턴트야. 아래 DART 공시들을 투자자 관점으로 해석해줘.
[공시 목록]
{dart_txt}
[시장 맥락] {mkt_summary}
3개 섹션 (한국어):
📋 주요 공시 요약 — 오늘 가장 중요한 공시 2-3개와 의미
🔍 투자 시사점 — 이 공시들이 주가·섹터에 미칠 영향
⚠️ 주의할 공시 — 리스크 관점에서 체크해야 할 것"""
        }

        message = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompts.get(briefing_type, prompts["dashboard"])}]
        )
        return message.content[0].text
    except Exception as e:
        return f"⚠️ AI 분석 실패: {str(e)}"


@app.get("/ai/dashboard")
async def ai_dashboard():
    mkt  = await market_overview()
    news = await news_rss()
    ai   = await claude_analyze("dashboard", mkt["data"], news["data"][:8], [])
    return {"status":"ok","ai_analysis":ai,"generated_at":kst_now().isoformat()}


@app.get("/ai/dart")
async def ai_dart(days: int = 7):
    dart = await dart_recent(days=days)
    mkt  = await market_overview()
    ai   = await claude_analyze("dart", mkt["data"], [], dart["data"])
    return {"status":"ok","ai_analysis":ai,"generated_at":kst_now().isoformat()}

'''

old_briefing_header = "# ── 브리핑 ───────────────────────────────────────────────────"
if old_briefing_header in mc and "claude_analyze" not in mc:
    mc = mc.replace(old_briefing_header, ai_block + old_briefing_header)
    print("✅ claude_analyze 함수 + /ai/dashboard + /ai/dart 엔드포인트 추가")
else:
    print("⏭️  AI 블록 이미 있거나 헤더 못 찾음")

# 2-3. 브리핑 엔드포인트에 ai_analysis 추가
replacements = [
    (
        '''@app.get("/briefing/morning")
async def briefing_morning():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    return {"status":"ok","type":"morning","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:5],"news":news["data"][:8]}''',
        '''@app.get("/briefing/morning")
async def briefing_morning():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    ai   = await claude_analyze("morning", mkt["data"], news["data"][:8], dart["data"][:5])
    return {"status":"ok","type":"morning","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:5],"news":news["data"][:8],
            "ai_analysis":ai}'''
    ),
    (
        '''@app.get("/briefing/closing")
async def briefing_closing():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    return {"status":"ok","type":"closing","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:10],"news":news["data"][:6]}''',
        '''@app.get("/briefing/closing")
async def briefing_closing():
    mkt  = await market_overview()
    dart = await dart_recent(days=1)
    news = await news_rss()
    ai   = await claude_analyze("closing", mkt["data"], news["data"][:6], dart["data"][:10])
    return {"status":"ok","type":"closing","generated_at":kst_now().isoformat(),
            "market":mkt["data"],"disclosures":dart["data"][:10],"news":news["data"][:6],
            "ai_analysis":ai}'''
    ),
    (
        '''@app.get("/briefing/weekend")
async def briefing_weekend():
    news = await news_rss()
    dart = await dart_recent(days=3)
    return {"status":"ok","type":"weekend","generated_at":kst_now().isoformat(),
            "news":news["data"],"disclosures":dart["data"][:8]}''',
        '''@app.get("/briefing/weekend")
async def briefing_weekend():
    news = await news_rss()
    dart = await dart_recent(days=3)
    mkt  = await market_overview()
    ai   = await claude_analyze("weekend", mkt["data"], news["data"], dart["data"][:8])
    return {"status":"ok","type":"weekend","generated_at":kst_now().isoformat(),
            "news":news["data"],"disclosures":dart["data"][:8],
            "ai_analysis":ai}'''
    ),
]
changed = sum(1 for old, new in replacements if old in mc)
for old, new in replacements:
    mc = mc.replace(old, new)
print(f"✅ 브리핑 엔드포인트 {changed}/3개 수정")

with open(mtmp, "w", encoding="utf-8") as f:
    f.write(mc)
os.replace(mtmp, msrc)
print("✅ main.py 저장 완료")

# ════════════════════════════════════════
#  3. andrew.html
# ════════════════════════════════════════
with open(hsrc, "r", encoding="utf-8") as f:
    hc = f.read()

# 3-1. generateAIAnalysis 함수 교체 (백엔드 호출 방식으로)
old_fn = """async function generateAIAnalysis(targetId, marketData, newsItems, dartItems, type) {
  const el = document.getElementById(targetId);
  if (!el) return;
  const mkt = marketData || {};
  const fmt = (k) => { const v = mkt[k]; if (!v) return '-'; const p = Number(v.price).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}); const c = v.change_pct != null ? (v.change_pct >= 0 ? '+' : '') + v.change_pct + '%' : ''; return `${p} (${c})`; };
  const mktSummary = `S&P500: ${fmt('sp500')}, 나스닥: ${fmt('nasdaq')}, 코스피: ${fmt('kospi')}, 코스닥: ${fmt('kosdaq')}, USD/KRW: ${fmt('usdkrw')}, 미10년물: ${fmt('us10y')}%, VIX: ${fmt('vix')}, VKOSPI: ${fmt('vkospi')}, 금: ${fmt('gold')}, 은: ${fmt('silver')}, WTI: ${fmt('wti')}`;
  const newsSummary = (newsItems||[]).slice(0,8).map(n=>`- ${n.title}`).join('\\n') || '없음';
  const dartSummary = (dartItems||[]).slice(0,5).map(d=>`- [${d.company}] ${d.title}`).join('\\n') || '없음';
  const prompts = {
    morning: `당신은 Andrew의 개인 투자 어시스턴트입니다. Andrew는 버핏 가치투자 + 하워드 막스 사이클 + 카너먼 행동경제학 기반 Draft 3.0 철학을 가진 투자자입니다.\\n\\n[시장 데이터]\\n${mktSummary}\\n\\n[주요 뉴스]\\n${newsSummary}\\n\\n[공시]\\n${dartSummary}\\n\\n아래 4개 섹션으로 브리핑해주세요 (각 2-3문장, 한국어):\\n📊 시황 변화 — 전날 미장 움직임의 의미, 주요 지수 흐름 해석\\n🔍 핵심 이슈 — 오늘 가장 중요한 이슈와 시장 영향\\n⚠️ 투자자 시사점 — VIX/VKOSPI 기준 공포·탐욕 구간, 주목할 섹터 힌트\\n💬 오늘의 한 마디 — 하워드 막스 또는 버핏 원칙으로 오늘 시장 한 문장 요약`,
    closing: `당신은 Andrew의 개인 투자 어시스턴트입니다.\\n\\n[마감 데이터]\\n${mktSummary}\\n\\n[뉴스]\\n${newsSummary}\\n\\n[공시]\\n${dartSummary}\\n\\n아래 4개 섹션으로 마감 브리핑 (각 2-3문장, 한국어):\\n📊 오늘 국장 총평 — 코스피·코스닥 흐름, 특이 섹터 의미\\n🔍 오늘의 핵심 — 시장을 움직인 주요 이슈 분석\\n🌏 내일 미장 포인트 — 오늘 흐름이 내일 미장에 시사하는 점\\n⚠️ Draft 3.0 관점 — 매수 적극·분할매수·관망·회피 중 어느 구간인지 판단`,
    weekend: `당신은 Andrew의 개인 투자 어시스턴트입니다.\\n\\n[시장 데이터]\\n${mktSummary}\\n\\n[이번 주 뉴스]\\n${newsSummary}\\n\\n[공시]\\n${dartSummary}\\n\\n아래 4개 섹션으로 주간 정리 (각 2-3문장, 한국어):\\n📊 이번 주 시장 총평 — 주간 주요 지수 흐름과 변화 의미\\n🔍 이번 주 핵심 이슈 — 가장 중요했던 이슈 2-3개와 시장 영향\\n📅 다음 주 주목 포인트 — FOMC·실적 등 예정 이벤트, 주목 섹터\\n⚠️ 포트폴리오 점검 — Draft 3.0 기준 현재 사이클 위치와 대응 전략`
  };
  try {
    el.innerHTML = '<div class="ai-loading"><div class="ai-dot"></div> AI가 시황을 분석하고 있어요...</div>';
    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'claude-sonnet-4-20250514', max_tokens: 1000, messages: [{ role: 'user', content: prompts[type] }] })
    });
    const data = await resp.json();
    const text = data.content?.[0]?.text || '분석 실패';
    const formatted = text.replace(/^(📊|🔍|⚠️|🌏|📅|💬)[^\\n]*/gm, m => `<span class="ai-label">${m}</span>`).replace(/\\n/g, '<br>');
    el.innerHTML = `<div class="ai-analysis-text">${formatted}</div>`;
  } catch(e) { el.innerHTML = '<div style="color:var(--text3);font-size:12px;">AI 분석 실패: ' + e.message + '</div>'; }
}"""

new_fn = """async function generateAIAnalysis(targetId, type) {
  const el = document.getElementById(targetId);
  if (!el) return;
  el.innerHTML = '<div class="ai-loading"><div class="ai-dot"></div> AI가 시황을 분석하고 있어요...</div>';
  const endpointMap = {
    morning: '/briefing/morning',
    closing: '/briefing/closing',
    weekend: '/briefing/weekend',
    dashboard: '/ai/dashboard',
    dart: '/ai/dart'
  };
  try {
    const resp = await fetch(BACKEND + (endpointMap[type] || '/ai/dashboard'));
    const data = await resp.json();
    const text = data.ai_analysis || '분석 결과 없음';
    if (text.startsWith('⚠️')) {
      el.innerHTML = `<div style="color:var(--text3);font-size:12px;">${text}</div>`;
      return;
    }
    const formatted = text
      .replace(/\\*\\*(.+?)\\*\\*/g, '<strong style="color:var(--orange)">$1</strong>')
      .replace(/^#{1,3}\\s+(.+)$/gm, '<strong style="color:var(--accent)">$1</strong>')
      .replace(/^(📊|🔍|⚠️|🌏|📅|💬|🎯|📈|📉|📋|💡)[^\\n]*/gm, m => `<span class="ai-label">${m}</span>`)
      .replace(/\\n/g, '<br>');
    el.innerHTML = `<div class="ai-analysis-text">${formatted}</div>`;
  } catch(e) {
    el.innerHTML = '<div style="color:var(--text3);font-size:12px;">AI 분석 실패: ' + e.message + '</div>';
  }
}"""

if old_fn in hc:
    hc = hc.replace(old_fn, new_fn)
    print("✅ generateAIAnalysis 함수 교체")
else:
    print("❌ generateAIAnalysis 패턴 못 찾음")

# 3-2. loadMorning 교체
old_morning = """async function loadMorning() {
  const now = new Date();
  document.getElementById('morning-time').textContent = now.toLocaleDateString('ko-KR', {year:'numeric',month:'long',day:'numeric',weekday:'long'});
  await loadMarket();
  const newsData = await loadNews('morning-news', 8);
  await loadDart(1);
  try { const mktJ = await (await fetch(BACKEND + '/market/overview')).json(); const dartJ = await (await fetch(BACKEND + '/dart/recent?days=1')).json(); generateAIAnalysis('morning-analysis', mktJ.data, newsData, dartJ.data, 'morning'); } catch(e) {}
}"""
new_morning = """async function loadMorning() {
  const now = new Date();
  document.getElementById('morning-time').textContent = now.toLocaleDateString('ko-KR', {year:'numeric',month:'long',day:'numeric',weekday:'long'});
  await loadMarket();
  await loadNews('morning-news', 8);
  await loadDart(1);
  generateAIAnalysis('morning-analysis', 'morning');
}"""
if old_morning in hc:
    hc = hc.replace(old_morning, new_morning)
    print("✅ loadMorning 교체")
else:
    print("❌ loadMorning 패턴 못 찾음")

# 3-3. loadClosing 교체
old_closing = """async function loadClosing() {
  const now = new Date();
  document.getElementById('closing-time').textContent = now.toLocaleDateString('ko-KR', {year:'numeric',month:'long',day:'numeric',weekday:'long'});
  await loadMarket();
  const newsData = await loadNews('closing-news', 8);
  await loadDart(1);
  try { const mktJ = await (await fetch(BACKEND + '/market/overview')).json(); const dartJ = await (await fetch(BACKEND + '/dart/recent?days=1')).json(); generateAIAnalysis('closing-analysis', mktJ.data, newsData, dartJ.data, 'closing'); } catch(e) {}
}"""
new_closing = """async function loadClosing() {
  const now = new Date();
  document.getElementById('closing-time').textContent = now.toLocaleDateString('ko-KR', {year:'numeric',month:'long',day:'numeric',weekday:'long'});
  await loadMarket();
  await loadNews('closing-news', 8);
  await loadDart(1);
  generateAIAnalysis('closing-analysis', 'closing');
}"""
if old_closing in hc:
    hc = hc.replace(old_closing, new_closing)
    print("✅ loadClosing 교체")
else:
    print("❌ loadClosing 패턴 못 찾음")

# 3-4. loadWeekend 교체
old_weekend = """async function loadWeekend() {
  const now = new Date();
  document.getElementById('weekend-time').textContent = now.toLocaleDateString('ko-KR', {year:'numeric',month:'long',day:'numeric',weekday:'long'});
  const newsData = await loadNews('weekend-news', 12);
  const r = await fetch(BACKEND + '/dart/recent?days=7').catch(()=>({json:()=>({data:[]})}));
  const j = await r.json();
  renderDartList(j.data, 'weekend-dart');
  try { const mktJ = await (await fetch(BACKEND + '/market/overview')).json(); generateAIAnalysis('weekend-analysis', mktJ.data, newsData, j.data, 'weekend'); } catch(e) {}
}"""
new_weekend = """async function loadWeekend() {
  const now = new Date();
  document.getElementById('weekend-time').textContent = now.toLocaleDateString('ko-KR', {year:'numeric',month:'long',day:'numeric',weekday:'long'});
  await loadNews('weekend-news', 12);
  const r = await fetch(BACKEND + '/dart/recent?days=7').catch(()=>({json:()=>({data:[]})}));
  const j = await r.json();
  renderDartList(j.data, 'weekend-dart');
  generateAIAnalysis('weekend-analysis', 'weekend');
}"""
if old_weekend in hc:
    hc = hc.replace(old_weekend, new_weekend)
    print("✅ loadWeekend 교체")
else:
    print("❌ loadWeekend 패턴 못 찾음")

# 3-5. 대시보드에 AI 분석 박스 + loadMarket에 AI 트리거 추가
old_dash_head = """  <!-- ══ 대시보드 ══ -->
  <div id="sec-dashboard" class="section active">
    <div class="section-head">
      <h2>📊 마켓 오버뷰 <span class="sub" id="mkt-updated"></span></h2>
      <button class="refresh-btn" onclick="loadMarket()">↻ 새로고침</button>
    </div>"""
new_dash_head = """  <!-- ══ 대시보드 ══ -->
  <div id="sec-dashboard" class="section active">
    <div class="section-head">
      <h2>📊 마켓 오버뷰 <span class="sub" id="mkt-updated"></span></h2>
      <button class="refresh-btn" onclick="loadMarket()">↻ 새로고침</button>
    </div>
    <div class="ai-analysis" id="dashboard-analysis"><div class="ai-loading"><div class="ai-dot"></div> AI가 시황을 분석하고 있어요...</div></div>"""
if old_dash_head in hc:
    hc = hc.replace(old_dash_head, new_dash_head)
    print("✅ 대시보드 AI 분석 박스 추가")
else:
    print("❌ 대시보드 헤더 패턴 못 찾음")

# 3-6. DART 탭에 AI 분석 박스 추가
old_dart_head = """  <!-- ══ DART 공시 ══ -->
  <div id="sec-dart" class="section">
    <div class="section-head">
      <h2>📋 DART 전자공시 실시간</h2>
      <div style="display:flex;gap:8px;align-items:center;">
        <select id="dart-days" onchange="loadDartFull()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 10px;border-radius:4px;font-size:11px;cursor:pointer;">
          <option value="3">최근 3일</option>
          <option value="7" selected>최근 7일</option>
          <option value="14">최근 14일</option>
          <option value="30">최근 30일</option>
        </select>
        <button class="refresh-btn" onclick="loadDartFull()">↻ 새로고침</button>
      </div>
    </div>
    <div class="card" id="dart-full-list">"""
new_dart_head = """  <!-- ══ DART 공시 ══ -->
  <div id="sec-dart" class="section">
    <div class="section-head">
      <h2>📋 DART 전자공시 실시간</h2>
      <div style="display:flex;gap:8px;align-items:center;">
        <select id="dart-days" onchange="loadDartFull()" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 10px;border-radius:4px;font-size:11px;cursor:pointer;">
          <option value="3">최근 3일</option>
          <option value="7" selected>최근 7일</option>
          <option value="14">최근 14일</option>
          <option value="30">최근 30일</option>
        </select>
        <button class="refresh-btn" onclick="loadDartFull()">↻ 새로고침</button>
      </div>
    </div>
    <div class="ai-analysis" id="dart-analysis"><div class="ai-loading"><div class="ai-dot"></div> AI가 공시를 분석하고 있어요...</div></div>
    <div class="card" id="dart-full-list">"""
if old_dart_head in hc:
    hc = hc.replace(old_dart_head, new_dart_head)
    print("✅ DART AI 분석 박스 추가")
else:
    print("❌ DART 헤더 패턴 못 찾음")

# 3-7. loadMarket에 dashboard AI 트리거, loadDartFull에 dart AI 트리거 추가
old_loadmarket_end = """  } catch(e) { console.error(e); }
}

// ── DART 로드 ────────────────────────────────────────"""
new_loadmarket_end = """  } catch(e) { console.error(e); }
  // 대시보드 탭이 활성화돼 있을 때만 AI 분석 갱신
  if (document.getElementById('sec-dashboard').classList.contains('active')) {
    generateAIAnalysis('dashboard-analysis', 'dashboard');
  }
}

// ── DART 로드 ────────────────────────────────────────"""
if old_loadmarket_end in hc:
    hc = hc.replace(old_loadmarket_end, new_loadmarket_end)
    print("✅ loadMarket에 dashboard AI 트리거 추가")
else:
    print("❌ loadMarket 끝부분 패턴 못 찾음")

old_loaddartfull_end = """async function loadDartFull() {
  const days = document.getElementById('dart-days')?.value || 7;
  try {
    const r = await fetch(BACKEND + '/dart/recent?days=' + days);
    const j = await r.json();
    renderDartList(j.data, 'dart-full-list');
  } catch(e) {}
}"""
new_loaddartfull_end = """async function loadDartFull() {
  const days = document.getElementById('dart-days')?.value || 7;
  try {
    const r = await fetch(BACKEND + '/dart/recent?days=' + days);
    const j = await r.json();
    renderDartList(j.data, 'dart-full-list');
    generateAIAnalysis('dart-analysis', 'dart');
  } catch(e) {}
}"""
if old_loaddartfull_end in hc:
    hc = hc.replace(old_loaddartfull_end, new_loaddartfull_end)
    print("✅ loadDartFull에 dart AI 트리거 추가")
else:
    print("❌ loadDartFull 패턴 못 찾음")

# 3-8. switchTab에 dart/dashboard AI 트리거 추가
old_switchtab = """  if (name === 'kr') {
    if (screenerCache.kr.length === 0) loadScreener('kr');
    else { renderScreenerCards(screenerCache.kr, 'kr'); loadScreener('kr'); }
  }
  if (name === 'us') {
    if (screenerCache.us.length === 0) loadScreener('us');
    else { renderScreenerCards(screenerCache.us, 'us'); loadScreener('us'); }
  }
};"""
new_switchtab = """  if (name === 'kr') {
    if (screenerCache.kr.length === 0) loadScreener('kr');
    else { renderScreenerCards(screenerCache.kr, 'kr'); loadScreener('kr'); }
  }
  if (name === 'us') {
    if (screenerCache.us.length === 0) loadScreener('us');
    else { renderScreenerCards(screenerCache.us, 'us'); loadScreener('us'); }
  }
  if (name === 'dart') loadDartFull();
  if (name === 'morning') loadMorning();
  if (name === 'closing') loadClosing();
  if (name === 'weekend') loadWeekend();
};"""
if old_switchtab in hc:
    hc = hc.replace(old_switchtab, new_switchtab)
    print("✅ switchTab에 탭 자동 로드 추가")
else:
    print("❌ switchTab 패턴 못 찾음")

with open(htmp, "w", encoding="utf-8") as f:
    f.write(hc)
os.replace(htmp, hsrc)
print("✅ andrew.html 저장 완료")

# ════════════════════════════════════════
#  4. Git push
# ════════════════════════════════════════
for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "feat: AI 시황분석 전 탭 확장 (dashboard, dart, morning, closing, weekend)"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료!")
print("https://andrew-backend-production.up.railway.app/app")
