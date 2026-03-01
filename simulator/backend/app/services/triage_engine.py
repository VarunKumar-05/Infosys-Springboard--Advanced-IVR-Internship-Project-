"""
Mock Triage ILP Engine — rule-based severity assessment that simulates
the behaviour of a SCIP-based Integer Linear Programming solver.
"""

from __future__ import annotations
import time
import random
from app.models import TriageLevel
from app.database import RESOURCES


# ── Clinical Rules ───────────────────────────────────────────────────────

_EMERGENCY_SYMPTOMS = {
    "chest pain", "heart attack", "stroke", "seizure", "unconscious",
    "difficulty breathing", "shortness of breath", "heavy bleeding",
    "severe bleeding", "choking", "anaphylaxis", "collapsed",
    "not breathing", "cardiac arrest", "heart palpitations",
    "wheezing", "chest tightness",
}

_URGENT_SYMPTOMS = {
    "high fever", "fever", "fracture", "broken bone", "deep cut",
    "bad headache", "migraine", "abdominal pain", "stomach pain",
    "dizziness", "fainting", "rash spreading", "burn", "sprain",
    "infected wound", "swelling", "vomiting", "dehydration",
    "numbness", "tingling",
}

_CARDIAC_RISK_FACTORS = {"hypertension", "diabetes", "smoking", "obesity",
                          "high cholesterol", "family history of heart disease"}


def assess(
    symptoms: list[str],
    severity_score: int,
    patient_age: int,
    patient_gender: str = "unknown",
    medical_history: list[str] | None = None,
    duration_minutes: int | None = None,
) -> dict:
    """Simulate ILP-based triage assessment.  Returns dict with full result."""
    start = time.perf_counter()
    medical_history = medical_history or []

    symptoms_lower = {s.lower() for s in symptoms}
    history_lower = {h.lower() for h in medical_history}

    risk_factors: list[str] = []
    constraints: list[str] = []

    # ── Rule evaluation ──────────────────────────────────────────────

    # 1. Symptom severity
    has_emergency_symptom = bool(symptoms_lower & _EMERGENCY_SYMPTOMS)
    has_urgent_symptom = bool(symptoms_lower & _URGENT_SYMPTOMS)

    # 2. Age-based risk
    if patient_age >= 50:
        risk_factors.append(f"Age {patient_age} (elevated cardiac risk)")
        constraints.append("age_risk_modifier: +1 severity")
    if patient_age <= 5:
        risk_factors.append(f"Pediatric patient (age {patient_age})")
        constraints.append("pediatric_priority: +2 severity")

    # 3. Cardiac risk assessment
    cardiac_history = history_lower & _CARDIAC_RISK_FACTORS
    if cardiac_history:
        risk_factors.extend([f"History: {h}" for h in cardiac_history])
        constraints.append(f"cardiac_risk_factors: {len(cardiac_history)} matched")

    # 4. Chest pain + male + age > 40 → always cardiac evaluation
    if "chest pain" in symptoms_lower and patient_age > 40:
        risk_factors.append("Chest pain in patient >40 → mandatory cardiac evaluation")
        constraints.append("HARD CONSTRAINT: chest_pain + age>40 → ER evaluation")
        has_emergency_symptom = True

    # 5. Duration modifier
    if duration_minutes and duration_minutes > 30 and has_emergency_symptom:
        risk_factors.append(f"Symptom duration {duration_minutes}min (>30min concerning)")
        constraints.append("duration_risk_modifier: prolonged symptoms")

    # ── ILP objective simulation ─────────────────────────────────────

    adjusted_severity = severity_score
    if has_emergency_symptom:
        adjusted_severity = max(adjusted_severity, 8)
    if cardiac_history and has_emergency_symptom:
        adjusted_severity = min(adjusted_severity + 1, 10)
    if patient_age >= 50 and has_emergency_symptom:
        adjusted_severity = min(adjusted_severity + 1, 10)

    # ── Determine triage level ───────────────────────────────────────

    if adjusted_severity >= 8 or has_emergency_symptom:
        triage_level = TriageLevel.EMERGENCY
        facility = "Emergency Room"
    elif adjusted_severity >= 5 or has_urgent_symptom:
        triage_level = TriageLevel.URGENT
        facility = "Urgent Care"
    else:
        triage_level = TriageLevel.ROUTINE
        facility = "General Appointment"

    # ── Resource constraint check ────────────────────────────────────

    if triage_level == TriageLevel.EMERGENCY:
        er = RESOURCES["emergency_room"]
        if er["available"] <= 0:
            constraints.append("RESOURCE CONSTRAINT: ER at capacity → divert to partner hospital")
            facility = "Partner Hospital ER (City General)"
        else:
            constraints.append(f"ER capacity: {er['available']}/{er['total']} beds available")
    elif triage_level == TriageLevel.URGENT:
        uc = RESOURCES["urgent_care"]
        constraints.append(f"Urgent Care capacity: {uc['available']}/{uc['total']} slots")

    # ── Build clinical reasoning ─────────────────────────────────────

    symptom_str = ", ".join(symptoms)
    reasoning_parts = [f"Symptoms reported: {symptom_str}."]
    if risk_factors:
        reasoning_parts.append(f"Risk factors: {'; '.join(risk_factors)}.")
    reasoning_parts.append(
        f"Adjusted severity: {adjusted_severity}/10 → {triage_level.value}."
    )
    reasoning_parts.append(f"Recommended: {facility}.")
    reasoning = " ".join(reasoning_parts)

    solver_ms = int((time.perf_counter() - start) * 1000) + random.randint(250, 450)

    return {
        "triage_level": triage_level,
        "recommended_facility": facility,
        "clinical_reasoning": reasoning,
        "severity_score": adjusted_severity,
        "risk_factors": risk_factors,
        "constraints_applied": constraints,
        "solver_time_ms": solver_ms,
    }
