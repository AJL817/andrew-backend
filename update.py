import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
hsrc = os.path.join(REPO, "andrew.html")
htmp = os.path.join(REPO, "andrew.tmp")

with open(hsrc, "r", encoding="utf-8") as f:
    hc = f.read()

old = "  setTimeout(() => loadDetailChart(s.ticker, market, '1M'), 50);"
new = "  setTimeout(() => loadDetailChart(s.ticker, market, '1M'), 50);\n  setTimeout(() => renderPeerTable(s, market), 200);"

if old in hc and 'renderPeerTable(s, market)' not in hc:
    hc = hc.replace(old, new)
    print("✅ renderPeerTable 호출 추가")
else:
    print("현재 상태:", "호출 있음" if 'renderPeerTable(s, market)' in hc else "패턴 없음")

with open(htmp, "w", encoding="utf-8") as f:
    f.write(hc)
os.replace(htmp, hsrc)

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "fix: call renderPeerTable after detail panel renders"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("🚀 완료!")
