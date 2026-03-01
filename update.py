import subprocess, os

REPO  = r"C:\Users\Andrew Lee\andrew-backend"
hsrc  = os.path.join(REPO, "andrew.html")
htmp  = os.path.join(REPO, "andrew.tmp")

with open(hsrc, "r", encoding="utf-8") as f:
    hc = f.read()

# ── generateAIAnalysis 함수 교체 ─────────────────────────────
# 기존: 브라우저에서 직접 Anthropic API 호출 (CORS로 막힘)
# 변경: 백엔드 /briefing/{type} 호출 → ai_analysis 필드 사용

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
  try {
    const resp = await fetch(BACKEND + '/briefing/' + type);
    const data = await resp.json();
    const text = data.ai_analysis || '분석 결과 없음';
    if (text.startsWith('⚠️')) {
      el.innerHTML = `<div style="color:var(--text3);font-size:12px;">${text}</div>`;
      return;
    }
    const formatted = text
      .replace(/\\*\\*(.+?)\\*\\*/g, '<strong style="color:var(--orange)">$1</strong>')
      .replace(/^#{1,3}\\s+(.+)$/gm, '<strong style="color:var(--accent)">$1</strong>')
      .replace(/^(📊|🔍|⚠️|🌏|📅|💬|🎯|📈|📉)[^\\n]*/gm, m => `<span class="ai-label">${m}</span>`)
      .replace(/\\n/g, '<br>');
    el.innerHTML = `<div class="ai-analysis-text">${formatted}</div>`;
  } catch(e) {
    el.innerHTML = '<div style="color:var(--text3);font-size:12px;">AI 분석 실패: ' + e.message + '</div>';
  }
}"""

if old_fn in hc:
    hc = hc.replace(old_fn, new_fn)
    print("✅ generateAIAnalysis 함수 교체 완료")
else:
    print("❌ generateAIAnalysis 패턴 못 찾음 — 수동 확인 필요")

# ── loadMorning 교체 ─────────────────────────────────────────
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
    print("✅ loadMorning 교체 완료")
else:
    print("❌ loadMorning 패턴 못 찾음")

# ── loadClosing 교체 ─────────────────────────────────────────
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
    print("✅ loadClosing 교체 완료")
else:
    print("❌ loadClosing 패턴 못 찾음")

# ── loadWeekend 교체 ─────────────────────────────────────────
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
    print("✅ loadWeekend 교체 완료")
else:
    print("❌ loadWeekend 패턴 못 찾음")

# ── 저장 ─────────────────────────────────────────────────────
with open(htmp, "w", encoding="utf-8") as f:
    f.write(hc)
os.replace(htmp, hsrc)
print("✅ andrew.html 저장 완료")

# ── Git push ──────────────────────────────────────────────────
for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "feat: AI 시황 분석 백엔드 연동 (CORS 수정)"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료! 모닝브리핑 탭에서 AI 분석 확인하세요.")
print("https://andrew-backend-production.up.railway.app/app")
