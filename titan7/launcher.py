"""SoundScape Pilot desktop launcher.

Runs the FastAPI backend on 127.0.0.1 (ephemeral port, invisible to the
user) and shows the UI in a native desktop window via pywebview (Edge
WebView2 on Windows). No browser, no port configuration.

First run: generates %APPDATA%/SoundScapePilot/config.json with a random
JWT secret + owner credentials, and shows them once on a welcome screen.
All failures are logged to %APPDATA%/SoundScapePilot/launcher.log so a
silent exit is always diagnosable (the frozen exe has no console).
"""
import json
import logging
import os
import secrets
import sys
import threading
import time

APP_NAME = "SoundScapePilot"
EXE_NAME = "SoundScapePilot.exe"

URL_MAP = {
    "dashboard": "home",
    "home": "home",
    "radio-autopilot": "radio",
    "booking-agent": "booking",
    "press-wire": "pr",
    "master-autopilot": "autopilot",
    "aegis-security": "security",
    "web-browser": "browser",
    "titan-meet": "meet",
    "ai-marketing": "marketing",
}


def app_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "SoundScapePilot")
    os.makedirs(d, exist_ok=True)
    return d


APP_DIR = app_dir()
LOG_PATH = os.path.join(APP_DIR, "launcher.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("launcher")


def load_or_create_config():
    cfg_path = os.path.join(APP_DIR, "config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f), False
    cfg = {
        "jwt_secret": secrets.token_hex(32),
        "owner_email": "owner@localhost",
        "owner_password": secrets.token_urlsafe(16),
    }
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    log.info("created first-run config at %s", cfg_path)
    return cfg, True


def register_protocol():
    # titan7:// deep links (kept for backwards compatibility)
    try:
        import winreg
        root = winreg.HKEY_CURRENT_USER
        sub = r"Software\Classes\titan7"
        key = winreg.CreateKey(root, sub)
        winreg.SetValue(key, "", winreg.REG_SZ, "URL:SoundScape Pilot Protocol")
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        winreg.CloseKey(key)
        cmd_key = winreg.CreateKey(root, sub + r"\shell\open\command")
        exe_path = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])
        winreg.SetValue(cmd_key, "", winreg.REG_SZ, '"%s" "%%1"' % exe_path)
        winreg.CloseKey(cmd_key)
    except Exception as e:
        log.warning("protocol registration failed: %s", e)


FIRST_RUN_HTML = """<!doctype html><html><head><meta charset="utf-8">
<title>Welcome to SoundScape Pilot</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#14100c;color:#f3e9d7;
display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{background:#221a12;border:1px solid #6b4a2a;border-radius:12px;
padding:36px 44px;max-width:520px;box-shadow:0 8px 32px #0008}}
h1{{color:#e8a33d;margin-top:0}}code{{background:#0f0c09;padding:10px 14px;
border-radius:6px;display:block;margin:8px 0;font-size:15px;color:#ffd98a;
user-select:all}}button{{background:#e8a33d;color:#1a120a;border:0;
border-radius:8px;padding:12px 28px;font-size:16px;font-weight:700;
cursor:pointer;margin-top:16px}}button:hover{{background:#f5b654}}
.small{{color:#a68b64;font-size:13px;margin-top:14px}}
</style></head><body><div class="card">
<h1>Welcome to SoundScape Pilot</h1>
<p>Your private owner login (save this somewhere safe):</p>
<p><b>Email</b><code>{email}</code></p>
<p><b>Password</b><code>{password}</code></p>
<button onclick="pywebview.api.open_app()">Continue to SoundScape Pilot</button>
<p class="small">You only see this once. The app opens in its own window.</p>
</div></body></html>"""


class Api:
    def __init__(self, app_url):
        self.app_url = app_url

    def open_app(self):
        import webview
        for w in webview.windows:
            w.load_url(self.app_url)


def main():
    log.info("launcher starting (frozen=%s)", getattr(sys, "frozen", False))

    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)

    # --- owner credentials: zero-config desktop setup ---
    cfg, first_run = load_or_create_config()
    os.environ.setdefault("JWT_SECRET", cfg["jwt_secret"])
    os.environ.setdefault("OWNER_EMAILS", cfg["owner_email"])
    os.environ.setdefault("OWNER_MASTER_PASSWORD", cfg["owner_password"])
    os.environ.setdefault("TITAN7_DATA_DIR", os.path.join(APP_DIR, "data"))

    # --- deep-link module (titan7://...) ---
    module = "home"
    for arg in sys.argv[1:]:
        if arg.startswith("titan7://"):
            path = arg.replace("titan7://", "").split("/")[0]
            module = URL_MAP.get(path, "home")
            break

    if not getattr(sys, "frozen", False):
        register_protocol()

    # --- start backend on 127.0.0.1, OS-assigned port ---
    import asyncio
    import uvicorn
    uv_config = uvicorn.Config("server:app", host="127.0.0.1", port=0,
                               log_level="warning")
    uv_server = uvicorn.Server(uv_config)

    def _serve():
        asyncio.run(uv_server.serve())

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    for _ in range(200):
        if uv_server.started:
            break
        time.sleep(0.1)
    else:
        log.error("backend failed to start; see log")
        raise SystemExit(1)
    port = uv_server.servers[0].sockets[0].getsockname()[1]
    app_url = "http://127.0.0.1:%d/?module=%s" % (port, module)
    log.info("backend up on 127.0.0.1:%d", port)

    # --- native desktop window (no browser, no visible port) ---
    import webview
    api = Api(app_url)
    window = webview.create_window(
        "SoundScape Pilot", url=app_url, js_api=api,
        width=1280, height=800, min_size=(960, 600),
    )
    if first_run:
        # show credentials once, then continue into the app
        window.load_html(FIRST_RUN_HTML.format(
            email=cfg["owner_email"], password=cfg["owner_password"]))
    log.info("opening desktop window")
    try:
        webview.start()
    finally:
        uv_server.should_exit = True
        log.info("shutdown")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("launcher crashed")
        raise
