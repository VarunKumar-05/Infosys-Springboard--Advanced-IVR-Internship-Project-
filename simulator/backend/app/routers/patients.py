"""
Patient Records endpoints — mock patient registry for the simulator.
"""

from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.database import _now

router = APIRouter(prefix="/api/patients", tags=["Patient Records"])


# ── In-memory patient store ──────────────────────────────────────────────

PATIENTS: dict[str, dict] = {
    "PAT-001": {
        "id": "PAT-001",
        "name": "John Anderson",
        "age": 58,
        "gender": "male",
        "phone": "+1-555-0101",
        "blood_type": "O+",
        "allergies": ["Penicillin"],
        "medical_history": ["hypertension", "type 2 diabetes"],
        "emergency_contact": {"name": "Mary Anderson", "phone": "+1-555-0102", "relation": "spouse"},
        "insurance": {"provider": "BlueCross", "policy": "BC-449821", "status": "active"},
        "last_visit": "2026-02-15",
        "created_at": _now().isoformat(),
    },
    "PAT-002": {
        "id": "PAT-002",
        "name": "Sarah Johnson",
        "age": 34,
        "gender": "female",
        "phone": "+1-555-0201",
        "blood_type": "A-",
        "allergies": [],
        "medical_history": ["asthma"],
        "emergency_contact": {"name": "David Johnson", "phone": "+1-555-0202", "relation": "brother"},
        "insurance": {"provider": "Aetna", "policy": "AE-773152", "status": "active"},
        "last_visit": "2026-01-22",
        "created_at": _now().isoformat(),
    },
    "PAT-003": {
        "id": "PAT-003",
        "name": "Robert Chen",
        "age": 72,
        "gender": "male",
        "phone": "+1-555-0301",
        "blood_type": "B+",
        "allergies": ["Sulfa drugs", "Latex"],
        "medical_history": ["coronary artery disease", "atrial fibrillation", "COPD"],
        "emergency_contact": {"name": "Lisa Chen", "phone": "+1-555-0302", "relation": "daughter"},
        "insurance": {"provider": "Medicare", "policy": "MC-881234", "status": "active"},
        "last_visit": "2026-02-28",
        "created_at": _now().isoformat(),
    },
    "PAT-004": {
        "id": "PAT-004",
        "name": "Emily Martinez",
        "age": 5,
        "gender": "female",
        "phone": "+1-555-0401",
        "blood_type": "AB+",
        "allergies": ["Peanuts"],
        "medical_history": [],
        "emergency_contact": {"name": "Carlos Martinez", "phone": "+1-555-0402", "relation": "father"},
        "insurance": {"provider": "UnitedHealth", "policy": "UH-556789", "status": "active"},
        "last_visit": "2026-02-10",
        "created_at": _now().isoformat(),
    },
    "PAT-005": {
        "id": "PAT-005",
        "name": "James Wilson",
        "age": 45,
        "gender": "male",
        "phone": "+1-555-0501",
        "blood_type": "O-",
        "allergies": [],
        "medical_history": ["migraines", "lower back pain"],
        "emergency_contact": {"name": "Angela Wilson", "phone": "+1-555-0502", "relation": "spouse"},
        "insurance": {"provider": "Cigna", "policy": "CG-334567", "status": "expired"},
        "last_visit": "2025-12-05",
        "created_at": _now().isoformat(),
    },
}


# ── Request / response models ───────────────────────────────────────────

class PatientCreate(BaseModel):
    name: str
    age: int = Field(..., ge=0, le=150)
    gender: str = "unknown"
    phone: str = ""
    blood_type: str = ""
    allergies: list[str] = []
    medical_history: list[str] = []

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[list[str]] = None
    medical_history: Optional[list[str]] = None


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("", summary="List all patients")
def list_patients(search: str | None = None) -> list[dict]:
    """Return all patient records, optionally filtered by name search."""
    patients = list(PATIENTS.values())
    if search:
        q = search.lower()
        patients = [p for p in patients if q in p["name"].lower() or q in p.get("phone", "")]
    return patients


@router.get("/{patient_id}", summary="Get patient by ID")
def get_patient(patient_id: str) -> dict:
    if patient_id not in PATIENTS:
        raise HTTPException(404, f"Patient '{patient_id}' not found")
    return PATIENTS[patient_id]


@router.post("", status_code=201, summary="Register new patient")
def create_patient(body: PatientCreate) -> dict:
    pid = f"PAT-{uuid.uuid4().hex[:4].upper()}"
    patient = {
        "id": pid,
        **body.model_dump(),
        "emergency_contact": None,
        "insurance": None,
        "last_visit": None,
        "created_at": _now().isoformat(),
    }
    PATIENTS[pid] = patient
    return patient


@router.put("/{patient_id}", summary="Update patient details")
def update_patient(patient_id: str, body: PatientUpdate) -> dict:
    if patient_id not in PATIENTS:
        raise HTTPException(404, f"Patient '{patient_id}' not found")
    updates = body.model_dump(exclude_none=True)
    PATIENTS[patient_id].update(updates)
    return PATIENTS[patient_id]


@router.delete("/{patient_id}", summary="Delete patient")
def delete_patient(patient_id: str) -> dict:
    if patient_id not in PATIENTS:
        raise HTTPException(404, f"Patient '{patient_id}' not found")
    del PATIENTS[patient_id]
    return {"deleted": patient_id, "status": "ok"}


@router.get("/{patient_id}/risk-profile", summary="Generate risk profile")
def get_risk_profile(patient_id: str) -> dict:
    """Compute a mock risk profile based on patient data."""
    if patient_id not in PATIENTS:
        raise HTTPException(404, f"Patient '{patient_id}' not found")
    p = PATIENTS[patient_id]
    risk_score = 0
    factors = []

    if p["age"] >= 65:
        risk_score += 3
        factors.append(f"Age {p['age']} — elderly risk")
    elif p["age"] <= 5:
        risk_score += 2
        factors.append(f"Age {p['age']} — pediatric risk")

    for cond in p.get("medical_history", []):
        if cond.lower() in ("coronary artery disease", "hypertension", "diabetes", "type 2 diabetes"):
            risk_score += 2
            factors.append(f"Condition: {cond}")
        else:
            risk_score += 1
            factors.append(f"History: {cond}")

    if len(p.get("allergies", [])) > 1:
        risk_score += 1
        factors.append(f"Multiple allergies ({len(p['allergies'])})")

    level = "LOW" if risk_score <= 2 else "MODERATE" if risk_score <= 5 else "HIGH"

    return {
        "patient_id": patient_id,
        "risk_level": level,
        "risk_score": risk_score,
        "risk_factors": factors,
        "recommendation": {
            "LOW": "Standard care pathway",
            "MODERATE": "Enhanced monitoring recommended",
            "HIGH": "Priority care — assign senior physician",
        }[level],
    }
