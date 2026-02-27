import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"
msrc = os.path.join(REPO, "main.py")
mtmp = os.path.join(REPO, "main.tmp")

with open(msrc, "r", encoding="utf-8") as f:
    mc = f.read()

old_fn = '''    result = {}
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
            )
            d = r.json()
            if d.get("status") != "000": continue
            items = d.get("list", [])
            if not items: continue
            # 데이터 있으면 연도 루프 탈출

            def get_val(keywords, sj_div):
                for item in items:
                    if item.get("sj_div") != sj_div: continue
                    nm = item.get("account_nm", "")
                    if any(k in nm for k in keywords):
                        v = item.get("thstrm_amount","").replace(",","").replace("-","").strip()
                        try: return float(v) if v else None
                        except: pass
                return None

            net_income   = get_val(["당기순이익"], "IS")
            equity       = get_val(["자본총계","지배기업 소유주 지분"], "BS")
            total_assets = get_val(["자산총계"], "BS")
            total_liab   = get_val(["부채총계"], "BS")
            revenue      = get_val(["매출액","영업수익"], "IS")
            op_income    = get_val(["영업이익"], "IS")

            if equity and equity > 0:
                if net_income: result["dart_roe"] = round(net_income / equity * 100, 2)
                if total_liab: result["dart_debt_ratio"] = round(total_liab / equity * 100, 1)
            if total_assets and total_assets > 0 and net_income:
                result["dart_roa"] = round(net_income / total_assets * 100, 2)
            if revenue and revenue > 0:
                if op_income: result["dart_op_margin"] = round(op_income / revenue * 100, 2)
                if net_income: result["dart_net_margin"] = round(net_income / revenue * 100, 2)
            result["dart_source"] = fs_div
            break
        except Exception as e:
            result["dart_error"] = str(e)
    return result'''

new_fn = '''    result = {}
    # 2월~3월엔 전년도 사업보고서 미공시 → year-2(2024) 우선
    now = kst_now()
    bsns_years = [str(now.year - 2), str(now.year - 1)] if now.month < 4 else [str(now.year - 1), str(now.year - 2)]
    for fs_div in ["CFS", "OFS"]:
        got_data = False
        for bsns_year in bsns_years:
            try:
                r = await client.get(
                    "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json",
                    params={"crtfc_key": DART_API_KEY, "corp_code": corp_code,
                            "bsns_year": bsns_year,
                            "reprt_code": "11011", "fs_div": fs_div},
                    timeout=12,
                )
                d = r.json()
                if d.get("status") != "000": continue
                items = d.get("list", [])
                if not items: continue

                def get_val(keywords, sj_div):
                    for item in items:
                        if item.get("sj_div") != sj_div: continue
                        nm = item.get("account_nm", "")
                        if any(k in nm for k in keywords):
                            v = item.get("thstrm_amount","").replace(",","").replace("-","").strip()
                            try: return float(v) if v else None
                            except: pass
                    return None

                net_income   = get_val(["당기순이익"], "IS")
                equity       = get_val(["자본총계","지배기업 소유주 지분"], "BS")
                total_assets = get_val(["자산총계"], "BS")
                total_liab   = get_val(["부채총계"], "BS")
                revenue      = get_val(["매출액","영업수익"], "IS")
                op_income    = get_val(["영업이익"], "IS")

                if equity and equity > 0:
                    if net_income: result["dart_roe"] = round(net_income / equity * 100, 2)
                    if total_liab: result["dart_debt_ratio"] = round(total_liab / equity * 100, 1)
                if total_assets and total_assets > 0 and net_income:
                    result["dart_roa"] = round(net_income / total_assets * 100, 2)
                if revenue and revenue > 0:
                    if op_income: result["dart_op_margin"] = round(op_income / revenue * 100, 2)
                    if net_income: result["dart_net_margin"] = round(net_income / revenue * 100, 2)
                result["dart_source"] = fs_div + "_" + bsns_year
                got_data = True
                break
            except Exception as e:
                result["dart_error"] = str(e)
        if got_data:
            break
    return result'''

if old_fn in mc:
    mc = mc.replace(old_fn, new_fn)
    print("✅ dart_financials 들여쓰기 수정")
else:
    print("❌ 패턴 없음")

with open(mtmp, "w", encoding="utf-8") as f:
    f.write(mc)
os.replace(mtmp, msrc)

for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "fix: dart_financials indentation syntax error"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 완료! 재스크리닝:")
print("https://andrew-backend-production.up.railway.app/screener/kr?force=true")
