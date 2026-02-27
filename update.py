import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
src  = os.path.join(REPO, "andrew.html")
tmp  = os.path.join(REPO, "andrew_new.html")

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

old = "function drawScreenerChart(s) {\n\nfunction drawCandleChart"
new = """function drawScreenerChart(s) {
  if (!s || !s.history || s.history.length === 0) return;
  const canvasId = 'chart-' + s.ticker.replace(/\\./g, '_');
  const canvas = document.getElementById(canvasId);
  if (canvas) drawCandleChart(canvas, s.history);
}

function drawCandleChart"""

if old in content:
    content = content.replace(old, new)
    print("✅ JS 문법 오류 수정됨")
else:
    print("⚠️ 이미 수정됐거나 패턴 없음 — 그냥 push 진행")

with open(tmp, "w", encoding="utf-8") as f:
    f.write(content)
os.replace(tmp, src)
print("✅ andrew.html 저장")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "fix: drawScreenerChart SyntaxError resolved"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("🚀 완료!")
