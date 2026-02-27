import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
hsrc = os.path.join(REPO, "andrew.html")
htmp = os.path.join(REPO, "andrew.tmp")

with open(hsrc, "r", encoding="utf-8") as f:
    hc = f.read()

old = "  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });\n\n  const scoreColor"
new = "  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });\n  setTimeout(() => renderPeerTable(s, market), 100);\n\n  const scoreColor"

if 'renderPeerTable(s, market)' not in hc and old in hc:
    hc = hc.replace(old, new)
    print("✅ renderPeerTable 호출 추가")
elif 'renderPeerTable(s, market)' in hc:
    print("⚠️ 이미 있음")
else:
    print("❌ 패턴 없음")

with open(htmp, "w", encoding="utf-8") as f:
    f.write(hc)
os.replace(htmp, hsrc)
print("✅ 저장")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "fix: actually call renderPeerTable after panel render"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료!")
