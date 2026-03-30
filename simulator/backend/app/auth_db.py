"""
Authentication PostgreSQL connection layer.
Separate connection pool for the auth database — does NOT touch the
existing POSTGRES_DB_URL used for patient/scenario/ambulance records.
"""

from __future__ import annotations
import os
import psycopg2
import psycopg2.pool
import psycopg2.extras
from contextlib import contextmanager

_auth_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_auth_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _auth_pool
    if _auth_pool is None:
        url = os.getenv("AUTH_POSTGRES_DB_URL")
        if not url:
            raise RuntimeError("AUTH_POSTGRES_DB_URL is not set")
        _auth_pool = psycopg2.pool.ThreadedConnectionPool(1, 10, url)
    return _auth_pool


@contextmanager
def get_conn():
    """Get a connection from the auth pool (auto-returned on exit)."""
    pool = _get_auth_pool()
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
    """Execute a write statement."""
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

_AUTH_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER,
    phone_number TEXT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
"""


def init_auth_db() -> None:
    """Create auth tables (idempotent). Seeds a default admin if table is empty."""
    print("[Auth DB] Initializing authentication tables...")
    execute(_AUTH_TABLES_SQL)

    # Seed a default admin account if no users exist
    count = fetch_one("SELECT COUNT(*) as cnt FROM users")
    if count and count["cnt"] == 0:
        import bcrypt
        admin_hash = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        execute(
            """INSERT INTO users (name, age, phone_number, email, password_hash, role)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (email) DO NOTHING""",
            ("Admin", 30, "+1-000-000-0000", "admin@hospital.ai", admin_hash, "admin"),
        )
        print("[Auth DB] Seeded default admin: admin@hospital.ai / admin123")

    print("[Auth DB] Authentication tables ready.")
