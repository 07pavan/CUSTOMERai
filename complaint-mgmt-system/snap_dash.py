import asyncio
import json
import os
import subprocess
import urllib.request
import base64
import websockets

async def snap():
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    bin_path = next(p for p in edge_paths if os.path.exists(p))
    user_data = os.path.abspath("snap_temp")
    proc = subprocess.Popen([
        bin_path,
        "--remote-debugging-port=9223",
        f"--user-data-dir={user_data}",
        "--headless=new",
        "--disable-gpu",
        "--window-size=1440,1400",
        "http://127.0.0.1:5173/admin/dashboard"
    ])
    await asyncio.sleep(2)
    try:
        ws_url = None
        for _ in range(10):
            try:
                with urllib.request.urlopen("http://127.0.0.1:9223/json/list", timeout=2) as r:
                    pages = json.loads(r.read())
                    for p in pages:
                        if p.get("webSocketDebuggerUrl"):
                            ws_url = p["webSocketDebuggerUrl"]
                            break
                    if ws_url:
                        break
            except Exception:
                await asyncio.sleep(0.5)

        if not ws_url:
            print("No WS URL found")
            return

        async with websockets.connect(ws_url, max_size=100*1024*1024) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
            await ws.send(json.dumps({"id": 2, "method": "Runtime.enable"}))
            
            # Set admin role and navigate to /admin/dashboard
            js = "localStorage.setItem('role', 'admin'); localStorage.setItem('actor', 'admin@pharma.com');"
            await ws.send(json.dumps({"id": 3, "method": "Runtime.evaluate", "params": {"expression": js}}))
            await ws.send(json.dumps({"id": 4, "method": "Page.navigate", "params": {"url": "http://127.0.0.1:5173/admin/dashboard"}}))
            
            # Wait for data to load from backend
            await asyncio.sleep(3.5)
            
            await ws.send(json.dumps({"id": 5, "method": "Page.captureScreenshot", "params": {"format": "png", "captureBeyondViewport": True}}))
            
            while True:
                raw = await ws.recv()
                msg = json.loads(raw)
                if msg.get("id") == 5 and "result" in msg:
                    data = base64.b64decode(msg["result"]["data"])
                    dest1 = os.path.abspath("../dashboard_live.png")
                    dest2 = r"C:\Users\91866\.gemini\antigravity\brain\a27a647c-2a51-428d-a8f8-a1f4feb77c22\dashboard_live.png"
                    with open(dest1, "wb") as f:
                        f.write(data)
                    with open(dest2, "wb") as f:
                        f.write(data)
                    print(f"SUCCESS: Snapshot written to {dest1} and {dest2} (size: {len(data)} bytes)")
                    break
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(snap())
