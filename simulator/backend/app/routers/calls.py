"""
Call simulation endpoints — start, interact with, and end simulated IVR calls.
"""

from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from app.models import (
    CallStartRequest, CallStartResponse, CallInputRequest, CallInputResponse,
    CallStatusResponse, CallEndRequest, CallSummary,
    CallStatus, TriageLevel, NluResult, TriageResult, DispatchResult,
)
from app.database import SCENARIOS, ACTIVE_CALLS, CALL_HISTORY, ANALYTICS, _now
from app.services import nlu_engine, triage_engine, dispatch_engine

router = APIRouter(prefix="/api/calls", tags=["Call Simulation"])


@router.post("/start", status_code=201, summary="Start a new simulated call")
def start_call(body: CallStartRequest) -> CallStartResponse:
    """Initialize a new simulated IVR call session."""
    call_id = f"SIM-{uuid.uuid4().hex[:8].upper()}"
    now = _now()

    greeting = "Welcome to City Hospital. How can I help you today?"
    if body.scenario_id and body.scenario_id in SCENARIOS:
        scenario = SCENARIOS[body.scenario_id]
        if scenario["steps"]:
            greeting = scenario["steps"][0]["content"]

    session = {
        "call_session_id": call_id,
        "status": CallStatus.IN_PROGRESS,
        "scenario_id": body.scenario_id,
        "language": body.language,
        "caller_phone": body.caller_phone,
        "started_at": now,
        "current_step": 0,
        "transcript": [
            {"step": 0, "speaker": "system", "content": greeting, "timestamp": now.isoformat()}
        ],
        "triage_result": None,
        "dispatch_result": None,
    }
    ACTIVE_CALLS[call_id] = session
    ANALYTICS["total_calls"] += 1

    return CallStartResponse(
        call_session_id=call_id,
        status=CallStatus.IN_PROGRESS,
        greeting=greeting,
        timestamp=now,
    )


@router.post("/{call_id}/input", summary="Send user input to a call")
def process_input(call_id: str, body: CallInputRequest) -> CallInputResponse:
    """Process user input (text/voice) and return NLU + triage + dispatch results."""
    if call_id not in ACTIVE_CALLS:
        raise HTTPException(404, f"Call session '{call_id}' not found")

    session = ACTIVE_CALLS[call_id]
    if session["status"] != CallStatus.IN_PROGRESS:
        raise HTTPException(400, f"Call is not in progress (status: {session['status']})")

    now = _now()
    session["current_step"] += 1
    step = session["current_step"]

    # ── Record user input ────────────────────────────────────────────
    session["transcript"].append({
        "step": step, "speaker": "patient",
        "content": body.user_input, "timestamp": now.isoformat(),
    })

    # ── NLU Analysis ─────────────────────────────────────────────────
    nlu = nlu_engine.analyze(body.user_input, session["language"])
    nlu_result = NluResult(
        intent=nlu["intent"],
        confidence=nlu["confidence"],
        entities=nlu["entities"],
        sentiment=nlu["sentiment"],
        distress_score=nlu["distress_score"],
    )

    # ── Triage (if symptom-related intent) ───────────────────────────
    triage_res: TriageResult | None = None
    dispatch_res: DispatchResult | None = None

    if nlu["intent"].startswith("symptom."):
        symptoms = nlu["entities"].get("symptoms", [body.user_input])
        severity = nlu["entities"].get("severity_score", 5)
        if nlu["intent"] == "symptom.emergency":
            severity = max(severity, 8)
        elif nlu["intent"] == "symptom.urgent":
            severity = max(severity, 5)

        triage = triage_engine.assess(
            symptoms=symptoms,
            severity_score=severity,
            patient_age=45,
            patient_gender="unknown",
            medical_history=[],
        )
        triage_res = TriageResult(
            triage_level=triage["triage_level"],
            recommended_facility=triage["recommended_facility"],
            clinical_reasoning=triage["clinical_reasoning"],
            severity_score=triage["severity_score"],
            solver_time_ms=triage["solver_time_ms"],
        )
        session["triage_result"] = triage_res.model_dump()

        # ── Dispatch (if emergency) ──────────────────────────────────
        if triage["triage_level"] == TriageLevel.EMERGENCY:
            ANALYTICS["emergency_calls"] += 1
            disp = dispatch_engine.assign(
                patient_lat=40.7128, patient_lon=-74.0060,
                priority="critical",
                chief_complaint=", ".join(symptoms),
                estimated_severity=triage["severity_score"],
                ambulance_type_required="ALS",
            )
            if "error" not in disp:
                dispatch_res = DispatchResult(
                    assigned_ambulance=disp["assigned_ambulance"],
                    ambulance_type=disp["ambulance_type"],
                    eta_minutes=disp["eta_minutes"],
                    crew_size=disp["crew_size"],
                )
                session["dispatch_result"] = dispatch_res.model_dump()
                ANALYTICS["total_dispatches"] += 1
                ANALYTICS["total_eta_minutes"] += disp["eta_minutes"]
                ANALYTICS["total_solver_time_ms"] += disp.get("solver_time_ms", 0)
                ANALYTICS["triage_correct"] += 1
        else:
            ANALYTICS["routine_calls"] += 1

    # ── Build system response ────────────────────────────────────────
    system_response = _build_response(nlu["intent"], nlu_result, triage_res, dispatch_res)
    session["current_step"] += 1
    session["transcript"].append({
        "step": session["current_step"], "speaker": "system",
        "content": system_response, "timestamp": _now().isoformat(),
    })

    return CallInputResponse(
        step_number=step,
        transcript=body.user_input,
        nlu=nlu_result,
        triage=triage_res,
        dispatch=dispatch_res,
        system_response=system_response,
        call_status=session["status"],
    )


@router.get("/{call_id}/status", summary="Get call status")
def get_call_status(call_id: str) -> CallStatusResponse:
    """Return current status and transcript of a call."""
    if call_id not in ACTIVE_CALLS:
        raise HTTPException(404, f"Call session '{call_id}' not found")
    s = ACTIVE_CALLS[call_id]
    elapsed = (_now() - s["started_at"]).total_seconds()
    return CallStatusResponse(
        call_session_id=call_id,
        status=s["status"],
        current_step=s["current_step"],
        duration_seconds=round(elapsed, 1),
        transcript=s["transcript"],
        triage_result=s.get("triage_result"),
        dispatch_result=s.get("dispatch_result"),
    )


@router.post("/{call_id}/end", summary="End a simulated call")
def end_call(call_id: str, body: CallEndRequest) -> CallSummary:
    """Terminate a call session and get summary."""
    if call_id not in ACTIVE_CALLS:
        raise HTTPException(404, f"Call session '{call_id}' not found")
    s = ACTIVE_CALLS[call_id]
    s["status"] = CallStatus.COMPLETED
    elapsed = (_now() - s["started_at"]).total_seconds()

    triage_level = None
    if s.get("triage_result"):
        triage_level = s["triage_result"].get("triage_level")

    ambulance = None
    if s.get("dispatch_result"):
        ambulance = s["dispatch_result"].get("assigned_ambulance")

    summary = CallSummary(
        call_session_id=call_id,
        status=CallStatus.COMPLETED,
        total_steps=s["current_step"],
        duration_seconds=round(elapsed, 1),
        final_triage=triage_level,
        ambulance_assigned=ambulance,
        transcript=s["transcript"],
    )

    CALL_HISTORY.append(summary.model_dump())
    ANALYTICS["total_duration_seconds"] += elapsed
    del ACTIVE_CALLS[call_id]
    return summary


@router.get("", summary="List active calls")
def list_active_calls() -> list[dict]:
    """Return all currently active call sessions."""
    result = []
    now = _now()
    for cid, s in ACTIVE_CALLS.items():
        elapsed = (now - s["started_at"]).total_seconds()
        result.append({
            "call_session_id": cid,
            "status": s["status"],
            "current_step": s["current_step"],
            "duration_seconds": round(elapsed, 1),
            "scenario_id": s.get("scenario_id"),
        })
    return result


# ── Helper ───────────────────────────────────────────────────────────────

def _build_response(
    intent: str,
    nlu: NluResult,
    triage: TriageResult | None,
    dispatch: DispatchResult | None,
) -> str:
    if dispatch and dispatch.assigned_ambulance:
        return (
            f"This sounds like an emergency. I've classified this as {triage.triage_level.value} "
            f"(severity {triage.severity_score}/10). "
            f"An ambulance ({dispatch.assigned_ambulance}, {dispatch.ambulance_type.value}) "
            f"has been dispatched. Estimated arrival: {dispatch.eta_minutes} minutes. "
            f"Please stay on the line while I transfer you to the ER desk."
        )
    if triage:
        return (
            f"Based on your symptoms, I've assessed this as {triage.triage_level.value} "
            f"(severity {triage.severity_score}/10). "
            f"Recommendation: {triage.recommended_facility}. "
            f"Reasoning: {triage.clinical_reasoning}"
        )
    if intent == "appointment.booking":
        return "I'd be happy to help you schedule an appointment. Dr. Smith has openings on Monday at 10:00 AM and Wednesday at 2:30 PM. Which works better?"
    if intent == "appointment.confirm":
        return "Your appointment has been confirmed. You'll receive an SMS confirmation shortly. Is there anything else I can help with?"
    if intent == "appointment.cancel":
        return "I can help you cancel or reschedule your appointment. Let me look up your records. Could you confirm your name and date of birth?"
    if intent == "prescription.refill":
        return "I can process your prescription refill. Your refill request has been submitted to the pharmacy. It will be ready for pickup within 2 hours."
    if intent == "billing.inquiry":
        return "I'll transfer you to our billing department for assistance. One moment please."
    if intent == "general.greeting":
        return "Hello! Welcome to City Hospital. How can I help you today?"
    if intent == "general.help":
        return "I can help with: emergency symptom assessment, appointment booking, prescription refills, billing questions, and ambulance dispatch. What do you need?"
    if intent == "general.goodbye":
        return "Thank you for calling City Hospital. Take care and stay healthy!"
    return "I understand. Could you tell me more about how I can help you today?"
