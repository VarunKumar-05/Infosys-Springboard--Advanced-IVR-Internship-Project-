"""
Triage assessment endpoints — standalone symptom triage without a call session.
"""

from __future__ import annotations
from fastapi import APIRouter
from app.models import TriageAssessRequest, TriageAssessResponse, ResourceAvailability
from app.database import RESOURCES, _now
from app.services import triage_engine

router = APIRouter(prefix="/api/triage", tags=["Triage Assessment"])


@router.post("/assess", summary="Run triage assessment on symptoms")
def assess_symptoms(body: TriageAssessRequest) -> TriageAssessResponse:
    """Simulate ILP-based triage solver for given symptoms and patient data."""
    result = triage_engine.assess(
        symptoms=body.symptoms,
        severity_score=body.severity_score,
        patient_age=body.patient_age,
        patient_gender=body.patient_gender,
        medical_history=body.medical_history,
        duration_minutes=body.duration_minutes,
    )
    return TriageAssessResponse(**result)


@router.get("/resources", summary="Check hospital resource availability")
def get_resources() -> ResourceAvailability:
    """Return current real-time hospital resource state."""
    return ResourceAvailability(
        emergency_room=RESOURCES["emergency_room"],
        urgent_care=RESOURCES["urgent_care"],
        general_ward=RESOURCES["general_ward"],
        queue_length=RESOURCES["queue_length"],
        last_updated=_now(),
    )


@router.put("/resources", summary="Update hospital resources (admin)")
def update_resources(
    er_available: int | None = None,
    uc_available: int | None = None,
    gw_available: int | None = None,
    queue_length: int | None = None,
) -> ResourceAvailability:
    """Manually update resource counts for simulation tuning."""
    if er_available is not None:
        RESOURCES["emergency_room"]["available"] = max(0, min(er_available, RESOURCES["emergency_room"]["total"]))
        RESOURCES["emergency_room"]["staffed"] = RESOURCES["emergency_room"]["available"]
    if uc_available is not None:
        RESOURCES["urgent_care"]["available"] = max(0, min(uc_available, RESOURCES["urgent_care"]["total"]))
        RESOURCES["urgent_care"]["staffed"] = RESOURCES["urgent_care"]["available"]
    if gw_available is not None:
        RESOURCES["general_ward"]["available"] = max(0, min(gw_available, RESOURCES["general_ward"]["total"]))
        RESOURCES["general_ward"]["staffed"] = RESOURCES["general_ward"]["available"]
    if queue_length is not None:
        RESOURCES["queue_length"] = max(0, queue_length)
    return ResourceAvailability(
        emergency_room=RESOURCES["emergency_room"],
        urgent_care=RESOURCES["urgent_care"],
        general_ward=RESOURCES["general_ward"],
        queue_length=RESOURCES["queue_length"],
        last_updated=_now(),
    )


@router.get("/rules", summary="List clinical triage rules")
def list_rules() -> list[dict]:
    """Return the clinical rules used by the triage engine."""
    return [
        {"rule": "EMERGENCY_SYMPTOMS", "description": "Chest pain, stroke, seizure, etc. → severity ≥ 8", "action": "Route to ER"},
        {"rule": "URGENT_SYMPTOMS", "description": "High fever, fracture, migraine → severity 5-7", "action": "Route to Urgent Care"},
        {"rule": "CARDIAC_RISK", "description": "Chest pain + age > 40 → mandatory cardiac eval", "action": "HARD CONSTRAINT → ER"},
        {"rule": "PEDIATRIC_PRIORITY", "description": "Patient age ≤ 5 → +2 severity modifier", "action": "Elevated priority"},
        {"rule": "AGE_RISK", "description": "Patient age ≥ 50 → +1 severity modifier for cardiac", "action": "Risk factor added"},
        {"rule": "DURATION_RISK", "description": "Symptoms > 30 min + emergency → escalated", "action": "Risk factor added"},
        {"rule": "RESOURCE_CONSTRAINT", "description": "ER at capacity → divert to partner hospital", "action": "Alternate facility"},
    ]
