import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"

# ── main.py 패치 ──────────────────────────────────────────────
msrc = os.path.join(REPO, "main.py")
mtmp = os.path.join(REPO, "main.tmp")
with open(msrc, "r", encoding="utf-8") as f:
    mc = f.read()

changes = 0

# 1) yf_get_fundamentals 반환값에 sector 추가
old1 = '            "shortRatio":     g("shortRatio"),\n        }'
new1 = '            "shortRatio":     g("shortRatio"),\n            "sector":         info.get("sector",""),\n            "industry":       info.get("industry",""),\n            "shortName":      info.get("shortName",""),\n        }'
if '"sector":         info.get' not in mc and old1 in mc:
    mc = mc.replace(old1, new1); changes += 1; print("✅ yf_get_fundamentals sector 추가")

# 2) yf_single_quote 반환값에 sector 추가
old2 = '    return {\n        "symbol":   ticker,\n        "regularMarketPrice": round(price, 2),\n        "regularMarketChangePercent": chg,\n        "currency": currency,\n        "_history": hist,'
new2 = '    sector   = yf_fund.get("sector","") or merged.get("sector","")\n    industry = yf_fund.get("industry","") or merged.get("industry","")\n    return {\n        "symbol":   ticker,\n        "regularMarketPrice": round(price, 2),\n        "regularMarketChangePercent": chg,\n        "currency": currency,\n        "sector":   sector,\n        "industry": industry,\n        "_history": hist,'
if '"sector":   sector,' not in mc and old2 in mc:
    mc = mc.replace(old2, new2); changes += 1; print("✅ yf_single_quote sector 추가")

# 3) screener results.append에 sector 추가
old3 = '                        "currency":   q.get("currency",""),\n                    })'
new3 = '                        "currency":   q.get("currency",""),\n                        "sector":     q.get("sector",""),\n                        "industry":   q.get("industry",""),\n                    })'
if '"sector":     q.get' not in mc and old3 in mc:
    mc = mc.replace(old3, new3); changes += 1; print("✅ screener results sector 추가")

print(f"총 {changes}개 수정")
with open(mtmp, "w", encoding="utf-8") as f:
    f.write(mc)
os.replace(mtmp, msrc)

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "fix: add sector/industry to screener + peer comparison"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료! 배포 후 재스크리닝:")
print("https://andrew-backend-production.up.railway.app/screener/kr?force=true")
