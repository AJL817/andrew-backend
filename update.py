import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"

# main.py 내용을 직접 읽어서 쓰기
src = os.path.join(REPO, "main.py")
tmp = os.path.join(REPO, "main_new.py")

# 수정된 내용 적용
with open(src, "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: TD 환경변수 이름
content = content.replace(
    'TD_API_KEY         = os.getenv("TD_API_KEY", "")   # Twelve Data — twelvedata.com 에서 무료 발급',
    'TD_API_KEY         = os.getenv("Twelve_Data", os.getenv("TD_API_KEY", ""))  # Twelve Data'
)

# Fix 2: PBR balance sheet fallback 삽입
old_pbr = '''        # 국장 일부 종목: yfinance가 음수 장부가치 반환 → None 처리
        if pbr is not None and pbr <= 0: pbr = None

        # ── PER ────────────────────────────────────────────────
        pe = g("trailingPE")
        if pe is None or pe <= 0 or pe > 2000:
            eps = g("trailingEps", "epsTrailingTwelveMonths")
            if eps and eps > 0 and price and price > 0:
                pe = round(price / eps, 2)
        if pe is not None and (pe <= 0 or pe > 2000): pe = None'''

new_pbr = '''        # 국장 fallback: balance sheet에서 총자본 직접 계산
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
        if pbr is not None and pbr <= 0: pbr = None

        # ── PER ────────────────────────────────────────────────
        pe = g("trailingPE")
        if pe is None or pe <= 0 or pe > 2000:
            eps = g("trailingEps", "epsTrailingTwelveMonths")
            if eps and eps > 0 and price and price > 0:
                pe = round(price / eps, 2)
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
        if pe is not None and (pe <= 0 or pe > 2000): pe = None'''

if old_pbr in content:
    content = content.replace(old_pbr, new_pbr)
    print("✅ PBR/PER fallback 패치 적용됨")
else:
    print("⚠️  PBR 패치 위치 못찾음 — Fix 1만 적용")

# 임시 파일로 쓴 다음 rename (파일 잠금 우회)
with open(tmp, "w", encoding="utf-8") as f:
    f.write(content)

os.replace(tmp, src)
print("✅ main.py 저장 완료")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "fix: TD env var + KR PBR/PER from balance sheet"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("🚀 배포 완료!")
