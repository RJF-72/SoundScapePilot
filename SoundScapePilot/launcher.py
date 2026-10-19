"""SoundScape Pilot desktop launcher.

Starts the FastAPI backend as a subprocess on 127.0.0.1 (ephemeral port)
and shows the UI in a native desktop window via pywebview (Edge WebView2
on Windows). No browser, no port configuration, no URLs exposed to the user.

First run: generates %APPDATA%/SoundScapePilot/config.json with a random
JWT secret + owner credentials, and shows them once on a welcome screen.
All failures are logged to %APPDATA%/SoundScapePilot/launcher.log.
"""
import json
import logging
import os
import secrets
import subprocess
import sys
import time

APP_NAME = "SoundScapePilot"
EXE_NAME = "SoundScapePilot.exe"


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


def find_free_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    log.info("launcher starting (frozen=%s)", getattr(sys, "frozen", False))

    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)

    # --- owner credentials: zero-config desktop setup ---
    cfg, first_run = load_or_create_config()
    os.environ.setdefault("JWT_SECRET", cfg["jwt_secret"])
    os.environ.setdefault("OWNER_EMAILS", cfg["owner_email"])
    os.environ.setdefault("OWNER_MASTER_PASSWORD", cfg["owner_password"])
    os.environ.setdefault("SOUNDSCAPE_DATA_DIR", os.path.join(APP_DIR, "data"))

    module = "home"

    # --- start backend as a subprocess on 127.0.0.1 ---
    port = find_free_port()
    env = os.environ.copy()
    env["PORT"] = str(port)
    server_path = os.path.join(base, "server.py")
    py_exe = "python" if getattr(sys, "frozen", False) else sys.executable
    backend_log_path = os.path.join(APP_DIR, "backend.log")
    backend_log = open(backend_log_path, "w", encoding="utf-8", errors="replace")
    log.info("subprocess: %s %s (exists=%s) env JWT=%s OWNER=%s PYTHONHOME=%s PYTHONPATH=%s",
             py_exe, server_path, os.path.exists(server_path),
             bool(env.get("JWT_SECRET")), bool(env.get("OWNER_EMAILS")),
             env.get("PYTHONHOME"), env.get("PYTHONPATH"))
    proc = subprocess.Popen(
        [py_exe, server_path],
        env=env,
        stdout=backend_log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    backend_log.close()
    log.info("backend subprocess started pid=%d port=%d", proc.pid, port)

    # wait for backend to accept connections
    import socket
    ready = False
    for _ in range(200):
        if proc.poll() is not None:
            log.error("backend subprocess exited early with code %s", proc.returncode)
            raise SystemExit(1)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                ready = True
                break
        except OSError:
            time.sleep(0.1)
    if not ready:
        log.error("backend failed to start on port %d", port)
        proc.terminate()
        raise SystemExit(1)

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
        window.load_html(FIRST_RUN_HTML.format(
            email=cfg["owner_email"], password=cfg["owner_password"]))
    log.info("opening desktop window")
    try:
        webview.start()
    finally:
        proc.terminate()
        log.info("shutdown")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("launcher crashed")
        raise
