"""
Analytics endpoints — metrics, call history, and performance data.
Reads from Supabase PostgreSQL via database.py proxy objects.
"""

from __future__ import annotations
from fastapi import APIRouter
from app.models import AnalyticsResponse, CallMetrics, DispatchMetrics
from app.database import (
    ANALYTICS, ACTIVE_CALLS, APPOINTMENTS, _now,
    get_analytics, get_call_history, get_all_ambulances_db,
    reset_analytics_db, get_all_appointments,
)
from app.models import AmbulanceStatus

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("", summary="Get full analytics dashboard data")
def get_analytics_endpoint() -> AnalyticsResponse:
    """Return aggregated metrics for calls, dispatch, and recent activity."""
    analytics = get_analytics()
    total = analytics["total_calls"] or 1
    dispatches = analytics["total_dispatches"] or 1

    ambulances = get_all_ambulances_db()
    available = sum(1 for a in ambulances if a["status"] == AmbulanceStatus.AVAILABLE)

    call_metrics = CallMetrics(
        total_calls=analytics["total_calls"],
        emergency_calls=analytics["emergency_calls"],
        routine_calls=analytics["routine_calls"],
        avg_duration_seconds=round(analytics["total_duration_seconds"] / total, 1),
        avg_response_time_ms=round(analytics["total_response_time_ms"] / total, 1),
        triage_accuracy_percent=round(analytics["triage_correct"] / total * 100, 1),
    )

    dispatch_metrics = DispatchMetrics(
        total_dispatches=analytics["total_dispatches"],
        avg_eta_minutes=round(analytics["total_eta_minutes"] / dispatches, 1) if analytics["total_dispatches"] else 0.0,
        ambulances_available=available,
        ambulances_total=len(ambulances),
        avg_solver_time_ms=round(analytics["total_solver_time_ms"] / dispatches, 1),
    )

    recent = get_call_history(10)

    return AnalyticsResponse(
        call_metrics=call_metrics,
        dispatch_metrics=dispatch_metrics,
        recent_calls=recent,
        timestamp=_now(),
    )


@router.get("/call-history", summary="Get completed call history")
def get_call_history_endpoint(limit: int = 20) -> list[dict]:
    """Return completed calls, newest first."""
    return get_call_history(limit)


@router.get("/active-calls", summary="Get currently active calls")
def get_active_calls() -> list[dict]:
    """Return all ongoing call sessions."""
    now = _now()
    return [
        {
            "call_session_id": cid,
            "status": s["status"],
            "current_step": s["current_step"],
            "duration_seconds": round((now - s["started_at"]).total_seconds(), 1),
            "scenario_id": s.get("scenario_id"),
        }
        for cid, s in ACTIVE_CALLS.items()
    ]


@router.post("/reset", summary="Reset all analytics counters")
def reset_analytics() -> dict:
    """Reset analytics to initial state (for testing)."""
    reset_analytics_db()
    from app import postgres_db as db
    db.execute("DELETE FROM call_history")
    return {"status": "analytics reset", "timestamp": _now().isoformat()}


@router.get("/appointments", summary="List all booked appointments")
def list_appointments() -> list[dict]:
    """Return all appointments booked through the IVR system."""
    return get_all_appointments()
