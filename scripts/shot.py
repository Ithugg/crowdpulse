"""Screenshot of the running console at its true size, through headless Edge's DevTools protocol.

    .\\scripts\\py.ps1 scripts\\shot.py runs\\console.png 1366 768 20 "4"
                                     output            w    h   wait keys

The keys are pressed one second apart after the page loads ("4" = camera 4, "5g" = camera 5 then the
grid), then the script waits `wait` seconds and saves the PNG. Set SHOT_URL for another port.
The server must already be running. Remember that overlay keys (g, b, h, v) change the server's
state for every viewer: press them again afterwards to put things back.
"""
import asyncio
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websockets

REPO_ROOT = Path(__file__).resolve().parent.parent
EDGE_PATHS = (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")
DEBUG_PORT = 9333

out, width, height, wait_s = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
keys = sys.argv[5] if len(sys.argv) > 5 else ""
edge = os.environ.get("EDGE_PATH") or next((p for p in EDGE_PATHS if Path(p).exists()), None)
if edge is None:
    sys.exit("Microsoft Edge not found. Set EDGE_PATH to msedge.exe (or chrome.exe).")

proc = subprocess.Popen(
    [edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
     f"--remote-debugging-port={DEBUG_PORT}", f"--user-data-dir={REPO_ROOT / 'runs' / 'edge-profile'}",
     f"--window-size={width},{height}", "about:blank"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def main():
    for _ in range(40):
        try:
            targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json"))
            break
        except Exception:
            time.sleep(0.25)
    page = next(t for t in targets if t["type"] == "page")
    async with websockets.connect(page["webSocketDebuggerUrl"], max_size=50_000_000) as ws:
        n = 0

        async def call(method, **params):
            nonlocal n
            n += 1
            await ws.send(json.dumps({"id": n, "method": method, "params": params}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == n:
                    return msg.get("result", {})

        await call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
        await call("Page.navigate", url=os.environ.get("SHOT_URL", "http://localhost:8000/"))
        await asyncio.sleep(3)
        for key in keys:
            await call("Input.dispatchKeyEvent", type="keyDown", key=key, text=key)
            await call("Input.dispatchKeyEvent", type="keyUp", key=key)
            await asyncio.sleep(1.0)
        await asyncio.sleep(wait_s)
        shot = await call("Page.captureScreenshot", format="png")
        Path(out).write_bytes(base64.b64decode(shot["data"]))
        print("saved", out)


try:
    asyncio.run(main())
finally:
    proc.terminate()
