import asyncio
import json
import os
import subprocess
import time
import urllib.request
import base64
import websockets

SCREENSHOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend_step2_screenshot.png"))
ARTIFACT_SCREENSHOT_PATH = r"C:\Users\91866\.gemini\antigravity\brain\a27a647c-2a51-428d-a8f8-a1f4feb77c22\frontend_step2_screenshot.png"

class CDPClient:
    def __init__(self, ws):
        self.ws = ws
        self.req_id = 0
        self.pending = {}
        self.running = True
        self.listen_task = asyncio.create_task(self._listener())

    async def _listener(self):
        try:
            while self.running:
                raw = await self.ws.recv()
                msg = json.loads(raw)
                if "id" in msg and msg["id"] in self.pending:
                    fut = self.pending.pop(msg["id"])
                    if not fut.done():
                        fut.set_result(msg)
        except Exception:
            pass

    async def send_cmd(self, method, params=None):
        self.req_id += 1
        cid = self.req_id
        fut = asyncio.get_event_loop().create_future()
        self.pending[cid] = fut
        payload = {"id": cid, "method": method}
        if params:
            payload["params"] = params
        await self.ws.send(json.dumps(payload))
        return await fut

    async def close(self):
        self.running = False
        self.listen_task.cancel()

async def capture_frontend_screenshot():
    print("Locating browser...")
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    browser_bin = next((p for p in edge_paths if os.path.exists(p)), None)
    if not browser_bin:
        raise RuntimeError("No Chrome or Edge browser binary found.")

    port = 9222
    user_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "browser_data_temp"))
    os.makedirs(user_data_dir, exist_ok=True)

    cmd = [
        browser_bin,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1440,1500",
        "http://127.0.0.1:5173"
    ]

    proc = subprocess.Popen(cmd)
    try:
        list_url = f"http://127.0.0.1:{port}/json/list"
        page_ws_url = None
        for _ in range(30):
            try:
                with urllib.request.urlopen(list_url, timeout=1) as resp:
                    pages = json.loads(resp.read().decode("utf-8"))
                    for p in pages:
                        if p.get("type") == "page" and p.get("webSocketDebuggerUrl"):
                            page_ws_url = p.get("webSocketDebuggerUrl")
                            break
                    if page_ws_url:
                        break
            except Exception:
                await asyncio.sleep(0.5)

        if not page_ws_url:
            raise RuntimeError("Could not find page websocket.")

        print(f"Connecting to CDP page: {page_ws_url}")
        async with websockets.connect(page_ws_url, max_size=100*1024*1024) as ws:
            cdp = CDPClient(ws)
            await cdp.send_cmd("Page.enable")
            await cdp.send_cmd("Runtime.enable")
            await cdp.send_cmd("Page.navigate", {"url": "http://127.0.0.1:5173"})

            print("Waiting for page load...")
            await asyncio.sleep(3.0)

            # Set user role in localStorage and ensure Log Complaint view
            setup_js = """
            (() => {
                localStorage.setItem('role', 'user');
                localStorage.setItem('actor', 'qa.officer@pharma.com');
                const btns = Array.from(document.querySelectorAll('button, a'));
                const logBtn = btns.find(b => b.textContent && b.textContent.includes('Log Complaint'));
                if (logBtn) logBtn.click();
                return true;
            })()
            """
            await cdp.send_cmd("Runtime.evaluate", {"expression": setup_js, "returnByValue": True})
            await asyncio.sleep(1.0)

            # Send prompt to Copilot chat using text input
            send_js = """
            (() => {
                const textInput = document.querySelector('input[placeholder*="Paste complaint"], input[placeholder*="describe issue"]') ||
                                  document.querySelector('form input[type="text"]');
                if (!textInput) return { error: 'no text input found' };
                
                const msg = "Apollo Pharmacy reported 12 discolored capsules in Amoxicillin Capsules 500mg. Batch number AMX240602. Manufacturing date March 2026. Expiry date February 2028. Please log this complaint.";
                
                const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                setter.call(textInput, msg);
                textInput.dispatchEvent(new Event('input', { bubbles: true }));
                textInput.dispatchEvent(new Event('change', { bubbles: true }));
                
                const form = textInput.closest('form');
                const btn = form ? form.querySelector('button[type="submit"]') : null;
                if (btn) {
                    btn.disabled = false;
                    btn.click();
                    return { status: 'button_clicked', val: textInput.value };
                }
                return { status: 'no_btn' };
            })()
            """
            send_res = await cdp.send_cmd("Runtime.evaluate", {"expression": send_js, "returnByValue": True})
            print(f"Copilot submission status: {send_res.get('result', {}).get('result', {}).get('value')}")

            print("Waiting for AI Copilot processing and form population...")
            for i in range(40):
                await asyncio.sleep(1.0)
                check_js = """
                (() => {
                    const prodInput = document.querySelector('#product_name');
                    const badge = document.querySelector('span[class*="badgeReady"]') || Array.from(document.querySelectorAll('*')).find(el => el.textContent && el.textContent.includes('Ready to Commit'));
                    const sevBox = document.querySelector('#severity');
                    const desc = document.querySelector('#complaint_description');
                    return {
                        product_name: prodInput ? prodInput.value : '',
                        ready_badge: Boolean(badge),
                        severity: sevBox ? sevBox.value : '',
                        desc: desc ? desc.value : ''
                    };
                })()
                """
                check_res = await cdp.send_cmd("Runtime.evaluate", {"expression": check_js, "returnByValue": True})
                val = check_res.get("result", {}).get("result", {}).get("value", {})
                if val.get("product_name") or val.get("ready_badge"):
                    print(f"Form successfully populated in {i+1}s: {val}")
                    break

            await asyncio.sleep(3.0)

            # Capture screenshot
            print("Capturing screenshot...")
            s_res = await cdp.send_cmd("Page.captureScreenshot", {"format": "png", "quality": 100, "captureBeyondViewport": True})
            img_b64 = s_res.get("result", {}).get("data")
            if img_b64:
                raw_bytes = base64.b64decode(img_b64)
                with open(SCREENSHOT_PATH, "wb") as f:
                    f.write(raw_bytes)
                os.makedirs(os.path.dirname(ARTIFACT_SCREENSHOT_PATH), exist_ok=True)
                with open(ARTIFACT_SCREENSHOT_PATH, "wb") as f:
                    f.write(raw_bytes)
                print(f"SUCCESS: Screenshot saved to {SCREENSHOT_PATH} and {ARTIFACT_SCREENSHOT_PATH}")
            else:
                print(f"Screenshot capture failed: {s_res}")

            await cdp.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(capture_frontend_screenshot())
