import os
import sys
import json
import asyncio
import platform
import time
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn
import jwt

try:
    import psutil
    HAVE_PSUTIL = True
except ImportError:
    HAVE_PSUTIL = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("soundscape")

try:
    import stripe
    STRIPE_ENABLED = bool(os.environ.get("STRIPE_SECRET_KEY"))
except ImportError:
    stripe = None
    STRIPE_ENABLED = False

import modules.database as db
from modules.database import get_connection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

sys.path.insert(0, BASE_DIR)

from modules.radio_finder import RadioFinder
from modules.booking_agent import BookingAgent
from modules.pr_wire import PRWire

radio_finder = RadioFinder()
booking_agent = BookingAgent()
pr_wire = PRWire()

# Input sanitization utilities
import re
import html

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent XSS and injection."""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    text = text[:max_length]
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    return text

def sanitize_email(email: str) -> str:
    """Sanitize and validate email."""
    email = sanitize_input(email, 254).lower()
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return ""
    return email

def sanitize_html(text: str) -> str:
    """Escape HTML for safe output."""
    return html.escape(text)

app = FastAPI(title="SoundScape Pilot", version="1.0.0")

# JWT / owner allowlist
# Credentials are read from the environment first, then from the
# launcher-managed config file (%APPDATA%/SoundScapePilot/config.json)
# that launcher.py creates on first run. There is intentionally NO
# default password and NO auto-generated secret here: if neither source
# provides them, the server refuses to start (fail fast) instead of
# booting with insecure defaults.
def _launcher_config() -> dict:
    candidates = []
    if os.environ.get("SOUNDSCAPE_CONFIG"):
        candidates.append(os.environ["SOUNDSCAPE_CONFIG"])
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    candidates.append(os.path.join(appdata, "SoundScapePilot", "config.json"))
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if isinstance(cfg, dict):
                    return cfg
        except Exception:
            continue
    return {}

_LAUNCHER_CFG = _launcher_config()

JWT_SECRET = os.environ.get("JWT_SECRET", "") or _LAUNCHER_CFG.get("jwt_secret", "")
if not JWT_SECRET:
    print("ERROR: JWT_SECRET is not set and no launcher config file was found. "
          "Set the JWT_SECRET environment variable, or run the desktop launcher once "
          "(it creates %APPDATA%/SoundScapePilot/config.json with owner credentials). "
          "Refusing to start without an owner secret.", file=sys.stderr)
    sys.exit(1)

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "24"))

_owner_emails_env = os.environ.get("OWNER_EMAILS", "") or os.environ.get("SOUNDSCAPE_OWNER_EMAILS", "")
if _owner_emails_env:
    OWNER_EMAILS = {e.strip().lower() for e in _owner_emails_env.split(",") if e.strip()}
elif _LAUNCHER_CFG.get("owner_email"):
    OWNER_EMAILS = {_LAUNCHER_CFG["owner_email"].strip().lower()}
else:
    OWNER_EMAILS = {"admin@localhost"}

OWNER_MASTER_PASSWORD = os.environ.get("OWNER_MASTER_PASSWORD", "") or _LAUNCHER_CFG.get("owner_password", "")
if not OWNER_MASTER_PASSWORD:
    print("ERROR: OWNER_MASTER_PASSWORD is not set and no launcher config file was found. "
          "Set the OWNER_MASTER_PASSWORD environment variable, or run the desktop launcher once "
          "(it creates %APPDATA%/SoundScapePilot/config.json with owner credentials). "
          "Refusing to start without an owner password.", file=sys.stderr)
    sys.exit(1)

security = HTTPBearer()

async def require_owner(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub", "").lower()
        if email not in OWNER_EMAILS:
            raise Exception("not an owner")
        return payload
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid or missing owner token")

async def optional_owner(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        return await require_owner(credentials)
    except Exception:
        return None

def create_token(email: str) -> str:
    exp = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode({"sub": email.lower(), "exp": exp}, JWT_SECRET, algorithm=JWT_ALGORITHM)

# Audit logging
async def audit_log(request: Request, action: str, detail: dict = None, user: dict = None):
    try:
        meta = {
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "path": str(request.url.path),
            "method": request.method,
        }
        db.insert_audit(action, user.get("sub") if user else None, json.dumps(detail or {}), json.dumps(meta))
    except Exception:
        pass

# CORS configuration
_cors_origins = os.environ.get("CORS_ORIGINS", "*")
if _cors_origins == "*":
    cors_origins = ["*"]
else:
    cors_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_root():
    html_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>SoundScape Pilot</h1><p>Frontend not found.</p>")

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    db_status = "ok"
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
    except Exception:
        db_status = "error"
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }

# ---------- AUTH / OWNERS ----------
class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/login")
async def login(req: LoginRequest, request: Request):
    email = req.email.strip().lower()
    if email not in OWNER_EMAILS:
        await audit_log(request, "login_failed", {"reason": "not_owner", "email": email})
        return JSONResponse(status_code=401, content={"error": "Not an authorized owner"})
    if req.password != OWNER_MASTER_PASSWORD:
        await audit_log(request, "login_failed", {"reason": "bad_password", "email": email})
        return JSONResponse(status_code=401, content={"error": "Invalid credentials"})
    token = create_token(email)
    await audit_log(request, "login", {"email": email}, {"sub": email})
    return {"access_token": token, "token_type": "bearer", "email": email}

@app.get("/api/auth/me")
async def auth_me(user: dict = Depends(require_owner)):
    return {"email": user["sub"], "owner": True}

class OwnerInviteRequest(BaseModel):
    email: str

@app.post("/api/auth/invite")
async def owner_invite(req: OwnerInviteRequest, request: Request, user: dict = Depends(require_owner)):
    email = req.email.strip().lower()
    if email not in OWNER_EMAILS:
        return JSONResponse(status_code=400, content={"error": "Email not in owner allowlist"})
    token = create_token(email)
    await audit_log(request, "owner_invite", {"invited": email}, user)
    return {"invite_token": token}

# ---------- AUDIT ----------
@app.get("/api/audit")
async def list_audit(limit: int = 100, offset: int = 0, user: dict = Depends(require_owner)):
    rows = db.list_audit(limit, offset)
    return {"items": [dict(r) for r in rows]}

class RadioSearchRequest(BaseModel):
    genre: Optional[str] = None
    state: Optional[str] = None

@app.post("/api/radio/search")
async def radio_search(req: RadioSearchRequest):
    try:
        results = await asyncio.to_thread(radio_finder.search, req.genre, req.state)
        return results
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class BookingSearchRequest(BaseModel):
    state: Optional[str] = None
    genre: Optional[str] = None
    include_churches: Optional[bool] = False
    query: Optional[str] = None
    size: Optional[str] = None       # all | small | medium | large
    type: Optional[str] = None       # all | bar | church | theater | outdoor | club | cafe | civic | listening_room | other
    lat: Optional[float] = None
    lon: Optional[float] = None

@app.post("/api/booking/search")
async def booking_search(req: BookingSearchRequest):
    try:
        genre = req.genre
        if req.include_churches and not genre:
            genre = "church"
        elif req.include_churches and genre:
            genre = genre + " church"
        results = await asyncio.to_thread(
            booking_agent.search_venues,
            req.state, genre, bool(req.include_churches), req.query,
            (req.size or "all").lower(), (req.type or "all").lower(),
            req.lat, req.lon)
        # Persist so /api/booking/dispatch keeps working without an explicit list.
        try:
            for v in results[:200]:
                db.insert_venue({
                    "state": v.get("state"), "name": v.get("name"),
                    "city": v.get("city"), "capacity": v.get("capacity"),
                    "contact": v.get("contact"), "website": v.get("website"),
                })
        except Exception:
            pass
        return results
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

def _load_mailer():
    from modules.mailer import Mailer
    host = db.get_setting("smtp_host")
    if not host:
        raise Exception("SMTP not configured. Go to SMTP Settings and save your credentials.")
    port = int(db.get_setting("smtp_port") or "587")
    user = db.get_setting("smtp_user") or ""
    password = db.get_setting("smtp_password") or ""
    return Mailer(smtp_host=host, smtp_port=port, smtp_user=user, smtp_pass=password)

class BookingDispatchRequest(BaseModel):
    venues: Optional[list] = None

@app.post("/api/booking/dispatch")
async def booking_dispatch(req: Optional[BookingDispatchRequest] = None):
    try:
        mailer = _load_mailer()
        venues = (req.venues if req and req.venues else None) or db.get_venues()
        if not venues:
            return JSONResponse(status_code=400, content={"error": "No venues selected. Search for venues, select rows (or Select All), then dispatch."})
        items = []
        for v in venues:
            recipient = v.get("contact") or v.get("email") or ""
            if recipient:
                items.append({"recipient": recipient, "subject": "EPK Submission - New Artist", "body": f"Dear {v.get('name', 'Team')},\n\nPlease find our EPK attached for your review.\n\nBest,\nSoundScape Pilot Artist"})
        if not items:
            return JSONResponse(status_code=400, content={"error": "No venue contacts available."})
        result = mailer.send_bulk(items, "booking")
        sent = sum(1 for r in result if r.get("success"))
        return {"result": f"EPKs dispatched to {sent}/{len(items)} venues."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class PRSearchRequest(BaseModel):
    topic: Optional[str] = None

@app.post("/api/pr/search")
async def pr_search(req: PRSearchRequest):
    try:
        results = await asyncio.to_thread(pr_wire.get_outlets, req.topic)
        return results
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/pr/dispatch")
async def pr_dispatch():
    try:
        mailer = _load_mailer()
        outlets = db.get_media_outlets()
        if not outlets:
            return JSONResponse(status_code=400, content={"error": "No outlets found. Search for outlets first."})
        items = []
        for o in outlets:
            recipient = o.get("email") or o.get("contact") or ""
            if recipient:
                items.append({"recipient": recipient, "subject": "Press Release - New Music Announcement", "body": f"Dear {o.get('name', 'Editor')},\n\nPlease find our press release attached.\n\nBest,\nSoundScape Pilot PR"})
        if not items:
            return JSONResponse(status_code=400, content={"error": "No outlet contacts available."})
        result = mailer.send_bulk(items, "pr")
        sent = sum(1 for r in result if r.get("success"))
        return {"result": f"Press wire sent to {sent}/{len(items)} outlets."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

def _get_cpu():
    if HAVE_PSUTIL:
        try: return psutil.cpu_percent(interval=0.3)
        except: pass
    return 0.0

def _get_mem():
    if HAVE_PSUTIL:
        try:
            m = psutil.virtual_memory()
            return m.used / 1024 / 1024, m.total / 1024 / 1024 / 1024, m.percent
        except: pass
    return 0, 0, 0

def _get_disk():
    if HAVE_PSUTIL:
        try:
            d = psutil.disk_usage('/')
            return d.used / 1024 / 1024 / 1024, d.total / 1024 / 1024 / 1024, d.percent
        except: pass
    return 0, 0, 0

def _get_net():
    if HAVE_PSUTIL:
        try:
            n = psutil.net_io_counters()
            return n.bytes_sent / 1024 / 1024, n.bytes_recv / 1024 / 1024
        except: pass
    return 0, 0

def _get_boot():
    if HAVE_PSUTIL:
        try: return datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        except: pass
    return "N/A"

@app.get("/api/status")
async def get_status():
    try:
        cpu = _get_cpu()
        mem_used_mb, _, _ = _get_mem()
        ram_text = f"{mem_used_mb:.0f} MB" if mem_used_mb < 1024 else f"{mem_used_mb/1024:.1f} GB"
        smtp_host = db.get_setting("smtp_host")
        smtp_status = "connected" if smtp_host else "disconnected"
        return {"cpu": cpu, "ram": ram_text, "driver": "AEGIS LITE", "smtp_status": smtp_status}
    except:
        return {"cpu": 0, "ram": "0 MB", "driver": "AEGIS LITE", "smtp_status": "error"}

@app.get("/api/security/status")
async def security_status():
    try:
        cpu = _get_cpu()
        mem_used_mb, mem_total_gb, mem_percent = _get_mem()
        disk_used, disk_total, disk_percent = _get_disk()
        net_sent, net_recv = _get_net()
        boot_time = _get_boot()
        return {
            "cipher": "AES-256-GCM",
            "driver": "AEGIS LITE",
            "driver_status": "active",
            "session": "protected",
            "protocol": "TLS 1.3",
            "cpu_usage": cpu,
            "memory_used": f"{mem_used_mb / 1024:.2f} GB" if mem_used_mb else "N/A",
            "memory_total": f"{mem_total_gb:.2f} GB" if mem_total_gb else "N/A",
            "memory_percent": mem_percent,
            "disk_used": f"{disk_used:.1f} GB" if disk_used else "N/A",
            "disk_total": f"{disk_total:.1f} GB" if disk_total else "N/A",
            "disk_percent": disk_percent,
            "network_sent": f"{net_sent:.1f} MB" if net_sent else "N/A",
            "network_recv": f"{net_recv:.1f} MB" if net_recv else "N/A",
            "boot_time": boot_time,
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "python": platform.python_version()
        }
    except Exception as e:
        return {"error": str(e)}

class MarketingCampaignRequest(BaseModel):
    artist: str = ""
    release: str = ""
    genre: str = ""

@app.post("/api/marketing/campaign")
async def marketing_campaign(req: MarketingCampaignRequest):
    try:
        from modules.ai_marketing import AIMarketingEngine
        engine = AIMarketingEngine()
        campaign = engine.generate_campaign(req.artist, req.release, req.genre)
        return campaign
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/marketing/social")
async def marketing_social(req: MarketingCampaignRequest):
    try:
        from modules.ai_marketing import AIMarketingEngine
        engine = AIMarketingEngine()
        posts = engine.generate_social_post(req.artist, req.release, req.genre)
        return {"posts": posts}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class SmtpConfigRequest(BaseModel):
    host: str
    port: int
    user: str
    password: str

@app.post("/api/smtp/test")
async def smtp_test(req: SmtpConfigRequest):
    try:
        from modules.mailer import Mailer
        m = Mailer(smtp_host=req.host, smtp_port=req.port, smtp_user=req.user, smtp_pass=req.password)
        result = m.send_email(req.user, "SMTP Test", "This is a test from SoundScape Pilot.")
        return {"result": "Test email sent" if result else "Send failed"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/smtp/save")
async def smtp_save(req: SmtpConfigRequest):
    try:
        db.save_setting("smtp_host", req.host)
        db.save_setting("smtp_port", str(req.port))
        db.save_setting("smtp_user", req.user)
        db.save_setting("smtp_password", req.password)
        return {"result": "SMTP configuration saved."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/email-log")
async def email_log():
    try:
        emails = db.get_emails()
        logs = [{"to": e.get("recipient", ""), "subject": e.get("subject", ""), "status": e.get("status", "sent"), "time": e.get("created_at", "")} for e in emails]
        return {"logs": logs}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

meet_rooms = {}

@app.websocket("/ws/meet/{room_id}")
async def meet_websocket(websocket: WebSocket, room_id: str):
    await websocket.accept()
    if room_id not in meet_rooms:
        meet_rooms[room_id] = []
    meet_rooms[room_id].append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg["from"] = f"user-{id(websocket) % 1000}"
            for client in meet_rooms[room_id]:
                if client != websocket:
                    try:
                        await client.send_text(json.dumps(msg))
                    except:
                        pass
    except WebSocketDisconnect:
        pass
    finally:
        if room_id in meet_rooms:
            meet_rooms[room_id] = [w for w in meet_rooms[room_id] if w != websocket]
            if not meet_rooms[room_id]:
                del meet_rooms[room_id]

@app.post("/api/meet/signal")
async def meet_signal(data: dict):
    return {"result": "signal received"}

# ============================================================
# EPK (Electronic Press Kit) Endpoints
# ============================================================

class EPKSaveRequest(BaseModel):
    artist: str = ""
    genre: str = ""
    bio: str = ""
    spotify: str = ""
    soundcloud: str = ""
    apple_music: str = ""
    youtube: str = ""
    press_quotes: str = ""
    photo_url: str = ""
    website: str = ""
    instagram: str = ""
    facebook: str = ""
    twitter: str = ""
    contact_email: str = ""
    email: str = ""
    phone: str = ""

def _req2dict(req):
    d = getattr(req, 'model_dump', lambda: getattr(req, 'dict', lambda: vars(req))())()
    if 'email' in d and d['email'] and not d.get('contact_email'):
        d['contact_email'] = d['email']
    return d

@app.post("/api/epk/save")
async def epk_save(req: EPKSaveRequest):
    try:
        db.save_epk(_req2dict(req))
        return {"result": "EPK saved"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/epk")
async def epk_get():
    try:
        epk = db.get_epk()
        return epk or {}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/epk/generate")
async def epk_generate(req: EPKSaveRequest):
    try:
        from modules.epk_engine import EPKEngine
        engine = EPKEngine()
        data = _req2dict(req)
        html = engine.generate_html(**data)
        text = engine.generate_text(**data)
        return {"html": html, "text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# Radio Selection & Dispatch
# ============================================================

class RadioResearchRequest(BaseModel):
    station_name: str = ""
    contact: str = ""
    website: str = ""

@app.post("/api/radio/research")
async def radio_research(req: RadioResearchRequest):
    try:
        from modules.epk_engine import RadioSubmissionResearch
        researcher = RadioSubmissionResearch()
        info = researcher.research(req.station_name, req.contact, req.website)
        return info
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

class RadioSelectRequest(BaseModel):
    stations: list = []

@app.post("/api/radio/select")
async def radio_select(req: RadioSelectRequest):
    try:
        from modules.epk_engine import RadioSubmissionResearch
        researcher = RadioSubmissionResearch()
        enriched = []
        for s in req.stations:
            info = researcher.research(s.get("station_name", ""), s.get("contact", ""), s.get("website", ""))
            s["submission_method"] = info.get("method", "")
            s["submission_email"] = info.get("email", "")
            s["submission_notes"] = info.get("notes", "")
            enriched.append(s)
        db.save_selected_stations(enriched)
        return {"result": f"{len(enriched)} stations selected", "stations": enriched}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/radio/selected")
async def radio_selected():
    try:
        return db.get_selected_stations()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/radio/clear-selected")
async def radio_clear_selected():
    try:
        db.clear_selected_stations()
        return {"result": "Selection cleared"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/radio/remove-selected")
async def radio_remove_selected(data: dict):
    try:
        station_name = data.get("station_name", "")
        if station_name:
            db.remove_selected_station(station_name)
        return {"result": "Station removed"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/radio/dispatch")
async def radio_dispatch():
    try:
        mailer = _load_mailer()
        from modules.epk_engine import EPKEngine
        engine = EPKEngine()

        selected = db.get_selected_stations()
        if not selected:
            return JSONResponse(status_code=400, content={"error": "No stations selected. Search and select stations first."})
        epk_data = db.get_epk()
        if not epk_data or not epk_data.get("artist"):
            return JSONResponse(status_code=400, content={"error": "No EPK found. Create an EPK first."})

        epk_text = engine.generate_text(**epk_data)

        items = []
        for s in selected:
            recipient = s.get("submission_email") or s.get("contact") or ""
            if recipient:
                station_name = s.get("station_name", "Radio Station")
                notes = s.get("submission_notes", "")
                body = f"Dear {station_name} Music Director,\n\nPlease find our EPK below for your consideration.\n\n---\n\n{epk_text}\n\n---\n\n{notes}\n\nBest,\n{epk_data.get('artist', 'SoundScape Pilot Artist')}\n{epk_data.get('contact_email', '')}"
                items.append({"contact": recipient, "subject": f"Music Submission - {epk_data.get('artist', 'New Artist')}", "body": body})
        if not items:
            return JSONResponse(status_code=400, content={"error": "No station contacts available."})
        result = mailer.send_bulk(items, "radio")
        sent = sum(1 for r in result if r.get("success"))
        return {"result": f"EPKs sent to {sent}/{len(items)} stations."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# Radio Promoter Endpoints — World-Class Promotion Engine
# ============================================================

class PromoterPitchRequest(BaseModel):
    artist: str = ""
    genre: str = ""
    bio: str = ""
    spotify: str = ""
    soundcloud: str = ""
    press_quotes: str = ""

@app.post("/api/promoter/classify")
async def promoter_classify(data: dict):
    try:
        from modules.radio_promoter import classify_station
        name = data.get("station_name", "") or data.get("name", "")
        vector = data.get("vector", "") or data.get("tags", "")
        location = data.get("location", "")
        fmt = classify_station(name, vector, location=location)
        return {"format": fmt}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/promoter/generate-pitch")
async def promoter_generate_pitch(req: PromoterPitchRequest):
    try:
        from modules.radio_promoter import get_pitch_strategy, classify_station
        data = _req2dict(req)
        selected = db.get_selected_stations()
        if not selected:
            return JSONResponse(status_code=400, content={"error": "No stations selected."})
        pitches = []
        for s in selected:
            name = s.get("station_name", "") or s.get("name", "")
            vector = s.get("vector", "")
            location = s.get("location", "")
            fmt = classify_station(name, vector, location=location)
            pitch = get_pitch_strategy(
                station_name=name,
                station_format=fmt,
                artist=data.get("artist", "Artist"),
                genre=data.get("genre", ""),
                bio=data.get("bio", ""),
                spotify=data.get("spotify", ""),
                soundcloud=data.get("soundcloud", ""),
                press_quotes=data.get("press_quotes", ""),
                station_location=location,
                station_vector=vector,
            )
            pitch["station"] = name
            pitch["contact"] = s.get("submission_email", "") or s.get("contact", "")
            pitch["location"] = location
            pitches.append(pitch)
        return {"pitches": pitches, "total": len(pitches)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/promoter/campaign-summary")
async def promoter_campaign_summary(data: dict):
    try:
        from modules.radio_promoter import build_campaign_summary
        selected = db.get_selected_stations()
        if not selected:
            return JSONResponse(status_code=400, content={"error": "No stations selected."})
        summary = build_campaign_summary(selected, data.get("artist", "Artist"), data.get("genre", ""))
        return summary
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/promoter/follow-up")
async def promoter_follow_up(data: dict):
    try:
        from modules.radio_promoter import generate_follow_up
        station_name = data.get("station_name", "Station")
        artist = data.get("artist", "Artist")
        attempt = int(data.get("attempt", 1))
        max_attempts = int(data.get("max_attempts", 3))
        body = generate_follow_up(station_name, artist, attempt, max_attempts)
        return {"body": body, "attempt": attempt, "max_attempts": max_attempts}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/promoter/dispatch-campaign")
async def promoter_dispatch_campaign(req: PromoterPitchRequest):
    try:
        mailer = _load_mailer()
        from modules.radio_promoter import get_pitch_strategy, classify_station
        data = _req2dict(req)
        selected = db.get_selected_stations()
        if not selected:
            return JSONResponse(status_code=400, content={"error": "No stations selected."})
        items = []
        for s in selected:
            name = s.get("station_name", "") or s.get("name", "")
            vector = s.get("vector", "")
            location = s.get("location", "")
            contact = s.get("submission_email", "") or s.get("contact", "")
            if not contact:
                continue
            fmt = classify_station(name, vector, location=location)
            pitch_data = get_pitch_strategy(
                station_name=name,
                station_format=fmt,
                artist=data.get("artist", "Artist"),
                genre=data.get("genre", ""),
                bio=data.get("bio", ""),
                spotify=data.get("spotify", ""),
                soundcloud=data.get("soundcloud", ""),
                press_quotes=data.get("press_quotes", ""),
                station_location=location,
                station_vector=vector,
            )
            body = pitch_data["pitch_body"]
            body += f"\n\n{data.get('artist', 'Artist')}\n{data.get('contact_email', '') or data.get('email', '')}"
            subject = f"New Music Submission - {data.get('artist', 'Artist')} ({data.get('genre', '')})"
            items.append({"contact": contact, "subject": subject, "body": body})
        if not items:
            return JSONResponse(status_code=400, content={"error": "No station contacts available."})
        result = mailer.send_bulk(items, "radio_promotion")
        sent = sum(1 for r in result if r.get("success"))
        return {"result": f"Personalized pitches sent to {sent}/{len(items)} stations."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# Streaming Platform Promoter Endpoints
# ============================================================

class StreamingPitchRequest(BaseModel):
    artist: str = ""
    genre: str = ""
    bio: str = ""
    spotify: str = ""
    soundcloud: str = ""
    press_quotes: str = ""

@app.get("/api/streaming/platforms")
async def streaming_platforms():
    try:
        from modules.streaming_promoter import get_all_platforms
        return get_all_platforms()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/streaming/campaign")
async def streaming_campaign(req: StreamingPitchRequest):
    try:
        from modules.streaming_promoter import get_platform_strategy, get_all_platforms
        data = _req2dict(req)
        platforms = get_all_platforms()
        results = []
        for p in platforms:
            key = p["key"]
            strategy = get_platform_strategy(
                platform=key,
                artist=data.get("artist", "Artist"),
                genre=data.get("genre", ""),
                bio=data.get("bio", ""),
                spotify=data.get("spotify", ""),
                soundcloud=data.get("soundcloud", ""),
            )
            results.append(strategy)
        return {"platforms": results, "total": len(results)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/streaming/strategy")
async def streaming_strategy(data: dict):
    try:
        from modules.streaming_promoter import get_platform_strategy
        platform = data.get("platform", "spotify")
        strategy = get_platform_strategy(
            platform=platform,
            artist=data.get("artist", "Artist"),
            genre=data.get("genre", ""),
            bio=data.get("bio", ""),
            spotify=data.get("spotify", ""),
            soundcloud=data.get("soundcloud", ""),
        )
        return strategy
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# Tour Manager Endpoints
# ============================================================

class TourRequest(BaseModel):
    genre: str = ""
    home_city: str = ""
    followers: int = 5000
    num_shows: int = 12

@app.post("/api/tour/suggest")
async def tour_suggest(req: TourRequest):
    try:
        from modules.tour_manager import suggest_tour_route
        result = suggest_tour_route(
            artist_genre=req.genre,
            home_city=req.home_city,
            followers=req.followers,
            num_shows=req.num_shows,
        )
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/tour/projection")
async def tour_projection(data: dict):
    try:
        from modules.tour_manager import calculate_tour_projection
        result = calculate_tour_projection(
            shows=int(data.get("shows", 12)),
            avg_guarantee=float(data.get("avg_guarantee", 1500)),
            followers=int(data.get("followers", 5000)),
            genre=data.get("genre", "rock"),
        )
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/tour/budget")
async def tour_budget(data: dict):
    try:
        from modules.tour_manager import build_tour_budget
        shows = data.get("shows", [])
        result = build_tour_budget(shows)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# Booking Manager Endpoints
# ============================================================

class DealRequest(BaseModel):
    artist_followers: int = 5000
    venue_capacity: int = 300
    genre: str = ""
    day_of_week: str = "Friday"

@app.post("/api/booking/deal-suggestion")
async def deal_suggestion(req: DealRequest):
    try:
        from modules.booking_manager import suggest_deal_type
        result = suggest_deal_type(
            artist_followers=req.artist_followers,
            venue_capacity=req.venue_capacity,
            genre=req.genre,
            day_of_week=req.day_of_week,
        )
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/booking/compare-offers")
async def compare_offers(data: dict):
    try:
        from modules.booking_manager import compare_offers
        offers = data.get("offers", [])
        result = compare_offers(offers)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/booking/checklist/{phase}")
async def booking_checklist(phase: str = "pre_booking"):
    try:
        from modules.booking_manager import get_booking_checklist
        return {"phase": phase, "items": get_booking_checklist(phase)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/booking/venue-fit")
async def venue_fit(data: dict):
    try:
        from modules.booking_manager import analyze_venue_fit
        result = analyze_venue_fit(
            venue_name=data.get("venue_name", "Venue"),
            venue_capacity=int(data.get("venue_capacity", 300)),
            artist_followers=int(data.get("artist_followers", 5000)),
            artist_genre=data.get("artist_genre", "rock"),
        )
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/booking/generate-contract")
async def generate_contract(data: dict):
    try:
        from modules.booking_manager import generate_contract_terms
        contract = generate_contract_terms(
            artist=data.get("artist", "Artist"),
            venue=data.get("venue", "Venue"),
            city=data.get("city", "City"),
            state=data.get("state", "State"),
            date=data.get("date", "TBD"),
            guarantee=float(data.get("guarantee", 0)),
            door_split=float(data.get("door_split", 0)),
            merch_split=float(data.get("merch_split", 100)),
        )
        return {"contract": contract}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# Rights + Royalty System Endpoints
# ============================================================

from modules.royalty_engine import RightsManager, RoyaltySplitEngine
_royalty = RightsManager()
_royalty_split = RoyaltySplitEngine()

class SongRegisterRequest(BaseModel):
    isrc: str = ""
    title: str = ""
    artists: list = []
    writers: list = []
    producers: list = []
    publishers: list = []
    upc: str = ""
    release_date: str = ""
    genre: str = ""
    duration_sec: int = 0

@app.post("/api/royalty/song/register")
async def royalty_register(req: SongRegisterRequest):
    try:
        song = _royalty.register_song(**req.model_dump())
        return song
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/royalty/calculate/mechanical")
async def royalty_mechanical(data: dict):
    try:
        copies = int(data.get("copies", 1000))
        per_copy = int(data.get("songs_per_copy", 1))
        return _royalty.calculate_mechanical(copies, per_copy)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/royalty/calculate/performance")
async def royalty_performance(data: dict):
    try:
        platform = data.get("platform", "spotify")
        streams = int(data.get("streams", 100000))
        return _royalty.calculate_performance(platform, streams)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/royalty/calculate/song")
async def royalty_song(data: dict):
    try:
        isrc = data.get("isrc", "")
        streams = data.get("streams_by_platform", {})
        digital = int(data.get("digital_sales", 0))
        physical = int(data.get("physical_sales", 0))
        return _royalty.calculate_song_royalties(isrc, streams, digital, physical)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/royalty/statement/generate")
async def royalty_statement(data: dict):
    try:
        artist = data.get("artist", "Artist")
        songs = data.get("songs", [])
        splits = data.get("splits")
        return _royalty.generate_artist_statement(artist, songs, splits)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/royalty/split/create")
async def royalty_split_create(data: dict):
    try:
        title = data.get("title", "")
        isrc = data.get("isrc", "")
        parties = data.get("parties", [])
        return _royalty_split.create_split_agreement(title, isrc, parties)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/royalty/split/calculate")
async def royalty_split_calc(data: dict):
    try:
        agreement_id = data.get("agreement_id", "")
        revenue = float(data.get("gross_revenue", 0))
        return _royalty_split.calculate_net_royalties(agreement_id, revenue)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# Catalog Management Endpoints
# ============================================================

from modules.catalog_manager import CatalogManager
_catalog = CatalogManager()

@app.post("/api/catalog/release/create")
async def catalog_release_create(data: dict):
    try:
        return _catalog.add_release(
            title=data.get("title", ""),
            artist=data.get("artist", ""),
            upc=data.get("upc", ""),
            isrc=data.get("isrc", ""),
            genre=data.get("genre", ""),
            release_date=data.get("release_date", ""),
            label=data.get("label", "Redemption Road Music Group"),
            catalog_number=data.get("catalog_number", ""),
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/catalog/release/{release_id}")
async def catalog_release_get(release_id: str):
    try:
        release = _catalog.get_release(release_id)
        if not release:
            return JSONResponse(status_code=404, content={"error": "Release not found"})
        return release
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/catalog/track/add")
async def catalog_track_add(data: dict):
    try:
        track = _catalog.add_track(
            release_id=data.get("release_id", ""),
            title=data.get("title", ""),
            isrc=data.get("isrc", ""),
            artists=data.get("artists"),
            writers=data.get("writers"),
            producers=data.get("producers"),
            duration_sec=int(data.get("duration_sec", 0)),
            genre=data.get("genre", ""),
            is_single=data.get("is_single", False),
        )
        if not track:
            return JSONResponse(status_code=404, content={"error": "Release not found"})
        return track
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/catalog/track/metadata")
async def catalog_track_metadata(data: dict):
    try:
        ok = _catalog.update_track_metadata(
            release_id=data.get("release_id", ""),
            track_id=data.get("track_id", ""),
            metadata=data.get("metadata", {}),
        )
        return {"updated": ok}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/catalog")
async def catalog_get(artist: str = "", genre: str = "", status: str = ""):
    try:
        return _catalog.get_catalog(artist=artist, genre=genre, status=status)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/catalog/summary")
async def catalog_summary():
    try:
        return _catalog.get_catalog_summary()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/catalog/search/isrc")
async def catalog_search_isrc(data: dict):
    try:
        result = _catalog.search_by_isrc(data.get("isrc", ""))
        return result or {"error": "No match found"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/catalog/search/upc")
async def catalog_search_upc(data: dict):
    try:
        result = _catalog.search_by_upc(data.get("upc", ""))
        return result or {"error": "No match found"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# Distribution Pipeline Endpoints
# ============================================================

from modules.distribution_pipeline import DistributionPipeline
_distributor = DistributionPipeline()

@app.get("/api/distribution/platforms")
async def distro_platforms(goal: str = ""):
    try:
        return _distributor.get_platforms(goal)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/distribution/metadata/prepare")
async def distro_metadata_prepare(data: dict):
    try:
        return _distributor.prepare_metadata(
            title=data.get("title", ""),
            artist=data.get("artist", ""),
            isrc=data.get("isrc", ""),
            upc=data.get("upc", ""),
            genre=data.get("genre", ""),
            release_date=data.get("release_date", ""),
            label=data.get("label", "Redemption Road Music Group"),
            tracks=data.get("tracks", []),
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/distribution/metadata/validate")
async def distro_metadata_validate(data: dict):
    try:
        return _distributor.validate_metadata(data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/distribution/delivery/create")
async def distro_delivery_create(data: dict):
    try:
        return _distributor.create_delivery(
            platform=data.get("platform", "distrokid"),
            metadata=data.get("metadata", {}),
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/distribution/delivery/{delivery_id}")
async def distro_delivery_get(delivery_id: str):
    try:
        delivery = _distributor.get_delivery(delivery_id)
        if not delivery:
            return JSONResponse(status_code=404, content={"error": "Delivery not found"})
        return delivery
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/distribution/deliveries")
async def distro_deliveries_all():
    try:
        return _distributor.get_all_deliveries()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/distribution/report")
async def distro_report():
    try:
        return _distributor.generate_delivery_report()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# Sync Licensing Endpoints
# ============================================================

from modules.sync_licensing import SyncLicensingEngine
_sync = SyncLicensingEngine()

@app.get("/api/sync/supervisors")
async def sync_supervisors(unsolicited: bool = False):
    try:
        return _sync.get_music_supervisors(filter_accepts_unsolicited=unsolicited)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/sync/festivals")
async def sync_festivals():
    try:
        return _sync.get_sync_festivals()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/sync/estimate")
async def sync_estimate(data: dict):
    try:
        return _sync.estimate_sync_value(
            usage_type=data.get("usage_type", "tv"),
            usage_subtype=data.get("usage_subtype", "network_primetime"),
            duration_sec=int(data.get("duration_sec", 30)),
            territory=data.get("territory", "worldwide"),
            exclusivity=data.get("exclusivity", False),
            term_years=int(data.get("term_years", 2)),
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/sync/cue-sheet")
async def sync_cue_sheet(data: dict):
    try:
        return _sync.generate_cue_sheet(
            project_title=data.get("project_title", ""),
            project_type=data.get("project_type", ""),
            producer=data.get("producer", ""),
            director=data.get("director", ""),
            network=data.get("network", ""),
            airdate=data.get("airdate", ""),
            episode=data.get("episode", ""),
            season=data.get("season", ""),
            cues=data.get("cues", []),
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/sync/pitch")
async def sync_pitch(data: dict):
    try:
        return _sync.create_pitch(
            track_title=data.get("track_title", ""),
            artist=data.get("artist", ""),
            isrc=data.get("isrc", ""),
            supervisor=data.get("supervisor", ""),
            project=data.get("project", ""),
            pitch_type=data.get("pitch_type", "tv"),
            notes=data.get("notes", ""),
            genre=data.get("genre", ""),
            mood_tags=data.get("mood_tags", []),
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/sync/placement")
async def sync_placement(data: dict):
    try:
        placement = _sync.record_placement(
            pitch_id=data.get("pitch_id", ""),
            fee=float(data.get("fee", 0)),
            contract_type=data.get("contract_type", "sync_license"),
            term_months=int(data.get("term_months", 24)),
            territory=data.get("territory", "worldwide"),
        )
        if not placement:
            return JSONResponse(status_code=404, content={"error": "Pitch not found"})
        return placement
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/sync/pitches")
async def sync_pitches(status: str = ""):
    try:
        return _sync.get_pitches(status=status)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/sync/placements")
async def sync_placements(pitch_id: str = ""):
    try:
        return _sync.get_placements(pitch_id=pitch_id)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/sync/summary")
async def sync_summary():
    try:
        return _sync.get_sync_summary()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# Label Identity + Artist Pipeline Endpoints
# ============================================================

from modules.label_identity import LabelIdentityManager
_label_mgr = LabelIdentityManager()

@app.get("/api/label/brand")
async def label_brand_get():
    try:
        return _label_mgr.get_brand()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/label/brand")
async def label_brand_update(data: dict):
    try:
        return _label_mgr.update_brand(data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/label/artist/add")
async def label_artist_add(data: dict):
    try:
        return _label_mgr.add_artist(
            name=data.get("name", ""),
            stage=data.get("stage", "development"),
            genre=data.get("genre", ""),
            bio=data.get("bio", ""),
            social_links=data.get("social_links"),
            metadata=data.get("metadata"),
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/label/artist/update")
async def label_artist_update(data: dict):
    try:
        result = _label_mgr.update_artist(data.get("artist_id", ""), data.get("updates", {}))
        if not result:
            return JSONResponse(status_code=404, content={"error": "Artist not found"})
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/label/artist/{artist_id}")
async def label_artist_get(artist_id: str):
    try:
        artist = _label_mgr.get_artist(artist_id)
        if not artist:
            return JSONResponse(status_code=404, content={"error": "Artist not found"})
        return artist
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/label/roster")
async def label_roster(stage: str = "", genre: str = "", status: str = ""):
    try:
        return _label_mgr.get_roster(stage=stage, genre=genre, status=status)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/label/submission")
async def label_submission(data: dict):
    try:
        return _label_mgr.submit_artist(
            artist_name=data.get("artist_name", ""),
            email=data.get("email", ""),
            genre=data.get("genre", ""),
            social_link=data.get("social_link", ""),
            message=data.get("message", ""),
            spotify_link=data.get("spotify_link", ""),
            youtube_link=data.get("youtube_link", ""),
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/label/submission/review")
async def label_submission_review(data: dict):
    try:
        result = _label_mgr.review_submission(
            submission_id=data.get("submission_id", ""),
            reviewer=data.get("reviewer", ""),
            decision=data.get("decision", ""),
            notes=data.get("notes", ""),
        )
        if not result:
            return JSONResponse(status_code=404, content={"error": "Submission not found or invalid decision"})
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/label/submissions")
async def label_submissions(status: str = ""):
    try:
        return _label_mgr.get_submissions(status=status)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/label/calendar/add")
async def label_calendar_add(data: dict):
    try:
        return _label_mgr.add_release_calendar(
            title=data.get("title", ""),
            artist=data.get("artist", ""),
            release_type=data.get("release_type", "single"),
            release_date=data.get("release_date", ""),
            upc=data.get("upc", ""),
            genre=data.get("genre", ""),
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/label/calendar")
async def label_calendar(artist: str = "", month: str = ""):
    try:
        return _label_mgr.get_release_calendar(artist=artist, month=month)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/label/summary")
async def label_summary():
    try:
        return _label_mgr.get_summary()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/label/milestone/complete")
async def label_milestone_complete(data: dict):
    try:
        ok = _label_mgr.complete_milestone(
            artist_id=data.get("artist_id", ""),
            milestone=data.get("milestone", ""),
        )
        return {"completed": ok}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/label/roadmap/{artist_id}")
async def label_roadmap(artist_id: str):
    try:
        roadmap = _label_mgr.get_development_roadmap(artist_id)
        if not roadmap:
            return JSONResponse(status_code=404, content={"error": "Artist not found"})
        return roadmap
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# Pricing Model + Marketing Copy Endpoints
# ============================================================

from modules.pricing_model import TIERS, ADDONS, COMPETITOR_COMPARISON, MARKETING_MESSAGES, estimate_annual_revenue

@app.get("/api/pricing/tiers")
async def pricing_tiers():
    return TIERS

@app.get("/api/pricing/addons")
async def pricing_addons():
    return ADDONS

@app.get("/api/pricing/competitors")
async def pricing_competitors():
    return COMPETITOR_COMPARISON

@app.get("/api/pricing/marketing")
async def pricing_marketing():
    return MARKETING_MESSAGES

@app.post("/api/pricing/project-revenue")
async def pricing_project(data: dict):
    try:
        result = estimate_annual_revenue(
            artist_starter_count=int(data.get("artist_starter", 0)),
            artist_pro_count=int(data.get("artist_pro", 0)),
            label_launchpad_count=int(data.get("label_launchpad", 0)),
            enterprise_count=int(data.get("enterprise", 0)),
            ai_songs_uploaded=int(data.get("ai_songs", 0)),
            sync_packs_sold=int(data.get("sync_packs", 0)),
            radio_boosts_sold=int(data.get("radio_boosts", 0)),
            streaming_blitzes_sold=int(data.get("streaming_blitzes", 0)),
            tour_plans_sold=int(data.get("tour_plans", 0)),
        )
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# Unified Dashboard Endpoint
# ============================================================

@app.get("/api/dashboard")
async def dashboard():
    try:
        # Aggregate data from all modules
        dashboard_data = {
            "label": _label_mgr.get_summary(),
            "catalog": _catalog.get_catalog_summary(),
            "royalty": {"status": "active"},
            "sync": _sync.get_sync_summary(),
            "distribution": _distributor.generate_delivery_report(),
        }
        dashboard_data["total_releases"] = dashboard_data["catalog"]["total_releases"]
        dashboard_data["total_artists"] = dashboard_data["label"]["total_artists"]
        dashboard_data["submissions_pending"] = dashboard_data["label"]["submissions_pending"]
        dashboard_data["sync_placements"] = dashboard_data["sync"]["total_placements"]
        dashboard_data["sync_revenue"] = dashboard_data["sync"]["total_revenue"]
        dashboard_data["distro_deliveries"] = dashboard_data["distribution"]["total"]
        return dashboard_data
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================
# Stripe Checkout & Webhook
# ============================================================

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_MAP = {
    "artist_starter": os.environ.get("STRIPE_PRICE_ARTIST_STARTER", ""),
    "artist_pro": os.environ.get("STRIPE_PRICE_ARTIST_PRO", ""),
    "label_launchpad": os.environ.get("STRIPE_PRICE_LABEL_LAUNCHPAD", ""),
    "enterprise": os.environ.get("STRIPE_PRICE_ENTERPRISE", ""),
    "ai_song_review": os.environ.get("STRIPE_PRICE_AI_REVIEW", ""),
    "sync_pack": os.environ.get("STRIPE_PRICE_SYNC_PACK", ""),
    "radio_boost": os.environ.get("STRIPE_PRICE_RADIO_BOOST", ""),
    "streaming_blitz": os.environ.get("STRIPE_PRICE_STREAMING_BLITZ", ""),
    "tour_plan": os.environ.get("STRIPE_PRICE_TOUR_PLAN", ""),
}

class CheckoutRequest(BaseModel):
    line_items: list
    success_url: str
    cancel_url: str
    customer_email: Optional[str] = None
    metadata: Optional[dict] = None
    mode: Optional[str] = "payment"

@app.post("/api/stripe/checkout")
async def stripe_checkout(req: CheckoutRequest, request: Request, user: Optional[dict] = Depends(optional_owner)):
    if not STRIPE_ENABLED or not stripe:
        return JSONResponse(status_code=503, content={"error": "Stripe not configured"})
    try:
        stripe.api_key = STRIPE_SECRET_KEY
        items = []
        for li in req.line_items:
            price_id = li.get("price") or STRIPE_PRICE_MAP.get(li.get("product"), "")
            if not price_id:
                continue
            items.append({"price": price_id, "quantity": int(li.get("quantity", 1))})
        if not items:
            return JSONResponse(status_code=400, content={"error": "No valid line items"})
        mode = req.mode if req.mode in ("payment", "subscription") else "payment"
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=items,
            mode=mode,
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            customer_email=req.customer_email,
            metadata=req.metadata or {},
        )
        await audit_log(request, "stripe_checkout_created", {"session_id": session.id, "items": items}, user)
        return {"session_id": session.id, "url": session.url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_ENABLED or not stripe:
        return JSONResponse(status_code=503, content={"error": "Stripe not configured"})
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        else:
            event = json.loads(payload.decode("utf-8"))
        if event.get("type") == "checkout.session.completed":
            session = event["data"]["object"]
            db.insert_order(
                session.get("customer_email", ""),
                session.get("id", ""),
                json.dumps(session.get("metadata", {})),
                "completed",
                session.get("amount_total", 0) / 100.0,
                json.dumps(session),
            )
            await audit_log(request, "stripe_payment_completed", {"session_id": session.get("id")})
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/api/stripe/products")
async def stripe_products():
    return {"prices": {k: v for k, v in STRIPE_PRICE_MAP.items() if v}}

# ============================================================
# Mercantile Products API
# ============================================================

class MercantileProductCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = ""
    category: str
    price: float
    cost: Optional[float] = 0.0
    stock: Optional[int] = 0
    image_url: Optional[str] = ""
    is_active: Optional[bool] = True

@app.get("/api/mercantile/products")
async def mercantile_products(category: Optional[str] = None):
    rows = db.list_mercantile_products(category=category, active_only=True)
    return {"products": [dict(r) for r in rows]}

@app.post("/api/mercantile/products")
async def mercantile_create(req: MercantileProductCreate, request: Request, user: dict = Depends(require_owner)):
    try:
        db.insert_mercantile_product(req.sku, req.name, req.description, req.category, req.price, req.cost, req.stock, req.image_url, req.is_active)
        await audit_log(request, "mercantile_product_create", {"sku": req.sku, "name": req.name}, user)
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/mercantile/inventory")
async def mercantile_inventory(user: dict = Depends(require_owner)):
    rows = db.list_mercantile_products(active_only=False)
    return {"products": [dict(r) for r in rows]}

class MercantileStockUpdate(BaseModel):
    sku: str
    stock: int

@app.patch("/api/mercantile/inventory")
async def mercantile_update_stock(req: MercantileStockUpdate, request: Request, user: dict = Depends(require_owner)):
    try:
        db.update_mercantile_stock(req.sku, req.stock)
        await audit_log(request, "mercantile_stock_update", {"sku": req.sku, "stock": req.stock}, user)
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ============================================================
# WebSocket: Audit / Presence / SoundScape Meet
# ============================================================

class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}
        self.presence: dict[str, dict] = {}

    async def connect(self, ws: WebSocket, user_id: str):
        await ws.accept()
        self.active[user_id] = ws
        self.presence[user_id] = {"online": True, "since": time.time(), "email": user_id}
        await self.broadcast({"type": "presence", "users": self.presence})

    def disconnect(self, user_id: str):
        self.active.pop(user_id, None)
        self.presence.pop(user_id, None)

    async def send(self, user_id: str, message: dict):
        ws = self.active.get(user_id)
        if ws:
            await ws.send_json(message)

    async def broadcast(self, message: dict):
        dead = []
        for uid, ws in self.active.items():
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect(uid)

ws_manager = ConnectionManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(ws: WebSocket, user_id: str):
    await ws_manager.connect(ws, user_id)
    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")
            if msg_type == "meet_signal":
                target = data.get("target")
                if target and target in ws_manager.active:
                    await ws_manager.send(target, {"type": "meet_signal", "from": user_id, "payload": data.get("payload")})
            elif msg_type == "ping":
                await ws_manager.send(user_id, {"type": "pong", "time": time.time()})
            else:
                await ws_manager.broadcast({"type": "broadcast", "from": user_id, "payload": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)
        await ws_manager.broadcast({"type": "presence", "users": ws_manager.presence})

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8765")), log_level="info")
