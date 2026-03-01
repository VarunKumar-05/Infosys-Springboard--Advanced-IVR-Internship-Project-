"""
Dispatch endpoints — ambulance assignment and fleet management.
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.models import (
    DispatchAssignRequest, DispatchAssignResponse, AmbulanceInfo,
)
from app.database import AMBULANCES, ANALYTICS, _now
from app.services import dispatch_engine

router = APIRouter(prefix="/api/dispatch", tags=["Ambulance Dispatch"])


@router.post("/assign", summary="Dispatch optimal ambulance to patient")
def assign_ambulance(body: DispatchAssignRequest) -> DispatchAssignResponse:
    """Run ILP dispatch solver to find the best ambulance for the patient."""
    result = dispatch_engine.assign(
        patient_lat=body.patient_location.lat,
        patient_lon=body.patient_location.lon,
        priority=body.priority,
        chief_complaint=body.chief_complaint,
        estimated_severity=body.estimated_severity,
        ambulance_type_required=body.ambulance_type_required,
    )
    if "error" in result:
        raise HTTPException(503, result["error"])

    # ── Update analytics in real time ────────────────────────────────
    ANALYTICS["total_dispatches"] += 1
    ANALYTICS["total_eta_minutes"] += result["eta_minutes"]
    ANALYTICS["total_solver_time_ms"] += result["solver_time_ms"]

    return DispatchAssignResponse(**result)


@router.get("/ambulances", summary="List all ambulances with status and GPS")
def list_ambulances() -> list[AmbulanceInfo]:
    """Return the full ambulance fleet with current status and location."""
    return [
        AmbulanceInfo(
            id=a["id"],
            location=a["location"],
            status=a["status"],
            type=a["type"],
            crew_size=a["crew_size"],
            last_updated=_now(),
        )
        for a in dispatch_engine.get_all_ambulances()
    ]


@router.get("/ambulances/{ambulance_id}", summary="Get single ambulance details")
def get_ambulance(ambulance_id: str) -> AmbulanceInfo:
    """Return details of a specific ambulance."""
    if ambulance_id not in AMBULANCES:
        raise HTTPException(404, f"Ambulance '{ambulance_id}' not found")
    a = AMBULANCES[ambulance_id]
    return AmbulanceInfo(
        id=a["id"], location=a["location"], status=a["status"],
        type=a["type"], crew_size=a["crew_size"], last_updated=_now(),
    )


@router.post("/ambulances/{ambulance_id}/reset", summary="Reset ambulance to available")
def reset_ambulance(ambulance_id: str) -> AmbulanceInfo:
    """Reset a dispatched ambulance back to available status."""
    result = dispatch_engine.reset_ambulance(ambulance_id)
    if result is None:
        raise HTTPException(404, f"Ambulance '{ambulance_id}' not found")
    return AmbulanceInfo(
        id=result["id"], location=result["location"], status=result["status"],
        type=result["type"], crew_size=result["crew_size"], last_updated=_now(),
    )


@router.post("/reset-all", summary="Reset all ambulances to available")
def reset_all_ambulances() -> dict:
    """Reset entire fleet to available (for testing purposes)."""
    count = 0
    for amb_id in AMBULANCES:
        dispatch_engine.reset_ambulance(amb_id)
        count += 1
    return {"reset_count": count, "status": "all ambulances available"}
