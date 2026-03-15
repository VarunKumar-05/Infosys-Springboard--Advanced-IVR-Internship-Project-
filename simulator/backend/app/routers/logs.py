"""
System Logs endpoints — backed by Supabase PostgreSQL.
"""

from __future__ import annotations
import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter
from app import supabase_db as db

router = APIRouter(prefix="/api/logs", tags=["System Logs"])


def _add_log(level: str, source: str, action: str, message: str, details: dict | None = None):
    """Append a new log entry to the system_logs table."""
    entry_id = f"LOG-{uuid.uuid4().hex[:6].upper()}"
    db.execute(
        """INSERT INTO system_logs (id, timestamp, level, source, action, message, details)
           VALUES (%s, NOW(), %s, %s, %s, %s, %s)""",
        (entry_id, level, source, action, message,
         json.dumps(details) if details else None),
    )
    return {
        "id": entry_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level, "source": source, "action": action,
        "message": message, "details": details,
    }


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("", summary="Get system logs")
def get_logs(
    level: str | None = None,
    source: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Return system logs, newest first. Filterable by level and source."""
    conditions = []
    params: list = []
    if level:
        conditions.append("level = %s")
        params.append(level.upper())
    if source:
        conditions.append("source = %s")
        params.append(source.lower())

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    rows = db.fetch_all(
        f"SELECT * FROM system_logs {where} ORDER BY timestamp DESC LIMIT %s",
        tuple(params),
    )
    # Parse details JSON
    for r in rows:
        if isinstance(r.get("details"), str):
            try:
                r["details"] = json.loads(r["details"])
            except Exception:
                pass
    return rows


@router.get("/stats", summary="Log statistics")
def get_log_stats() -> dict:
    """Return log count by level and source."""
    by_level = db.fetch_all(
        "SELECT level, COUNT(*) as cnt FROM system_logs GROUP BY level"
    )
    by_source = db.fetch_all(
        "SELECT source, COUNT(*) as cnt FROM system_logs GROUP BY source"
    )
    total = db.fetch_one("SELECT COUNT(*) as cnt FROM system_logs")
    return {
        "total": total["cnt"] if total else 0,
        "by_level": {r["level"]: r["cnt"] for r in by_level},
        "by_source": {r["source"]: r["cnt"] for r in by_source},
    }


@router.get("/sources", summary="List log sources")
def list_sources() -> list[str]:
    """Return distinct log sources."""
    rows = db.fetch_all("SELECT DISTINCT source FROM system_logs ORDER BY source")
    return [r["source"] for r in rows]


@router.get("/levels", summary="List log levels")
def list_levels() -> list[str]:
    return ["INFO", "WARNING", "ERROR", "CRITICAL"]


@router.post("/clear", summary="Clear all logs")
def clear_logs() -> dict:
    """Remove all log entries."""
    count_row = db.fetch_one("SELECT COUNT(*) as cnt FROM system_logs")
    count = count_row["cnt"] if count_row else 0
    db.execute("DELETE FROM system_logs")
    _add_log("INFO", "system", "logs_cleared", f"Cleared {count} log entries")
    return {"cleared": count, "status": "ok"}
