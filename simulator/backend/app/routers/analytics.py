"""
Analytics endpoints — metrics, call history, and performance data.
"""

from __future__ import annotations
from fastapi import APIRouter
from app.models import AnalyticsResponse, CallMetrics, DispatchMetrics
from app.database import (
    ANALYTICS, CALL_HISTORY, AMBULANCES, ACTIVE_CALLS, _now,
)
from app.models import AmbulanceStatus

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("", summary="Get full analytics dashboard data")
def get_analytics() -> AnalyticsResponse:
    """Return aggregated metrics for calls, dispatch, and recent activity."""
    total = ANALYTICS["total_calls"] or 1
    dispatches = ANALYTICS["total_dispatches"] or 1

    available = sum(1 for a in AMBULANCES.values() if a["status"] == AmbulanceStatus.AVAILABLE)

    call_metrics = CallMetrics(
        total_calls=ANALYTICS["total_calls"],
        emergency_calls=ANALYTICS["emergency_calls"],
        routine_calls=ANALYTICS["routine_calls"],
        avg_duration_seconds=round(ANALYTICS["total_duration_seconds"] / total, 1),
        avg_response_time_ms=round(ANALYTICS["total_response_time_ms"] / total, 1),
        triage_accuracy_percent=round(ANALYTICS["triage_correct"] / total * 100, 1),
    )

    dispatch_metrics = DispatchMetrics(
        total_dispatches=ANALYTICS["total_dispatches"],
        avg_eta_minutes=round(ANALYTICS["total_eta_minutes"] / dispatches, 1) if ANALYTICS["total_dispatches"] else 0.0,
        ambulances_available=available,
        ambulances_total=len(AMBULANCES),
        avg_solver_time_ms=round(ANALYTICS["total_solver_time_ms"] / dispatches, 1),
    )

    recent = CALL_HISTORY[-10:][::-1]

    return AnalyticsResponse(
        call_metrics=call_metrics,
        dispatch_metrics=dispatch_metrics,
        recent_calls=recent,
        timestamp=_now(),
    )


@router.get("/call-history", summary="Get completed call history")
def get_call_history(limit: int = 20) -> list[dict]:
    """Return completed calls, newest first."""
    return CALL_HISTORY[-limit:][::-1]


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
    ANALYTICS.update({
        "total_calls": 0,
        "emergency_calls": 0,
        "routine_calls": 0,
        "total_dispatches": 0,
        "total_response_time_ms": 0,
        "total_duration_seconds": 0.0,
        "total_solver_time_ms": 0,
        "triage_correct": 0,
        "total_eta_minutes": 0.0,
    })
    CALL_HISTORY.clear()
    return {"status": "analytics reset", "timestamp": _now().isoformat()}
