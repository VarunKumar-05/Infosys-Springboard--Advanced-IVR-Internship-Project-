"""
Supabase PostgreSQL connection layer.
Provides a connection pool, query helpers, and table initialization.
"""

from __future__ import annotations
import os
import json
import psycopg2
import psycopg2.pool
import psycopg2.extras
from contextlib import contextmanager

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        url = os.getenv("POSTGRES_DB_URL")
        if not url:
            raise RuntimeError("POSTGRES_DB_URL is not set")
        _pool = psycopg2.pool.ThreadedConnectionPool(1, 10, url)
    return _pool


@contextmanager
def get_conn():
    """Get a connection from the pool (auto-returned on exit)."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def execute(sql: str, params: tuple | dict | None = None) -> None:
    """Execute a write statement (INSERT, UPDATE, DELETE, DDL)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def fetch_one(sql: str, params: tuple | dict | None = None) -> dict | None:
    """Fetch a single row as a dict."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


def fetch_all(sql: str, params: tuple | dict | None = None) -> list[dict]:
    """Fetch all rows as a list of dicts."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


# ── Table Definitions ────────────────────────────────────────────────────

_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS scenarios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    language TEXT DEFAULT 'en-US',
    expected_triage_level TEXT,
    steps JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ambulances (
    id TEXT PRIMARY KEY,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    status TEXT DEFAULT 'available',
    type TEXT DEFAULT 'BLS',
    crew_size INT DEFAULT 2,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS patients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    age INT DEFAULT 0,
    gender TEXT DEFAULT 'unknown',
    phone TEXT DEFAULT '',
    blood_type TEXT DEFAULT '',
    allergies JSONB DEFAULT '[]'::jsonb,
    medical_history JSONB DEFAULT '[]'::jsonb,
    emergency_contact JSONB,
    insurance JSONB,
    call_notes JSONB DEFAULT '[]'::jsonb,
    last_visit TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS call_history (
    id SERIAL PRIMARY KEY,
    call_session_id TEXT NOT NULL,
    status TEXT DEFAULT 'completed',
    duration_seconds DOUBLE PRECISION DEFAULT 0,
    transcript JSONB DEFAULT '[]'::jsonb,
    triage_result JSONB,
    dispatch_result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analytics (
    id INT PRIMARY KEY DEFAULT 1,
    total_calls INT DEFAULT 0,
    emergency_calls INT DEFAULT 0,
    routine_calls INT DEFAULT 0,
    total_dispatches INT DEFAULT 0,
    total_response_time_ms INT DEFAULT 0,
    total_duration_seconds DOUBLE PRECISION DEFAULT 0,
    total_solver_time_ms INT DEFAULT 0,
    triage_correct INT DEFAULT 0,
    total_eta_minutes DOUBLE PRECISION DEFAULT 0
);

CREATE TABLE IF NOT EXISTS appointments (
    id TEXT PRIMARY KEY,
    patient_name TEXT DEFAULT 'Unknown',
    doctor_name TEXT NOT NULL,
    department TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    reason TEXT DEFAULT '',
    status TEXT DEFAULT 'confirmed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_logs (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    level TEXT DEFAULT 'INFO',
    source TEXT DEFAULT 'system',
    action TEXT DEFAULT '',
    message TEXT DEFAULT '',
    details JSONB
);

CREATE TABLE IF NOT EXISTS call_logs (
    id SERIAL PRIMARY KEY,
    call_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    data JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS resources (
    id INT PRIMARY KEY DEFAULT 1,
    emergency_room JSONB DEFAULT '{"total": 10, "available": 4, "staffed": 4}'::jsonb,
    urgent_care JSONB DEFAULT '{"total": 8, "available": 6, "staffed": 6}'::jsonb,
    general_ward JSONB DEFAULT '{"total": 50, "available": 22, "staffed": 22}'::jsonb,
    queue_length INT DEFAULT 8
);
"""


def init_db() -> None:
    """Create tables (idempotent) and seed initial data if tables are empty."""
    print("[DB] Initializing PostgreSQL tables...")
    execute(_TABLES_SQL)

    # Seed analytics row if not present
    row = fetch_one("SELECT id FROM analytics WHERE id = 1")
    if not row:
        execute("INSERT INTO analytics (id) VALUES (1)")

    # Seed resources row if not present
    row = fetch_one("SELECT id FROM resources WHERE id = 1")
    if not row:
        execute(
            "INSERT INTO resources (id) VALUES (1)"
        )

    # Seed scenarios if empty
    count = fetch_one("SELECT COUNT(*) as cnt FROM scenarios")
    if count and count["cnt"] == 0:
        _seed_scenarios()

    # Seed ambulances if empty
    count = fetch_one("SELECT COUNT(*) as cnt FROM ambulances")
    if count and count["cnt"] == 0:
        _seed_ambulances()

    # Seed patients if empty
    count = fetch_one("SELECT COUNT(*) as cnt FROM patients")
    if count and count["cnt"] == 0:
        _seed_patients()

    # Seed system logs if empty
    count = fetch_one("SELECT COUNT(*) as cnt FROM system_logs")
    if count and count["cnt"] == 0:
        _seed_logs()

    print("[DB] PostgreSQL initialization complete.")


# ── Seed Functions ───────────────────────────────────────────────────────

def _seed_scenarios() -> None:
    """Seed the scenarios table from the original in-memory data."""
    from app._seed_data import SEED_SCENARIOS
    for sid, s in SEED_SCENARIOS.items():
        execute(
            """INSERT INTO scenarios (id, name, description, category, language, expected_triage_level, steps, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
               ON CONFLICT (id) DO NOTHING""",
            (sid, s["name"], s["description"], s["category"], s["language"],
             s.get("expected_triage_level"), json.dumps(s["steps"])),
        )
    print(f"[DB] Seeded {len(SEED_SCENARIOS)} scenarios.")


def _seed_ambulances() -> None:
    """Seed the ambulances table."""
    from app._seed_data import SEED_AMBULANCES
    for aid, a in SEED_AMBULANCES.items():
        execute(
            """INSERT INTO ambulances (id, lat, lon, status, type, crew_size, last_updated)
               VALUES (%s, %s, %s, %s, %s, %s, NOW())
               ON CONFLICT (id) DO NOTHING""",
            (aid, a["location"]["lat"], a["location"]["lon"],
             a["status"].value if hasattr(a["status"], "value") else a["status"],
             a["type"].value if hasattr(a["type"], "value") else a["type"],
             a["crew_size"]),
        )
    print(f"[DB] Seeded {len(SEED_AMBULANCES)} ambulances.")


def _seed_patients() -> None:
    """Seed the patients table."""
    from app._seed_data import SEED_PATIENTS
    for pid, p in SEED_PATIENTS.items():
        execute(
            """INSERT INTO patients (id, name, age, gender, phone, blood_type, allergies, medical_history, emergency_contact, insurance, last_visit, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
               ON CONFLICT (id) DO NOTHING""",
            (pid, p["name"], p["age"], p["gender"], p.get("phone", ""),
             p.get("blood_type", ""), json.dumps(p.get("allergies", [])),
             json.dumps(p.get("medical_history", [])),
             json.dumps(p.get("emergency_contact")),
             json.dumps(p.get("insurance")),
             p.get("last_visit")),
        )
    print(f"[DB] Seeded {len(SEED_PATIENTS)} patients.")


def _seed_logs() -> None:
    """Seed the system_logs table."""
    from app._seed_data import SEED_LOGS
    for log in SEED_LOGS:
        execute(
            """INSERT INTO system_logs (id, timestamp, level, source, action, message, details)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO NOTHING""",
            (log["id"], log["timestamp"], log["level"], log["source"],
             log["action"], log["message"],
             json.dumps(log.get("details")) if log.get("details") else None),
        )
    print(f"[DB] Seeded {len(SEED_LOGS)} system log entries.")
