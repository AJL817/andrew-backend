import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"

# ── main.py: MARKET_TICKERS에 silver/vix/vkospi 추가 ──
msrc = os.path.join(REPO, "main.py")
mtmp = os.path.join(REPO, "main.tmp")
with open(msrc, "r", encoding="utf-8") as f:
    mc = f.read()

old_t = '"gold":"GC=F","wti":"CL=F","copper":"HG=F",'
new_t = '"gold":"GC=F","silver":"SI=F","wti":"CL=F","copper":"HG=F","vix":"^VIX","vkospi":"^VKOSPI",'
if 'silver' not in mc:
    mc = mc.replace(old_t, new_t)
    print("✅ MARKET_TICKERS 수정")
else:
    print("⚠️ main.py 이미 수정됨")

with open(mtmp, "w", encoding="utf-8") as f:
    f.write(mc)
os.replace(mtmp, msrc)

# ── andrew.html: 전체 패치 ──
hsrc = os.path.join(REPO, "andrew.html")
htmp = os.path.join(REPO, "andrew.tmp")
with open(hsrc, "r", encoding="utf-8") as f:
    hc = f.read().replace('\r\n', '\n')

changes = []

# CSS
if '.ai-analysis' not in hc:
    css = """\n.ai-analysis {
  background: linear-gradient(135deg, rgba(0,255,136,.06) 0%, rgba(88,166,255,.06) 100%);
  border: 1px solid rgba(0,255,136,.25); border-radius: 8px; padding: 16px; margin-bottom: 16px;
}
.ai-analysis::before { content: '⬡ AI 시황 분석'; font-size: 10px; font-weight: 700; color: var(--accent); letter-spacing: 1px; display: block; margin-bottom: 10px; }
.ai-analysis-text { font-size: 13px; color: var(--text); line-height: 1.8; }
.ai-label { font-size: 11px; font-weight: 700; color: var(--accent); margin: 10px 0 3px; display: block; }
.ai-loading { display: flex; align-items: center; gap: 8px; color: var(--text3); font-size: 12px; }
.ai-dot { width:6px;height:6px;border-radius:50%;background:var(--accent);animation:aipulse 1s infinite; }
@keyframes aipulse { 0%,100%{opacity:.3} 50%{opacity:1} }\n"""
    hc = hc.replace('</style>', css + '\n</style>')
    changes.append("CSS")

# 대시보드 silver/vix/vkospi 타일
old_d = '<div class="mkt-tile"><div class="mkt-label">구리 (Copper)</div><div class="mkt-val" id="m-copper">—</div><div class="mkt-chg" id="m-copper-c">—</div></div>'
if 'id="m-silver"' not in hc and old_d in hc:
    hc = hc.replace(old_d, old_d + '\n<div class="mkt-tile"><div class="mkt-label">은 (Silver)</div><div class="mkt-val" id="m-silver">—</div><div class="mkt-chg" id="m-silver-c">—</div></div>\n<div class="mkt-tile"><div class="mkt-label">VIX 공포지수</div><div class="mkt-val" id="m-vix">—</div><div class="mkt-chg" id="m-vix-c">—</div></div>\n<div class="mkt-tile"><div class="mkt-label">VKOSPI</div><div class="mkt-val" id="m-vkospi">—</div><div class="mkt-chg" id="m-vkospi-c">—</div></div>')
    changes.append("대시보드 타일")

# JS map
old_map = "      ['copper','m-copper','m-copper-c',null,null,','],\n    ];"
if "'vix','m-vix'" not in hc and old_map in hc:
    hc = hc.replace(old_map, "      ['copper','m-copper','m-copper-c',null,null,','],\n      ['silver','m-silver','m-silver-c','tk-silver','tk-silver-chg',','],\n      ['vix','m-vix','m-vix-c','tk-vix','tk-vix-chg',''],\n      ['vkospi','m-vkospi','m-vkospi-c',null,null,''],\n    ];")
    changes.append("JS map")

# 티커바
old_tk = 'id="tk-gold-chg">—</span></div>\n    <div class="ticker-item"><span class="ticker-name">WTI</span>'
if 'tk-silver' not in hc and old_tk in hc:
    hc = hc.replace(old_tk, 'id="tk-gold-chg">—</span></div>\n    <div class="ticker-item"><span class="ticker-name">은</span><span class="ticker-val" id="tk-silver">—</span><span class="ticker-chg" id="tk-silver-chg">—</span></div>\n    <div class="ticker-item"><span class="ticker-name">VIX</span><span class="ticker-val" id="tk-vix">—</span><span class="ticker-chg" id="tk-vix-chg">—</span></div>\n    <div class="ticker-item"><span class="ticker-name">WTI</span>')
    changes.append("티커바")

# mm-map
old_mm = "['gold','mm-gold','mm-gold-c'],['wti','mm-wti','mm-wti-c'],"
if "'silver','mm-silver'" not in hc and old_mm in hc:
    hc = hc.replace(old_mm, "['gold','mm-gold','mm-gold-c'],['silver','mm-silver','mm-silver-c'],['wti','mm-wti','mm-wti-c'],['vix','mm-vix','mm-vix-c'],")
    changes.append("mm-map")

# AI div 삽입
for aid, marker in [
    ('morning-analysis', '    <div class="grid-2" style="margin-bottom:16px;">\n      <div class="card morning-card">'),
    ('closing-analysis', '    <div class="grid-2" style="margin-bottom:16px;">\n      <div class="card closing-card">'),
    ('weekend-analysis', '    <div class="grid-2">\n      <div class="card weekend-card">\n        <div class="card-title">📰 주요 뉴스'),
]:
    if f'id="{aid}"' not in hc and marker in hc:
        hc = hc.replace(marker, f'    <div class="ai-analysis" id="{aid}"><div class="ai-loading"><div class="ai-dot"></div> AI가 시황을 분석하고 있어요...</div></div>\n' + marker)
        changes.append(f"{aid} div")

# AI 함수
if 'generateAIAnalysis' not in hc:
    ai_fn = r"""
async function generateAIAnalysis(targetId, marketData, newsItems, dartItems, type) {
  const el = document.getElementById(targetId);
  if (!el) return;
  const mkt = marketData || {};
  const fmt = (k) => { const v = mkt[k]; if (!v) return '-'; const p = Number(v.price).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}); const c = v.change_pct != null ? (v.change_pct >= 0 ? '+' : '') + v.change_pct + '%' : ''; return `${p} (${c})`; };
  const mktSummary = `S&P500: ${fmt('sp500')}, 나스닥: ${fmt('nasdaq')}, 코스피: ${fmt('kospi')}, 코스닥: ${fmt('kosdaq')}, USD/KRW: ${fmt('usdkrw')}, 미10년물: ${fmt('us10y')}%, VIX: ${fmt('vix')}, VKOSPI: ${fmt('vkospi')}, 금: ${fmt('gold')}, 은: ${fmt('silver')}, WTI: ${fmt('wti')}`;
  const newsSummary = (newsItems||[]).slice(0,8).map(n=>`- ${n.title}`).join('\n') || '없음';
  const dartSummary = (dartItems||[]).slice(0,5).map(d=>`- [${d.company}] ${d.title}`).join('\n') || '없음';
  const prompts = {
    morning: `당신은 Andrew의 개인 투자 어시스턴트입니다. Andrew는 버핏 가치투자 + 하워드 막스 사이클 + 카너먼 행동경제학 기반 Draft 3.0 철학을 가진 투자자입니다.\n\n[시장 데이터]\n${mktSummary}\n\n[주요 뉴스]\n${newsSummary}\n\n[공시]\n${dartSummary}\n\n아래 4개 섹션으로 브리핑해주세요 (각 2-3문장, 한국어):\n📊 시황 변화 — 전날 미장 움직임의 의미, 주요 지수 흐름 해석\n🔍 핵심 이슈 — 오늘 가장 중요한 이슈와 시장 영향\n⚠️ 투자자 시사점 — VIX/VKOSPI 기준 공포·탐욕 구간, 주목할 섹터 힌트\n💬 오늘의 한 마디 — 하워드 막스 또는 버핏 원칙으로 오늘 시장 한 문장 요약`,
    closing: `당신은 Andrew의 개인 투자 어시스턴트입니다.\n\n[마감 데이터]\n${mktSummary}\n\n[뉴스]\n${newsSummary}\n\n[공시]\n${dartSummary}\n\n아래 4개 섹션으로 마감 브리핑 (각 2-3문장, 한국어):\n📊 오늘 국장 총평 — 코스피·코스닥 흐름, 특이 섹터 의미\n🔍 오늘의 핵심 — 시장을 움직인 주요 이슈 분석\n🌏 내일 미장 포인트 — 오늘 흐름이 내일 미장에 시사하는 점\n⚠️ Draft 3.0 관점 — 매수 적극·분할매수·관망·회피 중 어느 구간인지 판단`,
    weekend: `당신은 Andrew의 개인 투자 어시스턴트입니다.\n\n[시장 데이터]\n${mktSummary}\n\n[이번 주 뉴스]\n${newsSummary}\n\n[공시]\n${dartSummary}\n\n아래 4개 섹션으로 주간 정리 (각 2-3문장, 한국어):\n📊 이번 주 시장 총평 — 주간 주요 지수 흐름과 변화 의미\n🔍 이번 주 핵심 이슈 — 가장 중요했던 이슈 2-3개와 시장 영향\n📅 다음 주 주목 포인트 — FOMC·실적 등 예정 이벤트, 주목 섹터\n⚠️ 포트폴리오 점검 — Draft 3.0 기준 현재 사이클 위치와 대응 전략`
  };
  try {
    el.innerHTML = '<div class="ai-loading"><div class="ai-dot"></div> AI가 시황을 분석하고 있어요...</div>';
    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: 'claude-sonnet-4-20250514', max_tokens: 1000, messages: [{ role: 'user', content: prompts[type] }] })
    });
    const data = await resp.json();
    const text = data.content?.[0]?.text || '분석 실패';
    const formatted = text.replace(/^(📊|🔍|⚠️|🌏|📅|💬)[^\n]*/gm, m => `<span class="ai-label">${m}</span>`).replace(/\n/g, '<br>');
    el.innerHTML = `<div class="ai-analysis-text">${formatted}</div>`;
  } catch(e) { el.innerHTML = '<div style="color:var(--text3);font-size:12px;">AI 분석 실패: ' + e.message + '</div>'; }
}
"""
    hc = hc.replace('async function loadMorning()', ai_fn + '\nasync function loadMorning()')
    changes.append("AI 함수")

# loadMorning
old_lm = "async function loadMorning() {\n  const now = new Date();\n  document.getElementById('morning-time').textContent = now.toLocaleDateString('ko-KR', {year:'numeric',month:'long',day:'numeric',weekday:'long'});\n  await loadMarket();\n  await loadNews('morning-news', 8);\n  await loadDart(1);\n}"
if old_lm in hc:
    hc = hc.replace(old_lm, "async function loadMorning() {\n  const now = new Date();\n  document.getElementById('morning-time').textContent = now.toLocaleDateString('ko-KR', {year:'numeric',month:'long',day:'numeric',weekday:'long'});\n  await loadMarket();\n  const newsData = await loadNews('morning-news', 8);\n  await loadDart(1);\n  try { const mktJ = await (await fetch(BACKEND + '/market/overview')).json(); const dartJ = await (await fetch(BACKEND + '/dart/recent?days=1')).json(); generateAIAnalysis('morning-analysis', mktJ.data, newsData, dartJ.data, 'morning'); } catch(e) {}\n}")
    changes.append("loadMorning")

# loadClosing
old_lc = "async function loadClosing() {\n  const now = new Date();\n  document.getElementById('closing-time').textContent = now.toLocaleDateString('ko-KR', {year:'numeric',month:'long',day:'numeric',weekday:'long'});\n  await loadMarket();\n  await loadNews('closing-news', 8);\n  await loadDart(1);\n}"
if old_lc in hc:
    hc = hc.replace(old_lc, "async function loadClosing() {\n  const now = new Date();\n  document.getElementById('closing-time').textContent = now.toLocaleDateString('ko-KR', {year:'numeric',month:'long',day:'numeric',weekday:'long'});\n  await loadMarket();\n  const newsData = await loadNews('closing-news', 8);\n  await loadDart(1);\n  try { const mktJ = await (await fetch(BACKEND + '/market/overview')).json(); const dartJ = await (await fetch(BACKEND + '/dart/recent?days=1')).json(); generateAIAnalysis('closing-analysis', mktJ.data, newsData, dartJ.data, 'closing'); } catch(e) {}\n}")
    changes.append("loadClosing")

# loadWeekend
old_lw = "async function loadWeekend() {\n  const now = new Date();\n  document.getElementById('weekend-time').textContent = now.toLocaleDateString('ko-KR', {year:'numeric',month:'long',day:'numeric',weekday:'long'});\n  await loadNews('weekend-news', 12);\n  const r = await fetch(BACKEND + '/dart/recent?days=7').catch(()=>({json:()=>({data:[]})}));\n  const j = await r.json();\n  renderDartList(j.data, 'weekend-dart');\n}"
if old_lw in hc:
    hc = hc.replace(old_lw, "async function loadWeekend() {\n  const now = new Date();\n  document.getElementById('weekend-time').textContent = now.toLocaleDateString('ko-KR', {year:'numeric',month:'long',day:'numeric',weekday:'long'});\n  const newsData = await loadNews('weekend-news', 12);\n  const r = await fetch(BACKEND + '/dart/recent?days=7').catch(()=>({json:()=>({data:[]})}));\n  const j = await r.json();\n  renderDartList(j.data, 'weekend-dart');\n  try { const mktJ = await (await fetch(BACKEND + '/market/overview')).json(); generateAIAnalysis('weekend-analysis', mktJ.data, newsData, j.data, 'weekend'); } catch(e) {}\n}")
    changes.append("loadWeekend")

print("적용:", changes)

with open(htmp, "w", encoding="utf-8") as f:
    f.write(hc)
os.replace(htmp, hsrc)
print("✅ andrew.html 저장")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "feat: silver/VIX/VKOSPI + AI briefing analysis"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료!")
