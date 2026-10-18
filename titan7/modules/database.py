import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

try:
    import psycopg2
    from psycopg2.pool import SimpleConnectionPool
    from psycopg2.extras import RealDictCursor
    HAS_PG = True
except ImportError:
    HAS_PG = False

DB_DIR = os.environ.get("TITAN7_DATA_DIR", os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TITAN7"))
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "titan7.db")

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_PG = HAS_PG and DATABASE_URL and DATABASE_URL.startswith(("postgres://", "postgresql://"))

_pg_pool = None

def _get_pg_pool():
    global _pg_pool
    if _pg_pool is None and USE_PG:
        _pg_pool = SimpleConnectionPool(1, 10, DATABASE_URL)
    return _pg_pool

@contextmanager
def get_connection():
    if USE_PG:
        pool = _get_pg_pool()
        conn = pool.getconn()
        try:
            yield conn
        finally:
            pool.putconn(conn)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

def _execute(cur, query, params=None):
    if USE_PG:
        cur.execute(query, params)
    else:
        cur.execute(query, params or ())

def _init_tables(cur):
    # Radio stations discovered
    _execute(cur, """
        CREATE TABLE IF NOT EXISTS radio_targets (
            id SERIAL PRIMARY KEY,
            genre TEXT NOT NULL,
            state TEXT DEFAULT '',
            station_name TEXT NOT NULL,
            vector TEXT NOT NULL,
            location TEXT,
            frequency TEXT,
            contact TEXT,
            match_score REAL,
            contacted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Venues for booking
    _execute(cur, """
        CREATE TABLE IF NOT EXISTS venues (
            id SERIAL PRIMARY KEY,
            state TEXT NOT NULL,
            name TEXT NOT NULL,
            city TEXT,
            capacity INTEGER,
            contact TEXT,
            website TEXT,
            status TEXT DEFAULT 'identified',
            epk_sent INTEGER DEFAULT 0,
            contract_sent INTEGER DEFAULT 0,
            booked INTEGER DEFAULT 0,
            follow_up_count INTEGER DEFAULT 0,
            next_follow_up TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Media outlets for PR
    _execute(cur, """
        CREATE TABLE IF NOT EXISTS media_outlets (
            id SERIAL PRIMARY KEY,
            topic TEXT NOT NULL,
            name TEXT NOT NULL,
            tier TEXT,
            contact TEXT,
            website TEXT,
            pr_sent INTEGER DEFAULT 0,
            opened INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Emails dispatched
    _execute(cur, """
        CREATE TABLE IF NOT EXISTS emails_sent (
            id SERIAL PRIMARY KEY,
            module TEXT NOT NULL,
            owner_email TEXT NOT NULL,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT,
            status TEXT DEFAULT 'queued',
            sent_at TIMESTAMP,
            error TEXT,
            tracking_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Master autopilot DAG tasks
    _execute(cur, """
        CREATE TABLE IF NOT EXISTS autopilot_tasks (
            id SERIAL PRIMARY KEY,
            task_type TEXT NOT NULL,
            current_state TEXT DEFAULT 'pending',
            payload TEXT,
            next_action_time TEXT,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Radio station library
    _execute(cur, """
        CREATE TABLE IF NOT EXISTS radio_library (
            id SERIAL PRIMARY KEY,
            genre TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT '',
            station_name TEXT NOT NULL,
            vector TEXT NOT NULL DEFAULT '',
            location TEXT DEFAULT '',
            frequency TEXT DEFAULT '',
            format TEXT DEFAULT '',
            contact TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            pastor TEXT DEFAULT '',
            website TEXT DEFAULT '',
            match_score REAL DEFAULT 50.0,
            source TEXT DEFAULT 'curated',
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(genre, state, station_name)
        )
    """)

    # Venue library
    _execute(cur, """
        CREATE TABLE IF NOT EXISTS venue_library (
            id SERIAL PRIMARY KEY,
            genre TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            city TEXT DEFAULT '',
            capacity INTEGER DEFAULT 0,
            contact TEXT DEFAULT '',
            website TEXT DEFAULT '',
            source TEXT DEFAULT 'curated',
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(genre, state, name)
        )
    """)

    # Media outlet library
    _execute(cur, """
        CREATE TABLE IF NOT EXISTS media_library (
            id SERIAL PRIMARY KEY,
            topic TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            tier TEXT DEFAULT '',
            contact TEXT DEFAULT '',
            website TEXT DEFAULT '',
            source TEXT DEFAULT 'curated',
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(topic, state, name)
        )
    """)

    _execute(cur, """
        CREATE TABLE IF NOT EXISTS search_history (
            id SERIAL PRIMARY KEY,
            module TEXT NOT NULL,
            query TEXT NOT NULL,
            state TEXT DEFAULT '',
            results_count INTEGER DEFAULT 0,
            contacts_found INTEGER DEFAULT 0,
            success INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    _execute(cur, """
        CREATE TABLE IF NOT EXISTS learning_stats (
            id SERIAL PRIMARY KEY,
            module TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(module, key)
        )
    """)

    _execute(cur, """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    _execute(cur, """
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            action TEXT NOT NULL,
            user_email TEXT,
            detail TEXT DEFAULT '{}',
            meta TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    _execute(cur, """
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            customer_email TEXT NOT NULL,
            stripe_session_id TEXT,
            metadata TEXT DEFAULT '{}',
            status TEXT DEFAULT 'pending',
            amount REAL DEFAULT 0,
            raw_session TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    _execute(cur, """
        CREATE TABLE IF NOT EXISTS mercantile_products (
            id SERIAL PRIMARY KEY,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT NOT NULL,
            price REAL NOT NULL,
            cost REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            image_url TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def init_db():
    with get_connection() as conn:
        cur = conn.cursor()
        _init_tables(cur)
        conn.commit()

# Initialize on import
init_db()

# ============================================================
# Original TITAN 7 database functions
# ============================================================

def insert_radio_target(data: Dict[str, Any]) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("""
                INSERT INTO radio_targets (genre, state, station_name, vector, location, frequency, contact, match_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (data.get("genre"), data.get("state", ""), data.get("station_name"), data.get("vector"),
                  data.get("location"), data.get("frequency"), data.get("contact"),
                  data.get("match_score", 0.0)))
        else:
            cur.execute("""
                INSERT INTO radio_targets (genre, state, station_name, vector, location, frequency, contact, match_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (data.get("genre"), data.get("state", ""), data.get("station_name"), data.get("vector"),
                  data.get("location"), data.get("frequency"), data.get("contact"),
                  data.get("match_score", 0.0)))
        conn.commit()
        return cur.lastrowid if not USE_PG else cur.fetchone()[0] if USE_PG else cur.lastrowid

def get_radio_targets(genre: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        if genre:
            cur.execute("SELECT * FROM radio_targets WHERE genre = ? ORDER BY match_score DESC", (genre,))
        else:
            cur.execute("SELECT * FROM radio_targets ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]

def insert_venue(data: Dict[str, Any]) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("""
                INSERT INTO venues (state, name, city, capacity, contact, website)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (data.get("state"), data.get("name"), data.get("city"),
                  data.get("capacity"), data.get("contact"), data.get("website")))
        else:
            cur.execute("""
                INSERT INTO venues (state, name, city, capacity, contact, website)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (data.get("state"), data.get("name"), data.get("city"),
                  data.get("capacity"), data.get("contact"), data.get("website")))
        conn.commit()
        return cur.lastrowid

def get_venues(state: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        if state:
            cur.execute("SELECT * FROM venues WHERE state = ? ORDER BY created_at DESC", (state,))
        else:
            cur.execute("SELECT * FROM venues ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]

def update_venue(venue_id: int, updates: Dict[str, Any]):
    with get_connection() as conn:
        cur = conn.cursor()
        fields = ", ".join([f"{k} = ?" for k in updates.keys()])
        cur.execute(f"UPDATE venues SET {fields} WHERE id = ?", (*updates.values(), venue_id))
        conn.commit()

def insert_media_outlet(data: Dict[str, Any]) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("""
                INSERT INTO media_outlets (topic, name, tier, contact, website)
                VALUES (%s, %s, %s, %s, %s)
            """, (data.get("topic"), data.get("name"), data.get("tier"),
                  data.get("contact"), data.get("website")))
        else:
            cur.execute("""
                INSERT INTO media_outlets (topic, name, tier, contact, website)
                VALUES (?, ?, ?, ?, ?)
            """, (data.get("topic"), data.get("name"), data.get("tier"),
                  data.get("contact"), data.get("website")))
        conn.commit()
        return cur.lastrowid

def get_media_outlets(topic: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        if topic:
            cur.execute("SELECT * FROM media_outlets WHERE topic = ? ORDER BY created_at DESC", (topic,))
        else:
            cur.execute("SELECT * FROM media_outlets ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]

def log_email(module: str, owner_email: str, recipient: str, subject: str, body: str,
              status: str = "queued", error: str = None, tracking_id: str = None) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("""
                INSERT INTO emails_sent (module, owner_email, recipient, subject, body, status, error, tracking_id, sent_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (module, owner_email, recipient, subject, body, status, error, tracking_id,
                  datetime.utcnow().isoformat() if status == "sent" else None))
        else:
            cur.execute("""
                INSERT INTO emails_sent (module, owner_email, recipient, subject, body, status, error, tracking_id, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (module, owner_email, recipient, subject, body, status, error, tracking_id,
                  datetime.utcnow().isoformat() if status == "sent" else None))
        conn.commit()
        return cur.lastrowid

def get_emails(module: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        if module:
            cur.execute("SELECT * FROM emails_sent WHERE module = ? ORDER BY created_at DESC", (module,))
        else:
            cur.execute("SELECT * FROM emails_sent ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]

def log_search(module: str, query: str, state: str, results_count: int, contacts_found: int, success: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("""
                INSERT INTO search_history (module, query, state, results_count, contacts_found, success)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (module, query, state, results_count, contacts_found, success))
        else:
            cur.execute("""
                INSERT INTO search_history (module, query, state, results_count, contacts_found, success)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (module, query, state, results_count, contacts_found, success))
        conn.commit()
        return cur.lastrowid

def update_learning_stat(module: str, key: str, value: str, weight_delta: float = 0.0):
    with get_connection() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("""
                INSERT INTO learning_stats (module, key, value, weight)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(module, key) DO UPDATE SET
                    value = EXCLUDED.value,
                    weight = GREATEST(0.1, learning_stats.weight + EXCLUDED.weight)
            """, (module, key, value, weight_delta))
        else:
            cur.execute("""
                INSERT INTO learning_stats (module, key, value, weight)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(module, key) DO UPDATE SET
                    value = excluded.value,
                    weight = MAX(0.1, learning_stats.weight + excluded.weight)
            """, (module, key, value, weight_delta))
        conn.commit()

def get_learning_stat(module: str, key: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM learning_stats WHERE module = ? AND key = ?", (module, key))
        row = cur.fetchone()
        return dict(row) if row else None

def get_top_queries(module: str, limit: int = 20) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("""
            SELECT query, state, COUNT(*) as attempts, SUM(success) as successes,
                   SUM(contacts_found) as total_contacts, AVG(results_count) as avg_results
            FROM search_history
            WHERE module = ?
            GROUP BY query, state
            ORDER BY successes DESC, total_contacts DESC
            LIMIT ?
        """, (module, limit))
        return [dict(r) for r in cur.fetchall()]

def create_autopilot_task(task_type: str, payload: Dict[str, Any], next_action: Optional[str] = None) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("""
                INSERT INTO autopilot_tasks (task_type, current_state, payload, next_action_time)
                VALUES (%s, %s, %s, %s)
            """, (task_type, "pending", str(payload), next_action))
        else:
            cur.execute("""
                INSERT INTO autopilot_tasks (task_type, current_state, payload, next_action_time)
                VALUES (?, ?, ?, ?)
            """, (task_type, "pending", str(payload), next_action))
        conn.commit()
        return cur.lastrowid

def save_setting(key: str, value: str):
    with get_connection() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value", (key, value))
        else:
            cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()

def get_setting(key: str) -> Optional[str]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else None

def save_to_radio_library(stations: List[Dict[str, Any]], genre: str = "", state: str = "") -> int:
    saved = 0
    with get_connection() as conn:
        cur = conn.cursor()
        for s in stations:
            try:
                if USE_PG:
                    cur.execute("""
                        INSERT INTO radio_library (genre, state, station_name, vector, location, frequency, format, contact, website, match_score, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(genre, state, station_name) DO UPDATE SET
                            last_seen = CURRENT_TIMESTAMP,
                            match_score = GREATEST(EXCLUDED.match_score, radio_library.match_score),
                            contact = CASE WHEN EXCLUDED.contact != '' THEN EXCLUDED.contact ELSE radio_library.contact END,
                            website = CASE WHEN EXCLUDED.website != '' THEN EXCLUDED.website ELSE radio_library.website END
                    """, (genre or s.get("genre", ""), state or s.get("state", ""),
                          s.get("station_name", ""), s.get("vector", ""),
                          s.get("location", ""), s.get("frequency", ""),
                          s.get("format", ""), s.get("contact", ""),
                          s.get("website", ""), s.get("match_score", 50.0),
                          s.get("source", "discovered")))
                else:
                    cur.execute("""
                        INSERT INTO radio_library (genre, state, station_name, vector, location, frequency, format, contact, website, match_score, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(genre, state, station_name) DO UPDATE SET
                            last_seen = CURRENT_TIMESTAMP,
                            match_score = MAX(excluded.match_score, radio_library.match_score),
                            contact = CASE WHEN excluded.contact != '' THEN excluded.contact ELSE radio_library.contact END,
                            website = CASE WHEN excluded.website != '' THEN excluded.website ELSE radio_library.website END
                    """, (genre or s.get("genre", ""), state or s.get("state", ""),
                          s.get("station_name", ""), s.get("vector", ""),
                          s.get("location", ""), s.get("frequency", ""),
                          s.get("format", ""), s.get("contact", ""),
                          s.get("website", ""), s.get("match_score", 50.0),
                          s.get("source", "discovered")))
                saved += 1
            except Exception:
                pass
        conn.commit()
    return saved

def get_radio_library(genre: str = "", state: str = "") -> List[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        q = "SELECT * FROM radio_library WHERE 1=1"
        params = []
        if genre:
            q += " AND genre = ?"
            params.append(genre)
        if state:
            q += " AND state = ?"
            params.append(state)
        q += " ORDER BY match_score DESC, id DESC"
        cur.execute(q, params)
        return [dict(r) for r in cur.fetchall()]

def save_to_venue_library(venues: List[Dict[str, Any]], genre: str = "", state: str = "") -> int:
    saved = 0
    with get_connection() as conn:
        cur = conn.cursor()
        for v in venues:
            try:
                if USE_PG:
                    cur.execute("""
                        INSERT INTO venue_library (genre, state, name, city, capacity, contact, website, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(genre, state, name) DO UPDATE SET
                            last_seen = CURRENT_TIMESTAMP,
                            capacity = GREATEST(EXCLUDED.capacity, venue_library.capacity),
                            contact = CASE WHEN EXCLUDED.contact != '' THEN EXCLUDED.contact ELSE venue_library.contact END,
                            website = CASE WHEN EXCLUDED.website != '' THEN EXCLUDED.website ELSE venue_library.website END
                    """, (genre or v.get("genre", ""), state or v.get("state", ""),
                          v.get("name", ""), v.get("city", ""),
                          v.get("capacity", 0), v.get("contact", ""),
                          v.get("website", ""), v.get("source", "discovered")))
                else:
                    cur.execute("""
                        INSERT INTO venue_library (genre, state, name, city, capacity, contact, website, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(genre, state, name) DO UPDATE SET
                            last_seen = CURRENT_TIMESTAMP,
                            capacity = MAX(excluded.capacity, venue_library.capacity),
                            contact = CASE WHEN excluded.contact != '' THEN excluded.contact ELSE venue_library.contact END,
                            website = CASE WHEN excluded.website != '' THEN excluded.website ELSE venue_library.website END
                    """, (genre or v.get("genre", ""), state or v.get("state", ""),
                          v.get("name", ""), v.get("city", ""),
                          v.get("capacity", 0), v.get("contact", ""),
                          v.get("website", ""), v.get("source", "discovered")))
                saved += 1
            except Exception:
                pass
        conn.commit()
    return saved

def get_venue_library(genre: str = "", state: str = "") -> List[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        q = "SELECT * FROM venue_library WHERE 1=1"
        params = []
        if genre:
            q += " AND genre = ?"
            params.append(genre)
        if state:
            q += " AND state = ?"
            params.append(state)
        q += " ORDER BY capacity DESC"
        cur.execute(q, params)
        return [dict(r) for r in cur.fetchall()]

def save_to_media_library(outlets: List[Dict[str, Any]], topic: str = "", state: str = "") -> int:
    saved = 0
    with get_connection() as conn:
        cur = conn.cursor()
        for o in outlets:
            try:
                if USE_PG:
                    cur.execute("""
                        INSERT INTO media_library (topic, state, name, tier, contact, website, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(topic, state, name) DO UPDATE SET
                            last_seen = CURRENT_TIMESTAMP,
                            contact = CASE WHEN EXCLUDED.contact != '' THEN EXCLUDED.contact ELSE media_library.contact END
                    """, (topic or o.get("topic", ""), state or o.get("state", ""),
                          o.get("name", ""), o.get("tier", ""),
                          o.get("contact", ""), o.get("website", ""),
                          o.get("source", "discovered")))
                else:
                    cur.execute("""
                        INSERT INTO media_library (topic, state, name, tier, contact, website, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(topic, state, name) DO UPDATE SET
                            last_seen = CURRENT_TIMESTAMP,
                            contact = CASE WHEN excluded.contact != '' THEN excluded.contact ELSE media_library.contact END
                    """, (topic or o.get("topic", ""), state or o.get("state", ""),
                          o.get("name", ""), o.get("tier", ""),
                          o.get("contact", ""), o.get("website", ""),
                          o.get("source", "discovered")))
                saved += 1
            except Exception:
                pass
        conn.commit()
    return saved

def get_media_library(topic: str = "", state: str = "") -> List[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        q = "SELECT * FROM media_library WHERE 1=1"
        params = []
        if topic:
            q += " AND topic = ?"
            params.append(topic)
        if state:
            q += " AND state = ?"
            params.append(state)
        q += " ORDER BY tier"
        cur.execute(q, params)
        return [dict(r) for r in cur.fetchall()]

def seed_churches(churches: List[Dict[str, Any]]):
    with get_connection() as conn:
        cur = conn.cursor()
        count = 0
        for c in churches:
            try:
                genre = c.get("genre", "christian").lower().replace(" ", "_")
                state = c.get("state", "Texas")
                if USE_PG:
                    cur.execute("""
                        INSERT INTO venue_library (genre, state, name, city, capacity, contact, website, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(genre, state, name) DO UPDATE SET
                            last_seen = CURRENT_TIMESTAMP,
                            contact = CASE WHEN EXCLUDED.contact != '' THEN EXCLUDED.contact ELSE venue_library.contact END,
                            website = CASE WHEN EXCLUDED.website != '' THEN EXCLUDED.website ELSE venue_library.website END
                    """, (genre, state,
                          c.get("name", ""), c.get("city", ""),
                          c.get("capacity", 0), c.get("contact", ""),
                          c.get("website", ""), "church_seed"))
                else:
                    cur.execute("""
                        INSERT INTO venue_library (genre, state, name, city, capacity, contact, website, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(genre, state, name) DO UPDATE SET
                            last_seen = CURRENT_TIMESTAMP,
                            contact = CASE WHEN excluded.contact != '' THEN excluded.contact ELSE venue_library.contact END,
                            website = CASE WHEN excluded.website != '' THEN excluded.website ELSE venue_library.website END
                    """, (genre, state,
                          c.get("name", ""), c.get("city", ""),
                          c.get("capacity", 0), c.get("contact", ""),
                          c.get("website", ""), "church_seed"))
                count += 1
            except Exception:
                pass
        conn.commit()
        return count

def import_churches_csv(csv_path: str) -> int:
    import csv
    count = 0
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            batch.append({
                "name": row.get("name", "").strip(),
                "genre": row.get("genre", "christian").strip(),
                "state": row.get("state", "Texas").strip(),
                "city": row.get("city", "").strip(),
                "contact": row.get("contact", "").strip(),
                "website": row.get("website", "").strip(),
                "county": row.get("county", "").strip(),
            })
        count = seed_churches(batch)
    return count

def save_epk(data: Dict[str, Any]) -> int:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT id FROM epk LIMIT 1")
        existing = cur.fetchone()
        fields = ["artist", "genre", "bio", "spotify", "soundcloud", "apple_music",
                   "youtube", "press_quotes", "photo_url", "website", "instagram",
                   "facebook", "twitter", "contact_email", "phone"]
        if existing:
            sets = ", ".join([f"{f} = ?" for f in fields])
            sets += ", updated_at = CURRENT_TIMESTAMP"
            vals = [data.get(f, "") for f in fields] + [existing["id"]]
            cur.execute(f"UPDATE epk SET {sets} WHERE id = ?", vals)
            return existing["id"]
        else:
            cols = ", ".join(fields)
            placeholders = ", ".join(["?" for _ in fields])
            vals = [data.get(f, "") for f in fields]
            cur.execute(f"INSERT INTO epk ({cols}) VALUES ({placeholders})", vals)
            conn.commit()
            return cur.lastrowid

def get_epk() -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM epk LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else None

def save_selected_stations(stations: List[Dict[str, Any]]):
    with get_connection() as conn:
        cur = conn.cursor()
        for s in stations:
            try:
                if USE_PG:
                    cur.execute("""
                        INSERT INTO radio_selected
                        (station_name, vector, location, frequency, contact, website,
                         match_score, genre, state, submission_method, submission_email, submission_notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(station_name) DO UPDATE SET
                            vector = EXCLUDED.vector,
                            location = EXCLUDED.location,
                            frequency = EXCLUDED.frequency,
                            contact = EXCLUDED.contact,
                            website = EXCLUDED.website,
                            match_score = EXCLUDED.match_score,
                            genre = EXCLUDED.genre,
                            state = EXCLUDED.state,
                            submission_method = EXCLUDED.submission_method,
                            submission_email = EXCLUDED.submission_email,
                            submission_notes = EXCLUDED.submission_notes,
                            selected_at = CURRENT_TIMESTAMP
                    """, (
                        s.get("station_name", "") or s.get("name", ""),
                        s.get("vector", ""), s.get("location", ""),
                        s.get("frequency", ""), s.get("contact", ""),
                        s.get("website", ""), s.get("match_score", 0),
                        s.get("genre", ""), s.get("state", ""),
                        s.get("submission_method", ""),
                        s.get("submission_email", ""),
                        s.get("submission_notes", "")
                    ))
                else:
                    cur.execute("""
                        INSERT OR REPLACE INTO radio_selected
                        (station_name, vector, location, frequency, contact, website,
                         match_score, genre, state, submission_method, submission_email, submission_notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        s.get("station_name", "") or s.get("name", ""),
                        s.get("vector", ""), s.get("location", ""),
                        s.get("frequency", ""), s.get("contact", ""),
                        s.get("website", ""), s.get("match_score", 0),
                        s.get("genre", ""), s.get("state", ""),
                        s.get("submission_method", ""),
                        s.get("submission_email", ""),
                        s.get("submission_notes", "")
                    ))
            except Exception:
                pass
        conn.commit()

def get_selected_stations() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM radio_selected ORDER BY selected_at DESC")
        return [dict(r) for r in cur.fetchall()]

def clear_selected_stations():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM radio_selected")
        conn.commit()

def remove_selected_station(station_name: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM radio_selected WHERE station_name = ?", (station_name,))
        conn.commit()

# ============================================================
# Royalty Engine persistence
# ============================================================

def save_royalty_song(song: dict) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_PG:
                cur.execute("""
                    INSERT INTO royalty_songs
                    (id, isrc, upc, title, artists, writers, producers, publishers,
                     release_date, genre, duration_sec, registered, streams, sales, sync_income)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    song["id"], song["isrc"], song.get("upc", ""), song["title"],
                    json.dumps(song.get("artists", [])), json.dumps(song.get("writers", [])),
                    json.dumps(song.get("producers", [])), json.dumps(song.get("publishers", [])),
                    song.get("release_date", ""), song.get("genre", ""), song.get("duration_sec", 0),
                    song.get("registered", ""), json.dumps(song.get("streams", {})),
                    song.get("sales", 0), song.get("sync_income", 0.0)
                ))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO royalty_songs
                    (id, isrc, upc, title, artists, writers, producers, publishers,
                     release_date, genre, duration_sec, registered, streams, sales, sync_income)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    song["id"], song["isrc"], song.get("upc", ""), song["title"],
                    json.dumps(song.get("artists", [])), json.dumps(song.get("writers", [])),
                    json.dumps(song.get("producers", [])), json.dumps(song.get("publishers", [])),
                    song.get("release_date", ""), song.get("genre", ""), song.get("duration_sec", 0),
                    song.get("registered", ""), json.dumps(song.get("streams", {})),
                    song.get("sales", 0), song.get("sync_income", 0.0)
                ))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving royalty song: {e}")
        return False

def get_royalty_songs() -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM royalty_songs ORDER BY registered DESC")
        rows = cur.fetchall()
        result = []
        for row in rows:
            if USE_PG:
                d = dict(row)
            else:
                d = dict(row)
            for field in ('artists','writers','producers','publishers'):
                try: d[field] = json.loads(d.get(field, '[]'))
                except: d[field] = []
            try: d['streams'] = json.loads(d.get('streams', '{}'))
            except: d['streams'] = {}
            result.append(d)
        return result

def save_royalty_split_agreement(agreement: dict) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_PG:
                cur.execute("""
                    INSERT INTO royalty_split_agreements (id, title, isrc, parties, created)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    agreement["id"], agreement["title"], agreement.get("isrc", ""),
                    json.dumps(agreement.get("parties", [])), agreement.get("created", "")
                ))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO royalty_split_agreements (id, title, isrc, parties, created)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    agreement["id"], agreement["title"], agreement.get("isrc", ""),
                    json.dumps(agreement.get("parties", [])), agreement.get("created", "")
                ))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving royalty split agreement: {e}")
        return False

def get_royalty_split_agreements() -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM royalty_split_agreements ORDER BY created DESC")
        return [dict(r) for r in cur.fetchall()]

# ============================================================
# Catalog Manager persistence
# ============================================================

def save_catalog_release(release: dict) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_PG:
                cur.execute("""
                    INSERT INTO catalog_releases
                    (id, title, artist, upc, isrc, genre, release_date, label, catalog_number,
                     tracks, artwork_url, lyrics, credits, status, created, updated, version_history)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    release["id"], release["title"], release["artist"], release.get("upc",""),
                    release.get("isrc",""), release.get("genre",""), release.get("release_date",""),
                    release.get("label","Redemption Road Music Group"), release.get("catalog_number",""),
                    json.dumps(release.get("tracks", [])), release.get("artwork_url",""),
                    release.get("lyrics",""), release.get("credits",""), release.get("status","draft"),
                    release.get("created",""), release.get("updated",""),
                    json.dumps(release.get("version_history", []))
                ))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO catalog_releases
                    (id, title, artist, upc, isrc, genre, release_date, label, catalog_number,
                     tracks, artwork_url, lyrics, credits, status, created, updated, version_history)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    release["id"], release["title"], release["artist"], release.get("upc",""),
                    release.get("isrc",""), release.get("genre",""), release.get("release_date",""),
                    release.get("label","Redemption Road Music Group"), release.get("catalog_number",""),
                    json.dumps(release.get("tracks", [])), release.get("artwork_url",""),
                    release.get("lyrics",""), release.get("credits",""), release.get("status","draft"),
                    release.get("created",""), release.get("updated",""),
                    json.dumps(release.get("version_history", []))
                ))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving catalog release: {e}")
        return False

def get_catalog_releases() -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM catalog_releases ORDER BY created DESC")
        rows = cur.fetchall()
        result = []
        for row in rows:
            if USE_PG:
                d = dict(row)
            else:
                d = dict(row)
            for field in ('tracks', 'version_history'):
                try: d[field] = json.loads(d.get(field, '[]'))
                except: d[field] = []
            result.append(d)
        return result

def get_catalog_release(release_id: str) -> dict:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM catalog_releases WHERE id = ?", (release_id,))
        row = cur.fetchone()
        if row:
            d = dict(row)
            for field in ('tracks', 'version_history'):
                try: d[field] = json.loads(d.get(field, '[]'))
                except: d[field] = []
            return d
        return None

def delete_catalog_release(release_id: str) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM catalog_releases WHERE id = ?", (release_id,))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error deleting catalog release: {e}")
        return False

# ============================================================
# Distribution Pipeline persistence
# ============================================================

def save_distro_delivery(delivery: dict) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_PG:
                cur.execute("""
                    INSERT INTO distro_deliveries
                    (id, platform, platform_name, status, metadata, created, estimated_delivery, errors)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    delivery["id"], delivery["platform"], delivery.get("platform_name",""),
                    delivery["status"], json.dumps(delivery.get("metadata", {})),
                    delivery.get("created",""), delivery.get("estimated_delivery",""),
                    json.dumps(delivery.get("errors", []))
                ))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO distro_deliveries
                    (id, platform, platform_name, status, metadata, created, estimated_delivery, errors)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    delivery["id"], delivery["platform"], delivery.get("platform_name",""),
                    delivery["status"], json.dumps(delivery.get("metadata", {})),
                    delivery.get("created",""), delivery.get("estimated_delivery",""),
                    json.dumps(delivery.get("errors", []))
                ))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving distro delivery: {e}")
        return False

def get_distro_deliveries() -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM distro_deliveries ORDER BY created DESC")
        rows = cur.fetchall()
        result = []
        for row in rows:
            if USE_PG:
                d = dict(row)
            else:
                d = dict(row)
            try: d['metadata'] = json.loads(d.get('metadata', '{}'))
            except: d['metadata'] = {}
            try: d['errors'] = json.loads(d.get('errors', '[]'))
            except: d['errors'] = []
            result.append(d)
        return result

def get_distro_delivery(delivery_id: str) -> dict:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM distro_deliveries WHERE id = ?", (delivery_id,))
        row = cur.fetchone()
        if row:
            if USE_PG:
                d = dict(row)
            else:
                d = dict(row)
            try: d['metadata'] = json.loads(d.get('metadata', '{}'))
            except: d['metadata'] = {}
            try: d['errors'] = json.loads(d.get('errors', '[]'))
            except: d['errors'] = []
            return d
        return None

# ============================================================
# Sync Licensing persistence
# ============================================================

def save_sync_pitch(pitch: dict) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_PG:
                cur.execute("""
                    INSERT INTO sync_pitches
                    (id, track_title, artist, isrc, supervisor, project, pitch_type,
                     status, notes, genre, mood_tags, created, follow_up_date, response, placed)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    pitch["id"], pitch["track_title"], pitch.get("artist",""),
                    pitch.get("isrc",""), pitch.get("supervisor",""), pitch.get("project",""),
                    pitch.get("pitch_type",""), pitch.get("status","sent"), pitch.get("notes",""),
                    pitch.get("genre",""), json.dumps(pitch.get("mood_tags", [])),
                    pitch.get("created",""), pitch.get("follow_up_date",""),
                    pitch.get("response",""), 1 if pitch.get("placed") else 0
                ))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO sync_pitches
                    (id, track_title, artist, isrc, supervisor, project, pitch_type,
                     status, notes, genre, mood_tags, created, follow_up_date, response, placed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pitch["id"], pitch["track_title"], pitch.get("artist",""),
                    pitch.get("isrc",""), pitch.get("supervisor",""), pitch.get("project",""),
                    pitch.get("pitch_type",""), pitch.get("status","sent"), pitch.get("notes",""),
                    pitch.get("genre",""), json.dumps(pitch.get("mood_tags", [])),
                    pitch.get("created",""), pitch.get("follow_up_date",""),
                    pitch.get("response",""), 1 if pitch.get("placed") else 0
                ))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving sync pitch: {e}")
        return False

def get_sync_pitches() -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM sync_pitches ORDER BY created DESC")
        rows = cur.fetchall()
        result = []
        for row in rows:
            if USE_PG:
                d = dict(row)
            else:
                d = dict(row)
            try: d['mood_tags'] = json.loads(d.get('mood_tags', '[]'))
            except: d['mood_tags'] = []
            d['placed'] = bool(d.get('placed', 0))
            result.append(d)
        return result

def save_sync_placement(placement: dict) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_PG:
                cur.execute("""
                    INSERT INTO sync_placements
                    (id, pitch_id, track_title, artist, isrc, project, supervisor,
                     fee, contract_type, term_months, territory, placed_date, royalty_rate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    placement["id"], placement["pitch_id"], placement.get("track_title",""),
                    placement.get("artist",""), placement.get("isrc",""), placement.get("project",""),
                    placement.get("supervisor",""), placement.get("fee",0.0),
                    placement.get("contract_type","sync_license"), placement.get("term_months",24),
                    placement.get("territory","worldwide"), placement.get("placed_date",""),
                    placement.get("royalty_rate","")
                ))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO sync_placements
                    (id, pitch_id, track_title, artist, isrc, project, supervisor,
                     fee, contract_type, term_months, territory, placed_date, royalty_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    placement["id"], placement["pitch_id"], placement.get("track_title",""),
                    placement.get("artist",""), placement.get("isrc",""), placement.get("project",""),
                    placement.get("supervisor",""), placement.get("fee",0.0),
                    placement.get("contract_type","sync_license"), placement.get("term_months",24),
                    placement.get("territory","worldwide"), placement.get("placed_date",""),
                    placement.get("royalty_rate","")
                ))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving sync placement: {e}")
        return False

def get_sync_placements() -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM sync_placements ORDER BY placed_date DESC")
        return [dict(r) for r in cur.fetchall()]

# ============================================================
# Label Identity + Artist Pipeline persistence
# ============================================================

def save_label_artist(artist: dict) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_PG:
                cur.execute("""
                    INSERT INTO label_roster
                    (id, name, stage, genre, bio, social_links, metadata, joined,
                     next_release_date, milestones_completed, current_milestone, notes, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    artist["id"], artist["name"], artist.get("stage","development"),
                    artist.get("genre",""), artist.get("bio",""),
                    json.dumps(artist.get("social_links", {})),
                    json.dumps(artist.get("metadata", {})), artist.get("joined",""),
                    artist.get("next_release_date",""),
                    json.dumps(artist.get("milestones_completed", [])),
                    artist.get("current_milestone",""), artist.get("notes",""),
                    artist.get("status","active")
                ))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO label_roster
                    (id, name, stage, genre, bio, social_links, metadata, joined,
                     next_release_date, milestones_completed, current_milestone, notes, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    artist["id"], artist["name"], artist.get("stage","development"),
                    artist.get("genre",""), artist.get("bio",""),
                    json.dumps(artist.get("social_links", {})),
                    json.dumps(artist.get("metadata", {})), artist.get("joined",""),
                    artist.get("next_release_date",""),
                    json.dumps(artist.get("milestones_completed", [])),
                    artist.get("current_milestone",""), artist.get("notes",""),
                    artist.get("status","active")
                ))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving label artist: {e}")
        return False

def get_label_roster() -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM label_roster ORDER BY joined DESC")
        rows = cur.fetchall()
        result = []
        for row in rows:
            if USE_PG:
                d = dict(row)
            else:
                d = dict(row)
            for field in ('social_links','metadata','milestones_completed'):
                try: d[field] = json.loads(d.get(field, '{}' if field != 'milestones_completed' else '[]'))
                except: d[field] = {} if field != 'milestones_completed' else []
            result.append(d)
        return result

def get_label_artist(artist_id: str) -> dict:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM label_roster WHERE id = ?", (artist_id,))
        row = cur.fetchone()
        if row:
            if USE_PG:
                d = dict(row)
            else:
                d = dict(row)
            for field in ('social_links','metadata','milestones_completed'):
                try: d[field] = json.loads(d.get(field, '{}' if field != 'milestones_completed' else '[]'))
                except: d[field] = {} if field != 'milestones_completed' else []
            return d
        return None

def delete_label_artist(artist_id: str) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM label_roster WHERE id = ?", (artist_id,))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error deleting label artist: {e}")
        return False

def save_label_submission(sub: dict) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_PG:
                cur.execute("""
                    INSERT INTO label_submissions
                    (id, artist_name, email, genre, social_link, spotify_link, youtube_link,
                     message, status, submitted, reviewed_by, review_notes, decision)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    sub["id"], sub["artist_name"], sub.get("email",""), sub.get("genre",""),
                    sub.get("social_link",""), sub.get("spotify_link",""), sub.get("youtube_link",""),
                    sub.get("message",""), sub.get("status","new"), sub.get("submitted",""),
                    sub.get("reviewed_by",""), sub.get("review_notes",""), sub.get("decision","")
                ))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO label_submissions
                    (id, artist_name, email, genre, social_link, spotify_link, youtube_link,
                     message, status, submitted, reviewed_by, review_notes, decision)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sub["id"], sub["artist_name"], sub.get("email",""), sub.get("genre",""),
                    sub.get("social_link",""), sub.get("spotify_link",""), sub.get("youtube_link",""),
                    sub.get("message",""), sub.get("status","new"), sub.get("submitted",""),
                    sub.get("reviewed_by",""), sub.get("review_notes",""), sub.get("decision","")
                ))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving label submission: {e}")
        return False

def get_label_submissions() -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM label_submissions ORDER BY submitted DESC")
        return [dict(r) for r in cur.fetchall()]

def save_label_calendar(event: dict) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_PG:
                cur.execute("""
                    INSERT INTO label_release_calendar
                    (id, title, artist, release_type, release_date, upc, genre, milestones, created)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    event["id"], event["title"], event.get("artist",""), event.get("release_type",""),
                    event.get("release_date",""), event.get("upc",""), event.get("genre",""),
                    json.dumps(event.get("milestones", [])), event.get("created","")
                ))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO label_release_calendar
                    (id, title, artist, release_type, release_date, upc, genre, milestones, created)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event["id"], event["title"], event.get("artist",""), event.get("release_type",""),
                    event.get("release_date",""), event.get("upc",""), event.get("genre",""),
                    json.dumps(event.get("milestones", [])), event.get("created","")
                ))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving label calendar: {e}")
        return False

def get_label_calendar() -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM label_release_calendar ORDER BY release_date")
        rows = cur.fetchall()
        result = []
        for row in rows:
            if USE_PG:
                d = dict(row)
            else:
                d = dict(row)
            try: d['milestones'] = json.loads(d.get('milestones', '[]'))
            except: d['milestones'] = []
            result.append(d)
        return result

def save_label_brand(brand: dict) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            if USE_PG:
                cur.execute("""
                    INSERT INTO label_brand
                    (id, primary_color, secondary_color, accent_color, font_primary, font_secondary,
                     logo_url, tagline, mission, label_values)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    brand.get("id", 1), brand.get("primary_color","#1a1a2e"),
                    brand.get("secondary_color","#e94560"), brand.get("accent_color","#0f3460"),
                    brand.get("font_primary","Inter"), brand.get("font_secondary","JetBrains Mono"),
                    brand.get("logo_url",""), brand.get("tagline","Where Faith Meets Sound"),
                    brand.get("mission",""), json.dumps(brand.get("values", []))
                ))
            else:
                cur.execute("""
                    INSERT OR REPLACE INTO label_brand
                    (id, primary_color, secondary_color, accent_color, font_primary, font_secondary,
                     logo_url, tagline, mission, label_values)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    brand.get("id", 1), brand.get("primary_color","#1a1a2e"),
                    brand.get("secondary_color","#e94560"), brand.get("accent_color","#0f3460"),
                    brand.get("font_primary","Inter"), brand.get("font_secondary","JetBrains Mono"),
                    brand.get("logo_url",""), brand.get("tagline","Where Faith Meets Sound"),
                    brand.get("mission",""), json.dumps(brand.get("values", []))
                ))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error saving label brand: {e}")
        return False

def get_label_brand() -> dict:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM label_brand WHERE id = 1")
        row = cur.fetchone()
        if row:
            if USE_PG:
                d = dict(row)
            else:
                d = dict(row)
            try: d['values'] = json.loads(d.get('label_values', '[]'))
            except: d['values'] = []
            return d
        return None

# Initialize on import
init_db()

# ============================================================
# Helper functions for database operations
# ============================================================

def get_royalty_split_agreement(agreement_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM royalty_split_agreements WHERE id = ?", (agreement_id,))
        row = cur.fetchone()
        if row:
            if USE_PG:
                d = dict(row)
            else:
                d = dict(row)
            try: d['parties'] = json.loads(d.get('parties', '[]'))
            except: d['parties'] = []
            return d
        return None

def get_label_artist_milestones(artist_id: str) -> List[str]:
    artist = get_label_artist(artist_id)
    return artist.get('milestones_completed', []) if artist else []

def update_label_artist_milestone(artist_id: str, milestone: str) -> bool:
    artist = get_label_artist(artist_id)
    if not artist:
        return False
    milestones = artist.get('milestones_completed', [])
    if milestone not in milestones:
        milestones.append(milestone)
        artist['milestones_completed'] = milestones
        if len(milestones) >= 1 and artist.get('stage') == 'development':
            artist['stage'] = 'active'
        if len(milestones) >= 3 and artist.get('stage') == 'active':
            artist['stage'] = 'graduated'
        save_label_artist(artist)
        return True
    return False

# ============================================================
# Audit, Orders, Mercantile
# ============================================================

def insert_audit(action: str, user_email: Optional[str], detail: str, meta: str) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("""
                INSERT INTO audit_log (action, user_email, detail, meta)
                VALUES (%s, %s, %s, %s)
            """, (action, user_email, detail, meta))
        else:
            cur.execute("""
                INSERT INTO audit_log (action, user_email, detail, meta)
                VALUES (?, ?, ?, ?)
            """, (action, user_email, detail, meta))
        conn.commit()
        return cur.lastrowid

def list_audit(limit: int = 100, offset: int = 0) -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        cur.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        return [dict(r) for r in cur.fetchall()]

def insert_order(customer_email: str, stripe_session_id: str, metadata: str, status: str, amount: float, raw_session: str) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        if USE_PG:
            cur.execute("""
                INSERT INTO orders (customer_email, stripe_session_id, metadata, status, amount, raw_session)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (customer_email, stripe_session_id, metadata, status, amount, raw_session))
        else:
            cur.execute("""
                INSERT INTO orders (customer_email, stripe_session_id, metadata, status, amount, raw_session)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (customer_email, stripe_session_id, metadata, status, amount, raw_session))
        conn.commit()
        return cur.lastrowid

def insert_mercantile_product(sku: str, name: str, description: str, category: str, price: float,
                              cost: float = 0.0, stock: int = 0, image_url: str = "", is_active: bool = True) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        active = 1 if is_active else 0
        if USE_PG:
            cur.execute("""
                INSERT INTO mercantile_products (sku, name, description, category, price, cost, stock, image_url, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(sku) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    price = EXCLUDED.price,
                    cost = EXCLUDED.cost,
                    stock = EXCLUDED.stock,
                    image_url = EXCLUDED.image_url,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
            """, (sku, name, description, category, price, cost, stock, image_url, active))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO mercantile_products (sku, name, description, category, price, cost, stock, image_url, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sku, name, description, category, price, cost, stock, image_url, active))
        conn.commit()
        return cur.lastrowid

def list_mercantile_products(category: Optional[str] = None, active_only: bool = True) -> list:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row if not USE_PG else None
        cur = conn.cursor()
        q = "SELECT * FROM mercantile_products WHERE 1=1"
        params = []
        if category:
            q += " AND category = ?"
            params.append(category)
        if active_only:
            q += " AND is_active = 1"
        q += " ORDER BY category, name"
        cur.execute(q, params)
        return [dict(r) for r in cur.fetchall()]

def update_mercantile_stock(sku: str, stock: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE mercantile_products SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE sku = ?", (stock, sku))
        conn.commit()
        return cur.rowcount > 0

print(f"Database initialized with {'PostgreSQL' if USE_PG else 'SQLite'} backend")
