"""
In-memory data store for the IVR Simulator.
Holds scenarios, active calls, ambulances, and resource state.
Pre-loaded with realistic mock data.
"""

from __future__ import annotations
import math
import uuid
from datetime import datetime, timezone
from app.models import (
    AmbulanceStatus, AmbulanceType, CallStatus,
    TriageLevel, Location,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id() -> str:
    return uuid.uuid4().hex[:8].upper()


# ── Pre-built Scenarios ──────────────────────────────────────────────────

SCENARIOS: dict[str, dict] = {
    "emergency-chest-pain": {
        "id": "emergency-chest-pain",
        "name": "Emergency - Chest Pain",
        "description": "Patient experiencing severe chest pain radiating to left arm. High-priority cardiac emergency scenario.",
        "category": "emergency",
        "language": "en-US",
        "expected_triage_level": "EMERGENCY",
        "created_at": _now().isoformat(),
        "updated_at": _now().isoformat(),
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I'm having really bad chest pain and it's going to my left arm", "action": None, "expected_intent": "symptom.emergency"},
            {"step_number": 3, "speaker": "system", "content": "I understand you're experiencing chest pain radiating to your left arm. This could be serious. Let me assess this immediately.", "action": "triage_assess", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "Based on your symptoms, this is classified as an EMERGENCY. An ambulance has been dispatched to your location.", "action": "dispatch_ambulance", "expected_intent": None},
            {"step_number": 5, "speaker": "system", "content": "Ambulance AMB-007 is on its way. Estimated arrival: 5 minutes. Please stay on the line while I transfer you to the ER desk.", "action": "transfer_er", "expected_intent": None},
        ],
    },
    "emergency-breathing": {
        "id": "emergency-breathing",
        "name": "Emergency - Difficulty Breathing",
        "description": "Patient with severe shortness of breath and wheezing. Respiratory emergency.",
        "category": "emergency",
        "language": "en-US",
        "expected_triage_level": "EMERGENCY",
        "created_at": _now().isoformat(),
        "updated_at": _now().isoformat(),
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I can't breathe properly, I'm wheezing really badly", "action": None, "expected_intent": "symptom.emergency"},
            {"step_number": 3, "speaker": "system", "content": "I can hear you're having difficulty breathing. This is being treated as an emergency.", "action": "triage_assess", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "An ALS ambulance has been dispatched. ETA: 4 minutes. Stay calm and try to breathe slowly.", "action": "dispatch_ambulance", "expected_intent": None},
        ],
    },
    "urgent-fever": {
        "id": "urgent-fever",
        "name": "Urgent - High Fever",
        "description": "Patient with high fever (103°F) persisting for 3 days with body aches.",
        "category": "urgent",
        "language": "en-US",
        "expected_triage_level": "URGENT",
        "created_at": _now().isoformat(),
        "updated_at": _now().isoformat(),
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I've had a very high fever for three days now and my whole body aches", "action": None, "expected_intent": "symptom.urgent"},
            {"step_number": 3, "speaker": "system", "content": "A persistent high fever for 3 days is concerning. Let me assess your condition.", "action": "triage_assess", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "This is classified as URGENT. I recommend visiting our Urgent Care center. Would you like me to book an appointment within the next 2 hours?", "action": "recommend_urgent_care", "expected_intent": None},
        ],
    },
    "routine-appointment": {
        "id": "routine-appointment",
        "name": "Routine - Appointment Booking",
        "description": "Patient wants to schedule a routine check-up appointment with their doctor.",
        "category": "routine",
        "language": "en-US",
        "expected_triage_level": "ROUTINE",
        "created_at": _now().isoformat(),
        "updated_at": _now().isoformat(),
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I'd like to book a check-up appointment with Dr. Smith", "action": None, "expected_intent": "appointment.booking"},
            {"step_number": 3, "speaker": "system", "content": "I'd be happy to help you schedule an appointment with Dr. Smith. Let me check available slots.", "action": "check_availability", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "Dr. Smith has openings on Monday at 10:00 AM and Wednesday at 2:30 PM. Which works better for you?", "action": "offer_slots", "expected_intent": None},
            {"step_number": 5, "speaker": "patient", "content": "Monday at 10 AM works for me", "action": None, "expected_intent": "appointment.confirm"},
            {"step_number": 6, "speaker": "system", "content": "Your appointment with Dr. Smith is confirmed for Monday at 10:00 AM. You'll receive an SMS confirmation shortly. Is there anything else I can help with?", "action": "confirm_booking", "expected_intent": None},
        ],
    },
    "routine-prescription": {
        "id": "routine-prescription",
        "name": "Routine - Prescription Refill",
        "description": "Patient calling to request a prescription refill for ongoing medication.",
        "category": "routine",
        "language": "en-US",
        "expected_triage_level": "ROUTINE",
        "created_at": _now().isoformat(),
        "updated_at": _now().isoformat(),
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I need to refill my blood pressure medication, Lisinopril", "action": None, "expected_intent": "prescription.refill"},
            {"step_number": 3, "speaker": "system", "content": "I can help with your Lisinopril refill. Let me verify your information and check with the pharmacy.", "action": "verify_patient", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "Your refill has been submitted. It will be ready for pickup at the City Hospital pharmacy within 2 hours. You'll receive an SMS when it's ready.", "action": "submit_refill", "expected_intent": None},
        ],
    },
    "billing-inquiry": {
        "id": "billing-inquiry",
        "name": "Billing - Account Inquiry",
        "description": "Patient calling about a billing question regarding a recent hospital visit.",
        "category": "billing",
        "language": "en-US",
        "expected_triage_level": None,
        "created_at": _now().isoformat(),
        "updated_at": _now().isoformat(),
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I have a question about my hospital bill from last month", "action": None, "expected_intent": "billing.inquiry"},
            {"step_number": 3, "speaker": "system", "content": "I can help with billing questions. Let me transfer you to our billing department. One moment please.", "action": "transfer_billing", "expected_intent": None},
        ],
    },
}


# ── Ambulance Fleet ──────────────────────────────────────────────────────

AMBULANCES: dict[str, dict] = {
    "AMB-001": {"id": "AMB-001", "location": {"lat": 40.7580, "lon": -73.9855}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.ALS, "crew_size": 3, "last_updated": _now().isoformat()},
    "AMB-002": {"id": "AMB-002", "location": {"lat": 40.7282, "lon": -73.7949}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.BLS, "crew_size": 2, "last_updated": _now().isoformat()},
    "AMB-003": {"id": "AMB-003", "location": {"lat": 40.6892, "lon": -74.0445}, "status": AmbulanceStatus.DISPATCHED, "type": AmbulanceType.ALS, "crew_size": 3, "last_updated": _now().isoformat()},
    "AMB-004": {"id": "AMB-004", "location": {"lat": 40.7484, "lon": -73.9857}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.BLS, "crew_size": 2, "last_updated": _now().isoformat()},
    "AMB-005": {"id": "AMB-005", "location": {"lat": 40.7614, "lon": -73.9776}, "status": AmbulanceStatus.EN_ROUTE, "type": AmbulanceType.ALS, "crew_size": 3, "last_updated": _now().isoformat()},
    "AMB-006": {"id": "AMB-006", "location": {"lat": 40.7831, "lon": -73.9712}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.BLS, "crew_size": 2, "last_updated": _now().isoformat()},
    "AMB-007": {"id": "AMB-007", "location": {"lat": 40.7128, "lon": -74.0060}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.ALS, "crew_size": 3, "last_updated": _now().isoformat()},
    "AMB-008": {"id": "AMB-008", "location": {"lat": 40.7589, "lon": -73.9851}, "status": AmbulanceStatus.AT_HOSPITAL, "type": AmbulanceType.BLS, "crew_size": 2, "last_updated": _now().isoformat()},
    "AMB-009": {"id": "AMB-009", "location": {"lat": 40.7061, "lon": -74.0087}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.ALS, "crew_size": 3, "last_updated": _now().isoformat()},
    "AMB-010": {"id": "AMB-010", "location": {"lat": 40.7527, "lon": -73.9772}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.BLS, "crew_size": 2, "last_updated": _now().isoformat()},
    "AMB-011": {"id": "AMB-011", "location": {"lat": 40.7411, "lon": -74.0018}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.ALS, "crew_size": 3, "last_updated": _now().isoformat()},
    "AMB-012": {"id": "AMB-012", "location": {"lat": 40.7681, "lon": -73.9819}, "status": AmbulanceStatus.DISPATCHED, "type": AmbulanceType.BLS, "crew_size": 2, "last_updated": _now().isoformat()},
}


# ── Hospital Resources ───────────────────────────────────────────────────

RESOURCES: dict = {
    "emergency_room": {"total": 10, "available": 4, "staffed": 4},
    "urgent_care":    {"total": 8,  "available": 6, "staffed": 6},
    "general_ward":   {"total": 50, "available": 22, "staffed": 22},
    "queue_length": 8,
}


# ── Active Calls ─────────────────────────────────────────────────────────

ACTIVE_CALLS: dict[str, dict] = {}


# ── Call History (completed) ─────────────────────────────────────────────

CALL_HISTORY: list[dict] = []


# ── Analytics Counters ───────────────────────────────────────────────────

ANALYTICS: dict = {
    "total_calls": 0,
    "emergency_calls": 0,
    "routine_calls": 0,
    "total_dispatches": 0,
    "total_response_time_ms": 0,
    "total_duration_seconds": 0.0,
    "total_solver_time_ms": 0,
    "triage_correct": 0,
    "total_eta_minutes": 0.0,
}


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
