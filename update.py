import subprocess, os

REPO = r"C:\Users\Andrew Lee\andrew-backend"

# ── main.py 패치 ──────────────────────────────────────────────
src = os.path.join(REPO, "main.py")
tmp = os.path.join(REPO, "main.tmp")

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

pwa_routes = '''
@app.get("/manifest.json")
async def serve_manifest():
    from fastapi.responses import JSONResponse
    return JSONResponse({
        "name": "ANDREW Investment System",
        "short_name": "ANDREW",
        "description": "개인 투자 철학 기반 주식 스크리닝 시스템",
        "start_url": "/app",
        "display": "standalone",
        "background_color": "#0a0a0a",
        "theme_color": "#00ff88",
        "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}]
    })

@app.get("/sw.js")
async def serve_sw():
    from fastapi.responses import Response
    sw = b"self.addEventListener('install',e=>{self.skipWaiting();});self.addEventListener('activate',e=>{self.clients.claim();});self.addEventListener('fetch',e=>{e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});"
    return Response(content=sw, media_type="application/javascript")

@app.get("/icon.svg")
async def serve_icon():
    from fastapi.responses import Response
    svg = b\'\'\'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
<rect width="192" height="192" rx="40" fill="#0a0a0a"/>
<text x="96" y="95" font-family="monospace" font-size="80" font-weight="bold" fill="#00ff88" text-anchor="middle">A</text>
<text x="96" y="140" font-family="monospace" font-size="16" fill="#666" text-anchor="middle">ANDREW</text>
</svg>\'\'\'
    return Response(content=svg, media_type="image/svg+xml")

'''

if '/manifest.json' not in content:
    content = content.replace('@app.get("/app")', pwa_routes + '@app.get("/app")')
    print("✅ PWA 엔드포인트 추가됨")
else:
    print("⚠️ 이미 있음")

with open(tmp, "w", encoding="utf-8") as f:
    f.write(content)
os.replace(tmp, src)
print("✅ main.py 저장")

# ── andrew.html 패치 ──────────────────────────────────────────
hsrc = os.path.join(REPO, "andrew.html")
htmp = os.path.join(REPO, "andrew.tmp")

with open(hsrc, "r", encoding="utf-8") as f:
    hcontent = f.read()

pwa_head = '  <link rel="manifest" href="/manifest.json">\n  <meta name="theme-color" content="#00ff88">\n  <meta name="mobile-web-app-capable" content="yes">\n  <meta name="apple-mobile-web-app-title" content="ANDREW">\n'
sw_reg   = '<script>if("serviceWorker"in navigator){window.addEventListener("load",()=>{navigator.serviceWorker.register("/sw.js");});}</script>\n'

changed = False
if '<link rel="manifest"' not in hcontent:
    hcontent = hcontent.replace('<head>', '<head>\n' + pwa_head)
    print("✅ manifest 링크 추가")
    changed = True
if 'serviceWorker' not in hcontent:
    hcontent = hcontent.replace('</body>', sw_reg + '</body>')
    print("✅ SW 등록 추가")
    changed = True

if changed:
    with open(htmp, "w", encoding="utf-8") as f:
        f.write(hcontent)
    os.replace(htmp, hsrc)
    print("✅ andrew.html 저장")
else:
    print("⚠️ andrew.html 이미 수정됨")

# ── git push ─────────────────────────────────────────────────
for cmd in [
    ["git", "-C", REPO, "add", "-A"],
    ["git", "-C", REPO, "commit", "-m", "feat: PWA manifest + SW + icon endpoints"],
    ["git", "-C", REPO, "push"],
]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out: print(out)

print("\n🚀 배포 완료! 2분 후 확인:")
print("https://andrew-backend-production.up.railway.app/manifest.json")
