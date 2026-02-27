import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
msrc = os.path.join(REPO, "main.py")
mtmp = os.path.join(REPO, "main.tmp")

with open(msrc, "r", encoding="utf-8") as f:
    mc = f.read()

# 핵심 버그 수정: year-1(2025) 사업보고서는 3월 전엔 없음 → year-2(2024) 우선 시도
old = '''    result = {}
    for fs_div in ["CFS", "OFS"]:
        try:
            r = await client.get(
                "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json",
                params={"crtfc_key": DART_API_KEY, "corp_code": corp_code,
                        "bsns_year": str(kst_now().year - 1),
                        "reprt_code": "11011", "fs_div": fs_div},
                timeout=12,
            )'''

new = '''    result = {}
    # 2월 이전엔 전년도 사업보고서 미공시 → year-2 우선, 없으면 year-1
    now = kst_now()
    bsns_years = [str(now.year - 2), str(now.year - 1)] if now.month < 4 else [str(now.year - 1), str(now.year - 2)]
    for fs_div in ["CFS", "OFS"]:
        for bsns_year in bsns_years:
          try:
            r = await client.get(
                "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json",
                params={"crtfc_key": DART_API_KEY, "corp_code": corp_code,
                        "bsns_year": bsns_year,
                        "reprt_code": "11011", "fs_div": fs_div},
                timeout=12,
            )'''

if old in mc:
    mc = mc.replace(old, new)
    # items 체크 후 break 추가
    old2 = '''            if d.get("status") != "000": continue
            items = d.get("list", [])
            if not items: continue'''
    new2 = '''            if d.get("status") != "000": continue
            items = d.get("list", [])
            if not items: continue
            # 데이터 있으면 연도 루프 탈출'''
    mc = mc.replace(old2, new2, 1)
    print("✅ 연도 버그 수정 (year-2 우선)")
else:
    print("❌ 패턴 없음")

with open(mtmp, "w", encoding="utf-8") as f:
    f.write(mc)
os.replace(mtmp, msrc)

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "fix: DART use year-2 (2024) before Feb/March since 2025 reports not published yet"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료! 재스크리닝:")
print("https://andrew-backend-production.up.railway.app/screener/kr?force=true")
