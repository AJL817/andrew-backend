import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
src  = os.path.join(REPO, "main.py")
tmp  = os.path.join(REPO, "main.tmp")

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

changes = 0

# Fix 1: fetch_quote - regularMarketChangePercent 직접 사용
old1 = '''        m   = r.json()["chart"]["result"][0]["meta"]
        p   = m.get("regularMarketPrice") or m.get("previousClose", 0)
        pv  = m.get("previousClose") or m.get("chartPreviousClose", p)
        return {"price": round(p,4), "prev": round(pv,4),
                "change_pct": round((p-pv)/pv*100 if pv else 0, 2),
                "currency": m.get("currency","")}'''
new1 = '''        m   = r.json()["chart"]["result"][0]["meta"]
        p   = m.get("regularMarketPrice") or m.get("previousClose", 0)
        pv  = m.get("previousClose") or m.get("chartPreviousClose", p)
        chg = m.get("regularMarketChangePercent")  # Yahoo가 직접 제공하는 값 사용
        if chg is None and pv:
            chg = (p - pv) / pv * 100
        return {"price": round(p,4), "prev": round(pv,4),
                "change_pct": round(chg or 0, 2),
                "currency": m.get("currency","")}'''

if old1 in content:
    content = content.replace(old1, new1)
    changes += 1
    print("✅ fetch_quote 수정")

# Fix 2: fetch_quote_hist - 동일하게 수정
old2 = '''        p   = m.get("regularMarketPrice") or m.get("previousClose",0)
        pv  = m.get("previousClose") or m.get("chartPreviousClose",p)
        ts  = res.get("timestamp",[])
        cl  = res.get("indicators",{}).get("quote",[{}])[0].get("close",[])
        hist = [{"date":datetime.fromtimestamp(t).strftime("%m/%d"),"close":round(c,2)}
                for t,c in zip(ts,cl) if c is not None][-7:]
        return {"price":round(p,2),"prev":round(pv,2),
                "change_pct":round((p-pv)/pv*100 if pv else 0,2),
                "currency":m.get("currency",""),"history":hist}'''
new2 = '''        p   = m.get("regularMarketPrice") or m.get("previousClose",0)
        pv  = m.get("previousClose") or m.get("chartPreviousClose",p)
        chg = m.get("regularMarketChangePercent")
        if chg is None and pv:
            chg = (p - pv) / pv * 100
        ts  = res.get("timestamp",[])
        cl  = res.get("indicators",{}).get("quote",[{}])[0].get("close",[])
        hist = [{"date":datetime.fromtimestamp(t).strftime("%m/%d"),"close":round(c,2)}
                for t,c in zip(ts,cl) if c is not None][-7:]
        return {"price":round(p,2),"prev":round(pv,2),
                "change_pct":round(chg or 0,2),
                "currency":m.get("currency",""),"history":hist}'''

if old2 in content:
    content = content.replace(old2, new2)
    changes += 1
    print("✅ fetch_quote_hist 수정")

# Fix 3: yf_single_quote - 동일하게 수정
old3 = '''        price    = meta.get("regularMarketPrice") or meta.get("previousClose", 0)
        prev     = meta.get("previousClose") or meta.get("chartPreviousClose", price)
        chg      = round(((price - prev) / prev * 100) if prev else 0, 2)'''
new3 = '''        price    = meta.get("regularMarketPrice") or meta.get("previousClose", 0)
        prev     = meta.get("previousClose") or meta.get("chartPreviousClose", price)
        _chg     = meta.get("regularMarketChangePercent")
        chg      = round(_chg if _chg is not None else ((price - prev) / prev * 100 if prev else 0), 2)'''

if old3 in content:
    content = content.replace(old3, new3)
    changes += 1
    print("✅ yf_single_quote 수정")

# Fix 4: /chart 엔드포인트
old4 = '''            "change_pct": round((price - prev) / prev * 100 if prev else 0, 2),'''
new4 = '''            "change_pct": round(meta.get("regularMarketChangePercent") or ((price - prev) / prev * 100 if prev else 0), 2),'''

if old4 in content:
    content = content.replace(old4, new4)
    changes += 1
    print("✅ /chart 엔드포인트 수정")

print(f"\n총 {changes}개 수정")

with open(tmp, "w", encoding="utf-8") as f:
    f.write(content)
os.replace(tmp, src)
print("✅ main.py 저장")

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "fix: use regularMarketChangePercent directly - 등락률 오류 수정"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 배포 완료!")
