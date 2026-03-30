"""
Database layer for the IVR Simulator — backed by PostgreSQL.
Provides the same public API as the original in-memory version, but all
reads/writes go through PostgreSQL via postgres_db helpers.

ACTIVE_CALLS remains in-memory (ephemeral session state).
"""

from __future__ import annotations
import json
import math
import uuid
from datetime import datetime, timezone
from app.models import (
    AmbulanceStatus, AmbulanceType, CallStatus,
    TriageLevel, Location,
)
from app import postgres_db as db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id() -> str:
    return uuid.uuid4().hex[:8].upper()


# ── Scenarios (PostgreSQL) ───────────────────────────────────────────────

def get_all_scenarios() -> list[dict]:
    rows = db.fetch_all("SELECT * FROM scenarios ORDER BY name")
    for r in rows:
        if isinstance(r.get("steps"), str):
            r["steps"] = json.loads(r["steps"])
        r.setdefault("steps", [])
    return rows


def get_scenario(scenario_id: str) -> dict | None:
    row = db.fetch_one("SELECT * FROM scenarios WHERE id = %s", (scenario_id,))
    if row and isinstance(row.get("steps"), str):
        row["steps"] = json.loads(row["steps"])
    return row


def upsert_scenario(scenario_id: str, data: dict) -> None:
    db.execute(
        """INSERT INTO scenarios (id, name, description, category, language, expected_triage_level, steps, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (id) DO UPDATE SET
             name=EXCLUDED.name, description=EXCLUDED.description, category=EXCLUDED.category,
             language=EXCLUDED.language, expected_triage_level=EXCLUDED.expected_triage_level,
             steps=EXCLUDED.steps, updated_at=EXCLUDED.updated_at""",
        (scenario_id, data["name"], data.get("description", ""),
         data.get("category", "general"), data.get("language", "en-US"),
         data.get("expected_triage_level"),
         json.dumps(data.get("steps", [])),
         data.get("created_at", _now().isoformat()),
         data.get("updated_at", _now().isoformat())),
    )


def delete_scenario(scenario_id: str) -> bool:
    row = db.fetch_one("SELECT id FROM scenarios WHERE id = %s", (scenario_id,))
    if not row:
        return False
    db.execute("DELETE FROM scenarios WHERE id = %s", (scenario_id,))
    return True


# ── Backward compat: SCENARIOS dict-like access via a lazy wrapper ───────
# Routers that do SCENARIOS[id] or `for s in SCENARIOS.values()` will still
# work through this wrapper that delegates to PostgreSQL.

class _ScenariosProxy:
    """Dict-like proxy that reads/writes scenarios from PostgreSQL."""
    def __getitem__(self, key):
        row = get_scenario(key)
        if row is None:
            raise KeyError(key)
        return row

    def __contains__(self, key):
        return get_scenario(key) is not None

    def __setitem__(self, key, value):
        upsert_scenario(key, value)

    def __delitem__(self, key):
        if not delete_scenario(key):
            raise KeyError(key)

    def values(self):
        return get_all_scenarios()

    def items(self):
        return [(s["id"], s) for s in get_all_scenarios()]

    def get(self, key, default=None):
        row = get_scenario(key)
        return row if row is not None else default

    def __len__(self):
        row = db.fetch_one("SELECT COUNT(*) as cnt FROM scenarios")
        return row["cnt"] if row else 0


SCENARIOS = _ScenariosProxy()


# ── Ambulances (PostgreSQL) ──────────────────────────────────────────────

def get_all_ambulances_db() -> list[dict]:
    rows = db.fetch_all("SELECT * FROM ambulances ORDER BY id")
    return [_row_to_ambulance(r) for r in rows]


def get_ambulance_db(amb_id: str) -> dict | None:
    row = db.fetch_one("SELECT * FROM ambulances WHERE id = %s", (amb_id,))
    return _row_to_ambulance(row) if row else None


def update_ambulance_db(amb_id: str, updates: dict) -> None:
    sets = []
    vals = []
    for k, v in updates.items():
        if k == "location":
            sets.append("lat = %s")
            vals.append(v["lat"])
            sets.append("lon = %s")
            vals.append(v["lon"])
        elif k == "status":
            sets.append("status = %s")
            vals.append(v.value if hasattr(v, "value") else v)
        elif k == "type":
            sets.append("type = %s")
            vals.append(v.value if hasattr(v, "value") else v)
        else:
            sets.append(f"{k} = %s")
            vals.append(v)
    sets.append("last_updated = NOW()")
    vals.append(amb_id)
    db.execute(f"UPDATE ambulances SET {', '.join(sets)} WHERE id = %s", tuple(vals))


def _row_to_ambulance(row: dict) -> dict:
    return {
        "id": row["id"],
        "location": {"lat": row["lat"], "lon": row["lon"]},
        "status": AmbulanceStatus(row["status"]),
        "type": AmbulanceType(row["type"]),
        "crew_size": row["crew_size"],
        "last_updated": row.get("last_updated", _now()).isoformat()
             if not isinstance(row.get("last_updated"), str)
             else row.get("last_updated", ""),
    }


class _AmbulancesProxy:
    """Dict-like proxy for ambulances table in PostgreSQL."""
    def __getitem__(self, key):
        row = get_ambulance_db(key)
        if row is None:
            raise KeyError(key)
        return row

    def __contains__(self, key):
        return get_ambulance_db(key) is not None

    def __setitem__(self, key, value):
        # Update existing or ignore (ambulances are seeded)
        update_ambulance_db(key, value)

    def values(self):
        return get_all_ambulances_db()

    def items(self):
        ambs = get_all_ambulances_db()
        return [(a["id"], a) for a in ambs]

    def __iter__(self):
        return iter([a["id"] for a in get_all_ambulances_db()])

    def __len__(self):
        row = db.fetch_one("SELECT COUNT(*) as cnt FROM ambulances")
        return row["cnt"] if row else 0


AMBULANCES = _AmbulancesProxy()


# ── Resources (PostgreSQL) ──────────────────────────────────────────────

def get_resources() -> dict:
    row = db.fetch_one("SELECT * FROM resources WHERE id = 1")
    if not row:
        return {
            "emergency_room": {"total": 10, "available": 4, "staffed": 4},
            "urgent_care": {"total": 8, "available": 6, "staffed": 6},
            "general_ward": {"total": 50, "available": 22, "staffed": 22},
            "queue_length": 8,
        }
    return {
        "emergency_room": row["emergency_room"] if isinstance(row["emergency_room"], dict) else json.loads(row["emergency_room"]),
        "urgent_care": row["urgent_care"] if isinstance(row["urgent_care"], dict) else json.loads(row["urgent_care"]),
        "general_ward": row["general_ward"] if isinstance(row["general_ward"], dict) else json.loads(row["general_ward"]),
        "queue_length": row["queue_length"],
    }


class _ResourcesProxy:
    """Dict-like proxy for resources in PostgreSQL."""
    def __getitem__(self, key):
        return get_resources()[key]

    def get(self, key, default=None):
        return get_resources().get(key, default)

    def __contains__(self, key):
        return key in get_resources()


RESOURCES = _ResourcesProxy()


# ── Active Calls (IN-MEMORY — ephemeral session state) ───────────────────

ACTIVE_CALLS: dict[str, dict] = {}


# ── Call History (PostgreSQL) ────────────────────────────────────────────

def add_call_history(entry: dict) -> None:
    db.execute(
        """INSERT INTO call_history (call_session_id, status, duration_seconds, transcript, triage_result, dispatch_result, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
        (entry.get("call_session_id", ""),
         entry.get("status", "completed"),
         entry.get("duration_seconds", 0),
         json.dumps(entry.get("transcript", [])),
         json.dumps(entry.get("triage_result")),
         json.dumps(entry.get("dispatch_result"))),
    )


def get_call_history(limit: int = 50) -> list[dict]:
    rows = db.fetch_all(
        "SELECT * FROM call_history ORDER BY created_at DESC LIMIT %s", (limit,)
    )
    for r in rows:
        for field in ("transcript", "triage_result", "dispatch_result"):
            if isinstance(r.get(field), str):
                try:
                    r[field] = json.loads(r[field])
                except Exception:
                    pass
    return rows


class _CallHistoryProxy:
    """List-like proxy for call_history in PostgreSQL."""
    def append(self, entry):
        add_call_history(entry)

    def __getitem__(self, item):
        rows = get_call_history(100)
        return rows[item]

    def __len__(self):
        row = db.fetch_one("SELECT COUNT(*) as cnt FROM call_history")
        return row["cnt"] if row else 0

    def clear(self):
        db.execute("DELETE FROM call_history")


CALL_HISTORY = _CallHistoryProxy()


# ── Analytics (PostgreSQL) ──────────────────────────────────────────────

def get_analytics() -> dict:
    row = db.fetch_one("SELECT * FROM analytics WHERE id = 1")
    if not row:
        return {
            "total_calls": 0, "emergency_calls": 0, "routine_calls": 0,
            "total_dispatches": 0, "total_response_time_ms": 0,
            "total_duration_seconds": 0.0, "total_solver_time_ms": 0,
            "triage_correct": 0, "total_eta_minutes": 0.0,
        }
    return {k: v for k, v in row.items() if k != "id"}


def increment_analytics(field: str, value=1) -> None:
    db.execute(
        f"UPDATE analytics SET {field} = {field} + %s WHERE id = 1",
        (value,),
    )


def reset_analytics_db() -> None:
    db.execute(
        """UPDATE analytics SET
             total_calls=0, emergency_calls=0, routine_calls=0,
             total_dispatches=0, total_response_time_ms=0,
             total_duration_seconds=0, total_solver_time_ms=0,
             triage_correct=0, total_eta_minutes=0
           WHERE id = 1"""
    )


class _AnalyticsProxy:
    """Dict-like proxy for analytics in PostgreSQL."""
    def __getitem__(self, key):
        return get_analytics()[key]

    def __setitem__(self, key, value):
        # For backward compat: ANALYTICS["total_calls"] += 1
        # This is called as ANALYTICS[key] = ANALYTICS[key] + val
        # We just set the value directly
        db.execute(
            f"UPDATE analytics SET {key} = %s WHERE id = 1",
            (value,),
        )

    def get(self, key, default=None):
        return get_analytics().get(key, default)

    def update(self, d: dict):
        if not d:
            return
        sets = ", ".join(f"{k} = %s" for k in d.keys())
        vals = list(d.values())
        vals.append(1)
        db.execute(f"UPDATE analytics SET {sets} WHERE id = %s", tuple(vals))


ANALYTICS = _AnalyticsProxy()


# ── Call Logs (PostgreSQL) ──────────────────────────────────────────────

def log_call_event(call_id: str, event_type: str, data: dict) -> dict:
    """Append a timestamped event to the call log table."""
    entry = {
        "call_id": call_id,
        "event_type": event_type,
        "data": data,
        "timestamp": _now().isoformat(),
    }
    db.execute(
        """INSERT INTO call_logs (call_id, event_type, data, timestamp)
           VALUES (%s, %s, %s, NOW())""",
        (call_id, event_type, json.dumps(data, default=str)),
    )
    return entry


class _CallLogsProxy:
    """List-like proxy for call_logs in PostgreSQL."""
    def append(self, entry):
        db.execute(
            """INSERT INTO call_logs (call_id, event_type, data, timestamp)
               VALUES (%s, %s, %s, NOW())""",
            (entry.get("call_id", ""), entry.get("event_type", ""),
             json.dumps(entry.get("data", {}), default=str)),
        )

    def __len__(self):
        row = db.fetch_one("SELECT COUNT(*) as cnt FROM call_logs")
        return row["cnt"] if row else 0


CALL_LOGS = _CallLogsProxy()


# ── Appointments (PostgreSQL) ───────────────────────────────────────────

def book_appointment(
    patient_name: str,
    doctor_name: str,
    department: str,
    date: str,
    time: str,
    reason: str,
) -> dict:
    """Create a new appointment record in PostgreSQL."""
    appt_id = f"APPT-{_id()}"
    appointment = {
        "id": appt_id,
        "patient_name": patient_name,
        "doctor_name": doctor_name,
        "department": department,
        "date": date,
        "time": time,
        "reason": reason,
        "status": "confirmed",
        "created_at": _now().isoformat(),
    }
    db.execute(
        """INSERT INTO appointments (id, patient_name, doctor_name, department, date, time, reason, status, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
        (appt_id, patient_name, doctor_name, department, date, time, reason, "confirmed"),
    )
    return appointment


def get_all_appointments() -> list[dict]:
    return db.fetch_all("SELECT * FROM appointments ORDER BY created_at DESC")


def cancel_appointment(patient_name: str = None, department: str = None, doctor_name: str = None, date: str = None) -> dict:
    """Cancel an appointment based on given criteria"""
    query = "SELECT * FROM appointments WHERE status = 'confirmed'"
    args = []
    
    if patient_name and patient_name.lower() != "unknown":
        query += " AND LOWER(patient_name) LIKE %s"
        args.append(f"%{patient_name.lower()}%")
    if department:
        query += " AND LOWER(department) LIKE %s"
        args.append(f"%{department.lower()}%")
    if doctor_name:
        query += " AND LOWER(doctor_name) LIKE %s"
        args.append(f"%{doctor_name.lower()}%")
    if date:
        query += " AND date = %s"
        args.append(date)
        
    query += " ORDER BY created_at DESC LIMIT 1"
    
    row = db.fetch_one(query, tuple(args))
    if not row:
        return {"error": "No matching confirmed appointment found to cancel."}
    
    db.execute("UPDATE appointments SET status = 'cancelled' WHERE id = %s", (row["id"],))
    row["status"] = "cancelled"
    return {"message": "Appointment cancelled successfully.", "appointment": row}


class _AppointmentsProxy:
    """List-like proxy for appointments in PostgreSQL."""
    def append(self, entry):
        db.execute(
            """INSERT INTO appointments (id, patient_name, doctor_name, department, date, time, reason, status, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
               ON CONFLICT (id) DO NOTHING""",
            (entry.get("id", f"APPT-{_id()}"), entry.get("patient_name", ""),
             entry.get("doctor_name", ""), entry.get("department", ""),
             entry.get("date", ""), entry.get("time", ""),
             entry.get("reason", ""), entry.get("status", "confirmed")),
        )

    def __iter__(self):
        return iter(get_all_appointments())

    def __len__(self):
        row = db.fetch_one("SELECT COUNT(*) as cnt FROM appointments")
        return row["cnt"] if row else 0


APPOINTMENTS = _AppointmentsProxy()


# ── Patient Database Functions ──────────────────────────────────────────

def get_all_patients() -> list[dict]:
    rows = db.fetch_all("SELECT * FROM patients ORDER BY name")
    return [_fix_patient_json(r) for r in rows]


def get_patient(patient_id: str) -> dict | None:
    row = db.fetch_one("SELECT * FROM patients WHERE id = %s", (patient_id,))
    return _fix_patient_json(row) if row else None


def create_patient(patient_id: str, data: dict) -> dict:
    db.execute(
        """INSERT INTO patients (id, name, age, gender, phone, blood_type, allergies, medical_history, emergency_contact, insurance, last_visit, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
        (patient_id, data["name"], data.get("age", 0), data.get("gender", "unknown"),
         data.get("phone", ""), data.get("blood_type", ""),
         json.dumps(data.get("allergies", [])),
         json.dumps(data.get("medical_history", [])),
         json.dumps(data.get("emergency_contact")),
         json.dumps(data.get("insurance")),
         data.get("last_visit")),
    )
    return {"id": patient_id, **data}


def update_patient_fields(patient_id: str, updates: dict) -> dict | None:
    p = get_patient(patient_id)
    if not p:
        return None
    if not updates:
        return p
    # Handle JSON fields
    json_fields = {"allergies", "medical_history", "emergency_contact", "insurance", "call_notes"}
    sets = []
    vals = []
    for k, v in updates.items():
        if k in json_fields:
            sets.append(f"{k} = %s")
            vals.append(json.dumps(v))
        else:
            sets.append(f"{k} = %s")
            vals.append(v)
    vals.append(patient_id)
    db.execute(f"UPDATE patients SET {', '.join(sets)} WHERE id = %s", tuple(vals))
    return get_patient(patient_id)


def delete_patient_db(patient_id: str) -> bool:
    row = db.fetch_one("SELECT id FROM patients WHERE id = %s", (patient_id,))
    if not row:
        return False
    db.execute("DELETE FROM patients WHERE id = %s", (patient_id,))
    return True


def lookup_patient_by_phone(phone: str) -> dict | None:
    row = db.fetch_one("SELECT * FROM patients WHERE phone = %s", (phone,))
    return _fix_patient_json(row) if row else None


def lookup_patient_by_name(name: str) -> list[dict]:
    rows = db.fetch_all(
        "SELECT * FROM patients WHERE LOWER(name) LIKE %s",
        (f"%{name.lower()}%",),
    )
    return [_fix_patient_json(r) for r in rows]


def lookup_patient_by_symptoms(symptoms: list[str]) -> list[dict]:
    """Find patients whose medical_history matches any of the given symptoms."""
    all_patients = get_all_patients()
    symptoms_lower = {s.lower() for s in symptoms}
    results = []
    for p in all_patients:
        history = {h.lower() for h in p.get("medical_history", [])}
        overlap = symptoms_lower & history
        if overlap:
            results.append({**p, "matching_conditions": list(overlap)})
    return results


def update_patient_record(
    patient_id: str,
    new_symptoms: list[str] | None = None,
    notes: str | None = None,
    name: str | None = None,
) -> dict | None:
    """Update a patient record with new symptoms and/or call notes."""
    p = get_patient(patient_id)
    if not p:
        return None
    updates = {}
    if name and name.lower() != "unknown":
        updates["name"] = name
    if new_symptoms:
        existing = p.get("medical_history", [])
        for s in new_symptoms:
            if s.lower() not in [e.lower() for e in existing]:
                existing.append(s)
        updates["medical_history"] = existing
    if notes:
        call_notes = p.get("call_notes", []) or []
        call_notes.append({"note": notes, "timestamp": _now().isoformat()})
        updates["call_notes"] = call_notes
    updates["last_visit"] = _now().isoformat()
    return update_patient_fields(patient_id, updates)


def _fix_patient_json(row: dict) -> dict:
    """Parse JSON string fields back into Python objects."""
    if not row:
        return row
    for field in ("allergies", "medical_history", "emergency_contact", "insurance", "call_notes"):
        val = row.get(field)
        if isinstance(val, str):
            try:
                row[field] = json.loads(val)
            except Exception:
                pass
        elif val is None and field in ("allergies", "medical_history", "call_notes"):
            row[field] = []
    return row


# ── Helpers ──────────────────────────────────────────────────────────────

def haversine_km(loc1: dict, loc2: dict) -> float:
    """Approximate distance between two lat/lon points in km."""
    R = 6371.0
    lat1, lon1 = math.radians(loc1["lat"]), math.radians(loc1["lon"])
    lat2, lon2 = math.radians(loc2["lat"]), math.radians(loc2["lon"])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))
