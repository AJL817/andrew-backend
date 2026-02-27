import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"

# ── main.py 패치 ──────────────────────────────────────
src = os.path.join(REPO, "main.py")
tmp = os.path.join(REPO, "main.tmp")

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

old = '''MARKET_TICKERS = {
    "sp500":"^GSPC","nasdaq":"^IXIC","dow":"^DJI",
    "kospi":"^KS11","kosdaq":"^KQ11",
    "usdkrw":"KRW=X","usdjpy":"JPY=X",
    "us10y":"^TNX","us2y":"^IRX",
    "gold":"GC=F","wti":"CL=F","copper":"HG=F",
}'''
new = '''MARKET_TICKERS = {
    "sp500":"^GSPC","nasdaq":"^IXIC","dow":"^DJI",
    "kospi":"^KS11","kosdaq":"^KQ11",
    "usdkrw":"KRW=X","usdjpy":"JPY=X",
    "us10y":"^TNX","us2y":"^IRX",
    "gold":"GC=F","silver":"SI=F","wti":"CL=F","copper":"HG=F",
    "vix":"^VIX","vkospi":"^VKOSPI",
}'''

if old in content:
    content = content.replace(old, new)
    print("✅ MARKET_TICKERS 수정 (VIX, VKOSPI, 은 추가)")
else:
    print("⚠️ MARKET_TICKERS 패턴 못 찾음")

with open(tmp, "w", encoding="utf-8") as f:
    f.write(content)
os.replace(tmp, src)

# ── andrew.html 패치 ──────────────────────────────────
hsrc = os.path.join(REPO, "andrew.html")
htmp = os.path.join(REPO, "andrew.tmp")

with open(hsrc, "r", encoding="utf-8") as f:
    hcontent = f.read()

# 1) 대시보드 map 배열에 추가
old_map = "      ['copper','m-copper','m-copper-c',null,null,','],\r\n    ];"
new_map = "      ['copper','m-copper','m-copper-c',null,null,','],\r\n      ['silver','m-silver','m-silver-c','tk-silver','tk-silver-chg',','],\r\n      ['vix','m-vix','m-vix-c','tk-vix','tk-vix-chg',''],\r\n      ['vkospi','m-vkospi','m-vkospi-c',null,null,''],\r\n    ];"

if old_map in hcontent:
    hcontent = hcontent.replace(old_map, new_map)
    print("✅ JS map 배열 수정")

# 2) 모닝 브리핑 채권&원자재 카드에 은 추가
old_bonds = '''          <div class="mkt-tile"><div class="mkt-label">금</div><div class="mkt-val" id="mm-gold">—</div><div class="mkt-chg" id="mm-gold-c">—</div></div>
          <div class="mkt-tile"><div class="mkt-label">WTI</div><div class="mkt-val" id="mm-wti">—</div><div class="mkt-chg" id="mm-wti-c">—</div></div>'''
new_bonds = '''          <div class="mkt-tile"><div class="mkt-label">금</div><div class="mkt-val" id="mm-gold">—</div><div class="mkt-chg" id="mm-gold-c">—</div></div>
          <div class="mkt-tile"><div class="mkt-label">은</div><div class="mkt-val" id="mm-silver">—</div><div class="mkt-chg" id="mm-silver-c">—</div></div>
          <div class="mkt-tile"><div class="mkt-label">WTI</div><div class="mkt-val" id="mm-wti">—</div><div class="mkt-chg" id="mm-wti-c">—</div></div>
          <div class="mkt-tile"><div class="mkt-label">VIX</div><div class="mkt-val" id="mm-vix">—</div><div class="mkt-chg" id="mm-vix-c">—</div></div>'''

if old_bonds in hcontent:
    hcontent = hcontent.replace(old_bonds, new_bonds)
    print("✅ 모닝 채권&원자재 카드 수정")

# 3) 모닝 브리핑 map에 추가
old_mm = "      ['gold','mm-gold','mm-gold-c'],['wti','mm-wti','mm-wti-c'],"
new_mm = "      ['gold','mm-gold','mm-gold-c'],['silver','mm-silver','mm-silver-c'],['wti','mm-wti','mm-wti-c'],['vix','mm-vix','mm-vix-c'],"

if old_mm in hcontent:
    hcontent = hcontent.replace(old_mm, new_mm)
    print("✅ 모닝 mm-map 수정")

# 4) 대시보드 원자재 섹션에 은 + VIX 타일 추가
old_dash_gold = '''<div class="mkt-tile"><div class="mkt-label">금</div><div class="mkt-val" id="m-gold">—</div><div class="mkt-chg" id="m-gold-c">—</div></div>'''
new_dash_gold = '''<div class="mkt-tile"><div class="mkt-label">금</div><div class="mkt-val" id="m-gold">—</div><div class="mkt-chg" id="m-gold-c">—</div></div>
              <div class="mkt-tile"><div class="mkt-label">은</div><div class="mkt-val" id="m-silver">—</div><div class="mkt-chg" id="m-silver-c">—</div></div>
              <div class="mkt-tile"><div class="mkt-label">VIX</div><div class="mkt-val" id="m-vix">—</div><div class="mkt-chg" id="m-vix-c">—</div></div>
              <div class="mkt-tile"><div class="mkt-label">VKOSPI</div><div class="mkt-val" id="m-vkospi">—</div><div class="mkt-chg" id="m-vkospi-c">—</div></div>'''

if old_dash_gold in hcontent:
    hcontent = hcontent.replace(old_dash_gold, new_dash_gold)
    print("✅ 대시보드 원자재 섹션 수정")

# 5) 티커바에 은 + VIX 추가
old_ticker_gold = '''<div class="ticker-item"><span class="ticker-name">금</span><span class="ticker-val" id="tk-gold">—</span><span class="ticker-chg" id="tk-gold-chg">—</span></div>'''
new_ticker_gold = '''<div class="ticker-item"><span class="ticker-name">금</span><span class="ticker-val" id="tk-gold">—</span><span class="ticker-chg" id="tk-gold-chg">—</span></div>
    <div class="ticker-item"><span class="ticker-name">은</span><span class="ticker-val" id="tk-silver">—</span><span class="ticker-chg" id="tk-silver-chg">—</span></div>
    <div class="ticker-item"><span class="ticker-name">VIX</span><span class="ticker-val" id="tk-vix">—</span><span class="ticker-chg" id="tk-vix-chg">—</span></div>'''

if old_ticker_gold in hcontent:
    hcontent = hcontent.replace(old_ticker_gold, new_ticker_gold)
    print("✅ 티커바 수정")

with open(htmp, "w", encoding="utf-8") as f:
    f.write(hcontent)
os.replace(htmp, hsrc)
print("✅ andrew.html 저장")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "feat: add VIX, VKOSPI, Silver to market data"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료!")
