import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
src  = os.path.join(REPO, "main.py")
tmp  = os.path.join(REPO, "main_new.py")

with open(src, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 패치할 줄 찾기
insert_after_pbr  = None   # "if pbr is not None and pbr <= 0: pbr = None" 줄
insert_after_pe   = None   # 마지막 "if pe is not None and (pe <= 0 or pe > 2000): pe = None" 줄

for i, line in enumerate(lines):
    s = line.strip()
    if s == "if pbr is not None and pbr <= 0: pbr = None":
        insert_after_pbr = i
    if s == "if pe is not None and (pe <= 0 or pe > 2000): pe = None":
        insert_after_pe = i

print(f"PBR 삽입 위치: {insert_after_pbr}, PER 삽입 위치: {insert_after_pe}")

pbr_patch = '''\
        # 국장 fallback: balance sheet에서 총자본 직접 계산
        if (pbr is None or pbr <= 0) and is_kr:
            try:
                shares = g("sharesOutstanding")
                bs = t.quarterly_balance_sheet
                if bs is not None and not bs.empty:
                    equity_row = None
                    for row_key in ["Stockholders Equity","Total Equity Gross Minority Interest",
                                    "Common Stock Equity","Total Stockholders Equity"]:
                        if row_key in bs.index:
                            equity_row = float(bs.loc[row_key].iloc[0])
                            break
                    if equity_row and equity_row > 0 and shares and shares > 0:
                        bv_per_share = equity_row / shares
                        if bv_per_share > 0 and price and price > 0:
                            pbr = round(price / bv_per_share, 3)
            except: pass
'''

pe_patch = '''\
        # 국장 fallback: income statement TTM 합산으로 EPS 직접 계산
        if (pe is None or pe <= 0 or pe > 2000) and is_kr:
            try:
                shares = g("sharesOutstanding")
                inc = t.quarterly_income_stmt
                if inc is not None and not inc.empty:
                    net_income = None
                    for row_key in ["Net Income","Net Income Common Stockholders",
                                    "Net Income From Continuing Operations"]:
                        if row_key in inc.index:
                            vals = [float(v) for v in inc.loc[row_key].dropna().values[:4]]
                            if vals:
                                net_income = sum(vals)
                                break
                    if net_income and net_income > 0 and shares and shares > 0:
                        eps_calc = net_income / shares
                        if eps_calc > 0 and price and price > 0:
                            pe = round(price / eps_calc, 2)
            except: pass
'''

if insert_after_pbr is not None and insert_after_pe is not None:
    # pe 먼저 삽입 (뒤에서부터 해야 인덱스 안 밀림)
    lines.insert(insert_after_pe + 1, pe_patch)
    lines.insert(insert_after_pbr + 1, pbr_patch)
    print("✅ PBR/PER fallback 패치 적용됨")
else:
    print("⚠️  패치 위치를 찾지 못했어요. 줄 번호를 확인하세요.")

with open(tmp, "w", encoding="utf-8") as f:
    f.writelines(lines)
os.replace(tmp, src)
print("✅ main.py 저장 완료")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "fix: KR PBR/PER balance sheet fallback"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("🚀 배포 완료!")
