"""
Patient Records endpoints — backed by PostgreSQL.
"""

from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.database import (
    _now, get_all_patients, get_patient, create_patient,
    update_patient_fields, delete_patient_db,
)

router = APIRouter(prefix="/api/patients", tags=["Patient Records"])


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
    patients = get_all_patients()
    if search:
        q = search.lower()
        patients = [p for p in patients if q in p["name"].lower() or q in p.get("phone", "")]
    return patients


@router.get("/{patient_id}", summary="Get patient by ID")
def get_patient_endpoint(patient_id: str) -> dict:
    p = get_patient(patient_id)
    if not p:
        raise HTTPException(404, f"Patient '{patient_id}' not found")
    return p


@router.post("", status_code=201, summary="Register new patient")
def create_patient_endpoint(body: PatientCreate) -> dict:
    pid = f"PAT-{uuid.uuid4().hex[:4].upper()}"
    data = {
        **body.model_dump(),
        "emergency_contact": None,
        "insurance": None,
        "last_visit": None,
    }
    return create_patient(pid, data)


@router.put("/{patient_id}", summary="Update patient details")
def update_patient_endpoint(patient_id: str, body: PatientUpdate) -> dict:
    p = get_patient(patient_id)
    if not p:
        raise HTTPException(404, f"Patient '{patient_id}' not found")
    updates = body.model_dump(exclude_none=True)
    result = update_patient_fields(patient_id, updates)
    return result


@router.delete("/{patient_id}", summary="Delete patient")
def delete_patient_endpoint(patient_id: str) -> dict:
    if not delete_patient_db(patient_id):
        raise HTTPException(404, f"Patient '{patient_id}' not found")
    return {"deleted": patient_id, "status": "ok"}


@router.get("/{patient_id}/risk-profile", summary="Generate risk profile")
def get_risk_profile(patient_id: str) -> dict:
    """Compute a mock risk profile based on patient data."""
    p = get_patient(patient_id)
    if not p:
        raise HTTPException(404, f"Patient '{patient_id}' not found")
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
