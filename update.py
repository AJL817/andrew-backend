import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"

# ── main.py: sector/industry 필드 추가 ──────────────────────────
msrc = os.path.join(REPO, "main.py")
mtmp = os.path.join(REPO, "main.tmp")
with open(msrc, "r", encoding="utf-8") as f:
    mc = f.read()

# yf_single_quote에서 sector/industry 추출해서 반환
old_src = '''        return {"price":round(p,2),"prev":round(pv,2),
                "change_pct":round(chg or 0,2),
                "currency":m.get("currency",""),"history":hist}'''
new_src = '''        sector   = info.get("sector","")
        industry = info.get("industry","")
        return {"price":round(p,2),"prev":round(pv,2),
                "change_pct":round(chg or 0,2),
                "currency":m.get("currency",""),"history":hist,
                "sector":sector,"industry":industry}'''

if 'sector   = info.get("sector' not in mc and old_src in mc:
    mc = mc.replace(old_src, new_src)
    print("✅ sector/industry 추가 (yf_single_quote)")

# screener 결과 dict에도 sector/industry 포함
old_result = '''            result = {
                "ticker": ticker, "name": name, "price": price,
                "change_pct": chg, "currency": currency,'''
new_result = '''            result = {
                "ticker": ticker, "name": name, "price": price,
                "change_pct": chg, "currency": currency,
                "sector": q.get("sector",""), "industry": q.get("industry",""),'''

if '"sector": q.get' not in mc and old_result in mc:
    mc = mc.replace(old_result, new_result)
    print("✅ screener result에 sector/industry 추가")

with open(mtmp, "w", encoding="utf-8") as f:
    f.write(mc)
os.replace(mtmp, msrc)

# ── andrew.html: 동종 기업 비교 테이블 추가 ──────────────────────────
hsrc = os.path.join(REPO, "andrew.html")
htmp = os.path.join(REPO, "andrew.tmp")
with open(hsrc, "r", encoding="utf-8") as f:
    hc = f.read().replace('\r\n', '\n')

# CSS 추가
peer_css = """
.peer-table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 8px; }
.peer-table th { color: var(--text3); font-weight: 600; padding: 4px 8px; text-align: left; border-bottom: 1px solid var(--border); font-size: 10px; letter-spacing: .5px; }
.peer-table td { padding: 5px 8px; border-bottom: 1px solid var(--bg3); color: var(--text); }
.peer-table tr.peer-self { background: rgba(0,255,136,.07); }
.peer-table tr.peer-self td { color: var(--green); font-weight: 600; }
.peer-table tr:hover td { background: var(--bg3); }
.peer-rank-1 { color: var(--gold) !important; }
"""
if '.peer-table' not in hc:
    hc = hc.replace('</style>', peer_css + '\n</style>')
    print("✅ CSS 추가")

# renderScreenerDetail 안의 extraMetrics 뒤에 peer 비교 섹션 삽입
old_panel_end = '''      ${extraMetrics.length ? `
        <div style="margin-top:16px;">
          <div style="font-size:10px;font-weight:600;color:var(--text3);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;">📊 기타 지표</div>
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
            ${extraMetrics.map(m => `
              <div style="background:var(--bg3);border-radius:4px;padding:8px;">
                <div style="font-size:9px;color:var(--text3);margin-bottom:3px;">${m.label}</div>
                <div style="font-family:var(--font-mono);font-size:12px;font-weight:600;color:var(--text);">${m.val}</div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
    </div>
  `;'''

new_panel_end = '''      ${extraMetrics.length ? `
        <div style="margin-top:16px;">
          <div style="font-size:10px;font-weight:600;color:var(--text3);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;">📊 기타 지표</div>
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
            ${extraMetrics.map(m => `
              <div style="background:var(--bg3);border-radius:4px;padding:8px;">
                <div style="font-size:9px;color:var(--text3);margin-bottom:3px;">${m.label}</div>
                <div style="font-family:var(--font-mono);font-size:12px;font-weight:600;color:var(--text);">${m.val}</div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
      <!-- 동종 기업 비교 -->
      <div style="margin-top:16px;" id="peer-section-${s.ticker.replace(/\\./g,'_')}">
        <div style="font-size:10px;font-weight:600;color:var(--text3);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;">🏢 동종 기업 비교</div>
        <div id="peer-table-${s.ticker.replace(/\\./g,'_')}">
          <div style="color:var(--text3);font-size:11px;">동종 기업 로딩 중...</div>
        </div>
      </div>
    </div>
  `;'''

if old_panel_end in hc:
    hc = hc.replace(old_panel_end, new_panel_end)
    print("✅ 동종 기업 섹션 HTML 추가")

# renderPeerTable 함수 추가
peer_fn = r"""
function renderPeerTable(s, market) {
  const tableId = 'peer-table-' + s.ticker.replace(/\./g,'_');
  const el = document.getElementById(tableId);
  if (!el) return;

  const cache = screenerCache[market] || [];
  const sector = s.sector || '';
  const industry = s.industry || '';

  // 같은 industry 우선, 없으면 같은 sector
  let peers = cache.filter(p => p.ticker !== s.ticker && p.industry && p.industry === industry);
  if (peers.length < 3) {
    peers = cache.filter(p => p.ticker !== s.ticker && p.sector && p.sector === sector);
  }
  // 최대 6개, 점수 순 정렬
  peers = peers.sort((a,b) => b.score - a.score).slice(0, 6);

  if (!peers.length) {
    el.innerHTML = '<div style="color:var(--text3);font-size:11px;">같은 섹터 종목이 스크리너에 없어요 (섹터: ' + (sector||'미분류') + ')</div>';
    return;
  }

  // 현재 종목 포함해서 비교
  const all = [s, ...peers].sort((a,b) => b.score - a.score);
  const isKr = market === 'kr';

  const fmtPrice = (p, cur) => cur === 'USD' ? '$' + Number(p).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}) : Number(p).toLocaleString('ko-KR') + '원';
  const fmtPct = v => v != null ? (v >= 0 ? '+' : '') + v.toFixed(2) + '%' : '—';
  const fmtX = v => v != null ? v.toFixed(2) + 'x' : '—';
  const fmtPct1 = v => v != null ? v.toFixed(1) + '%' : '—';

  const cols = isKr
    ? ['종목', '점수', '주가', '등락', 'PBR', 'PER', 'ROE', '배당']
    : ['종목', '점수', '주가', '등락', 'PEG', 'PER', 'ROE', 'FCF'];

  const rows = all.map((p, i) => {
    const isSelf = p.ticker === s.ticker;
    const fcfStr = p.fcf ? (Math.abs(p.fcf)>=1e9 ? '$'+(p.fcf/1e9).toFixed(0)+'B' : '$'+(p.fcf/1e6).toFixed(0)+'M') : '—';
    const cells = isKr
      ? [
          `<b>${p.name}</b><br><span style="font-size:9px;color:var(--text3);">${p.ticker}</span>`,
          `<span style="${isSelf?'':'color:var(--text2);'}">${p.score}</span>`,
          fmtPrice(p.price, p.currency),
          `<span style="color:${p.change_pct>0?'var(--green)':p.change_pct<0?'var(--red)':'var(--text2)'}">${fmtPct(p.change_pct)}</span>`,
          fmtX(p.pbr), fmtX(p.pe), fmtPct1(p.roe!=null?p.roe*100:null), fmtPct1(p.div_yield!=null?p.div_yield*100:null)
        ]
      : [
          `<b>${p.name}</b><br><span style="font-size:9px;color:var(--text3);">${p.ticker}</span>`,
          `<span style="${isSelf?'':'color:var(--text2);'}">${p.score}</span>`,
          fmtPrice(p.price, p.currency),
          `<span style="color:${p.change_pct>0?'var(--green)':p.change_pct<0?'var(--red)':'var(--text2)'}">${fmtPct(p.change_pct)}</span>`,
          fmtX(p.peg), fmtX(p.pe), fmtPct1(p.roe!=null?p.roe*100:null), fcfStr
        ];
    return `<tr class="${isSelf?'peer-self':''}">
      ${i===0?`<td><span class="peer-rank-1">👑</span> ${cells[0]}</td>`:i===1?`<td>🥈 ${cells[0]}</td>`:i===2?`<td>🥉 ${cells[0]}</td>`:`<td>${cells[0]}</td>`}
      ${cells.slice(1).map(c=>`<td>${c}</td>`).join('')}
    </tr>`;
  }).join('');

  el.innerHTML = `
    <div style="font-size:10px;color:var(--text3);margin-bottom:6px;">섹터: <span style="color:var(--accent);">${industry || sector || '미분류'}</span> · ${all.length}개 비교</div>
    <table class="peer-table">
      <thead><tr>${cols.map(c=>`<th>${c}</th>`).join('')}</tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}
"""

if 'renderPeerTable' not in hc:
    hc = hc.replace('function selectScreenerStock(', peer_fn + '\nfunction selectScreenerStock(')
    print("✅ renderPeerTable 함수 추가")

# renderScreenerDetail 호출 후 renderPeerTable 호출
old_scroll = "  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });"
new_scroll = "  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });\n  // 패널 렌더 후 peer table 로드\n  setTimeout(() => renderPeerTable(s, market), 50);"
if 'renderPeerTable(s, market)' not in hc and old_scroll in hc:
    hc = hc.replace(old_scroll, new_scroll)
    print("✅ renderPeerTable 호출 추가")

with open(htmp, "w", encoding="utf-8") as f:
    f.write(hc)
os.replace(htmp, hsrc)
print("✅ andrew.html 저장")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "feat: peer comparison table for KR/US screener"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료!")
