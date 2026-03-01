"""
System Logs endpoints — activity logging and audit trail for the simulator.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter

router = APIRouter(prefix="/api/logs", tags=["System Logs"])


# ── Pre-seeded log entries ───────────────────────────────────────────────

def _ts(minutes_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


LOGS: list[dict] = [
    {"id": "LOG-001", "timestamp": _ts(120), "level": "INFO",    "source": "system",   "action": "server_start",     "message": "IVR Simulator backend started on port 8000",             "details": None},
    {"id": "LOG-002", "timestamp": _ts(115), "level": "INFO",    "source": "nlu",      "action": "engine_init",      "message": "NLU engine initialized — 11 intents loaded",             "details": {"intents_count": 11}},
    {"id": "LOG-003", "timestamp": _ts(110), "level": "INFO",    "source": "triage",   "action": "engine_init",      "message": "Triage ILP engine initialized — 7 clinical rules",       "details": {"rules_count": 7}},
    {"id": "LOG-004", "timestamp": _ts(105), "level": "INFO",    "source": "dispatch", "action": "engine_init",      "message": "Dispatch ILP engine initialized — 12 ambulances loaded", "details": {"fleet_size": 12}},
    {"id": "LOG-005", "timestamp": _ts(90),  "level": "INFO",    "source": "calls",    "action": "call_start",       "message": "Call SIM-A1B2C3D4 started — scenario: emergency-chest-pain", "details": {"call_id": "SIM-A1B2C3D4", "scenario": "emergency-chest-pain"}},
    {"id": "LOG-006", "timestamp": _ts(89),  "level": "INFO",    "source": "nlu",      "action": "nlu_analyze",      "message": "Intent detected: symptom.emergency (confidence: 0.95)",  "details": {"intent": "symptom.emergency", "confidence": 0.95}},
    {"id": "LOG-007", "timestamp": _ts(88),  "level": "WARNING", "source": "triage",   "action": "triage_assess",    "message": "EMERGENCY triage — chest pain + age>40 hard constraint triggered", "details": {"triage_level": "EMERGENCY", "severity": 10}},
    {"id": "LOG-008", "timestamp": _ts(87),  "level": "INFO",    "source": "dispatch", "action": "dispatch_assign",  "message": "AMB-009 dispatched — ETA 3 min to patient location",     "details": {"ambulance": "AMB-009", "eta_minutes": 3}},
    {"id": "LOG-009", "timestamp": _ts(85),  "level": "INFO",    "source": "calls",    "action": "call_end",         "message": "Call SIM-A1B2C3D4 completed — 4 steps, 62s duration",    "details": {"call_id": "SIM-A1B2C3D4", "steps": 4, "duration": 62}},
    {"id": "LOG-010", "timestamp": _ts(60),  "level": "INFO",    "source": "calls",    "action": "call_start",       "message": "Call SIM-E5F6G7H8 started — free-form call",             "details": {"call_id": "SIM-E5F6G7H8"}},
    {"id": "LOG-011", "timestamp": _ts(58),  "level": "INFO",    "source": "nlu",      "action": "nlu_analyze",      "message": "Intent detected: appointment.booking (confidence: 0.92)", "details": {"intent": "appointment.booking", "confidence": 0.92}},
    {"id": "LOG-012", "timestamp": _ts(55),  "level": "INFO",    "source": "calls",    "action": "call_end",         "message": "Call SIM-E5F6G7H8 completed — 3 steps, 45s duration",    "details": {"call_id": "SIM-E5F6G7H8", "steps": 3, "duration": 45}},
    {"id": "LOG-013", "timestamp": _ts(30),  "level": "ERROR",   "source": "dispatch", "action": "dispatch_failed",  "message": "No ALS ambulances available — all units dispatched",     "details": {"requested_type": "ALS", "available": 0}},
    {"id": "LOG-014", "timestamp": _ts(25),  "level": "WARNING", "source": "triage",   "action": "resource_low",     "message": "ER capacity at 60% — 4 of 10 beds available",           "details": {"facility": "emergency_room", "available": 4, "total": 10}},
    {"id": "LOG-015", "timestamp": _ts(10),  "level": "INFO",    "source": "patients", "action": "patient_lookup",   "message": "Patient PAT-003 (Robert Chen) record accessed",         "details": {"patient_id": "PAT-003"}},
    {"id": "LOG-016", "timestamp": _ts(5),   "level": "INFO",    "source": "system",   "action": "health_check",     "message": "System health check — all services operational",         "details": {"nlu": "ok", "triage": "ok", "dispatch": "ok"}},
]


def _add_log(level: str, source: str, action: str, message: str, details: dict | None = None):
    """Internal helper — append a new log entry."""
    entry = {
        "id": f"LOG-{uuid.uuid4().hex[:6].upper()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "source": source,
        "action": action,
        "message": message,
        "details": details,
    }
    LOGS.append(entry)
    # Cap at 500 entries
    if len(LOGS) > 500:
        LOGS.pop(0)
    return entry


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("", summary="Get system logs")
def get_logs(
    level: str | None = None,
    source: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Return system logs, newest first. Filterable by level and source."""
    logs = list(reversed(LOGS))
    if level:
        logs = [l for l in logs if l["level"] == level.upper()]
    if source:
        logs = [l for l in logs if l["source"] == source.lower()]
    return logs[:limit]


@router.get("/stats", summary="Log statistics")
def get_log_stats() -> dict:
    """Return log count by level and source."""
    by_level: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for log in LOGS:
        by_level[log["level"]] = by_level.get(log["level"], 0) + 1
        by_source[log["source"]] = by_source.get(log["source"], 0) + 1
    return {
        "total": len(LOGS),
        "by_level": by_level,
        "by_source": by_source,
    }


@router.get("/sources", summary="List log sources")
def list_sources() -> list[str]:
    """Return distinct log sources."""
    return sorted({l["source"] for l in LOGS})


@router.get("/levels", summary="List log levels")
def list_levels() -> list[str]:
    return ["INFO", "WARNING", "ERROR", "CRITICAL"]


@router.post("/clear", summary="Clear all logs")
def clear_logs() -> dict:
    """Remove all log entries."""
    count = len(LOGS)
    LOGS.clear()
    _add_log("INFO", "system", "logs_cleared", f"Cleared {count} log entries")
    return {"cleared": count, "status": "ok"}
