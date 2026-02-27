import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
src  = os.path.join(REPO, "main.py")
tmp  = os.path.join(REPO, "main.tmp")

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

changes = 0

# yf_single_quote 에서 등락률을 히스토리 마지막 두 캔들로 계산
old = '''        price    = meta.get("regularMarketPrice") or meta.get("previousClose", 0)
        prev     = meta.get("previousClose") or meta.get("chartPreviousClose", price)
        _chg     = meta.get("regularMarketChangePercent")
        chg      = round(_chg if _chg is not None else ((price - prev) / prev * 100 if prev else 0), 2)'''

new = '''        price    = meta.get("regularMarketPrice") or meta.get("previousClose", 0)
        prev     = meta.get("previousClose") or meta.get("chartPreviousClose", price)
        _chg     = meta.get("regularMarketChangePercent")
        chg      = round(_chg if _chg is not None else ((price - prev) / prev * 100 if prev else 0), 2)
        # Yahoo 등락률이 배당락 조정가 기준으로 틀릴 수 있음
        # 히스토리 마지막 두 캔들로 재계산해서 검증
        _chg_override = None'''

if old in content:
    content = content.replace(old, new)
    changes += 1
    print("✅ yf_single_quote 준비")

# hist 계산 후에 등락률 재계산 로직 추가
old2 = '''        hist = hist[-7:]

        # v8 meta에 포함된 재무지표 추출'''
new2 = '''        hist = hist[-7:]

        # 히스토리 마지막 두 캔들로 등락률 재계산 (Yahoo 조정가 오류 방지)
        if len(hist) >= 2:
            _today_close = hist[-1]["close"]
            _prev_close  = hist[-2]["close"]
            if _prev_close and _prev_close > 0:
                _chg_hist = round((_today_close - _prev_close) / _prev_close * 100, 2)
                # Yahoo 값과 히스토리 값 차이가 5% 이상이면 히스토리 값 사용
                if abs(_chg_hist - chg) > 5:
                    chg = _chg_hist

        # v8 meta에 포함된 재무지표 추출'''

if old2 in content:
    content = content.replace(old2, new2)
    changes += 1
    print("✅ 등락률 히스토리 검증 로직 추가")

print(f"총 {changes}개 수정")

with open(tmp, "w", encoding="utf-8") as f:
    f.write(content)
os.replace(tmp, src)
print("✅ main.py 저장")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "fix: recalc change_pct from history candles to avoid Yahoo adj-price error"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 배포 완료!")
