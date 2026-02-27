import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
hsrc = os.path.join(REPO, "andrew.html")
htmp = os.path.join(REPO, "andrew.tmp")

with open(hsrc, "r", encoding="utf-8") as f:
    hc = f.read()

# 패널 닫는 부분에 peer 섹션 삽입
old = "        </div>\n        </div>\n      </div>\n    </div>`;\n\n  // 차트 로드"
new = """        </div>
        </div>
      </div>
      <!-- 동종 기업 비교 -->
      <div style="margin-top:16px;">
        <div style="font-size:10px;font-weight:600;color:var(--text3);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;">🏢 동종 기업 비교</div>
        <div id="peer-table-${s.ticker.replace(/\\./g,'_')}">
          <div style="color:var(--text3);font-size:11px;">로딩 중...</div>
        </div>
      </div>
    </div>`;

  // 차트 로드"""

if 'peer-table-${s.ticker' not in hc and old in hc:
    hc = hc.replace(old, new)
    print("✅ peer 섹션 HTML 삽입")
else:
    print("⚠️ 이미 있거나 패턴 없음")

with open(htmp, "w", encoding="utf-8") as f:
    f.write(hc)
os.replace(htmp, hsrc)
print("✅ andrew.html 저장")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "fix: peer comparison HTML section inserted in detail panel"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료! 2분 후 종목 클릭해서 하단 동종 기업 비교 테이블 확인해줘요.")
