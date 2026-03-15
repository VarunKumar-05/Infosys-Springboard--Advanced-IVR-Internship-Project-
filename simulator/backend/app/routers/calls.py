"""
Call simulation endpoints — start, interact with, and end simulated IVR calls.
"""

from __future__ import annotations
import asyncio
import json
import os
import uuid
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from app.models import (
    CallStartRequest, CallStartResponse, CallInputRequest, CallInputResponse,
    CallStatusResponse, CallEndRequest, CallSummary,
    CallStatus, TriageLevel, NluResult, TriageResult, DispatchResult,
)
from app.database import (
    SCENARIOS, ACTIVE_CALLS, CALL_HISTORY, ANALYTICS, _now,
    lookup_patient_by_phone, create_patient
)
from app.services import nlu_engine, triage_engine, dispatch_engine

router = APIRouter(prefix="/api/calls", tags=["Call Simulation"])


@router.post("/start", status_code=201, summary="Start a new simulated call")
def start_call(body: CallStartRequest) -> CallStartResponse:
    """Initialize a new simulated IVR call session."""
    call_id = f"SIM-{uuid.uuid4().hex[:8].upper()}"
    now = _now()

    greeting = "Welcome to City Hospital. How can I help you today?"
    
    # Handle patient lookup/registration
    patient = None
    if body.caller_phone:
        patient = lookup_patient_by_phone(body.caller_phone)
        if not patient:
            patient_id = f"PAT-{uuid.uuid4().hex[:4].upper()}"
            new_patient_data = {
                "name": "Unknown",
                "phone": body.caller_phone,
                "age": 0,
                "gender": "unknown",
                "allergies": [],
                "medical_history": [],
            }
            patient = create_patient(patient_id, new_patient_data)
            greeting = "Welcome to City Hospital. I see you are calling for the first time. May I have your name, or how can I help you today?"
        else:
            patient_name = patient.get("name", "there")
            if patient_name == "Unknown":
                greeting = "Welcome back to City Hospital. How can I help you today?"
            else:
                greeting = f"Welcome back to City Hospital, {patient_name}. How can I help you today?"

    if body.scenario_id and body.scenario_id in SCENARIOS:
        scenario = SCENARIOS[body.scenario_id]
        if scenario.get("steps"):
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
async def process_input(call_id: str, body: CallInputRequest) -> CallInputResponse:
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

    triage_res: TriageResult | None = None
    dispatch_res: DispatchResult | None = None
    actions_list: list[dict] = []

    # ── Try Gemini Orchestration (real-time AI brain) ────────────────
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        # Build conversation history from session transcript
        conversation_history = []
        for entry in session["transcript"][:-1]:  # exclude current input
            role = "user" if entry["speaker"] == "patient" else "assistant"
            conversation_history.append({"role": role, "content": entry["content"]})

        orch = await nlu_engine.orchestrate_conversation(
            body.user_input, conversation_history, call_id,
        )
        system_response = orch["response_text"]
        actions_list = orch.get("actions", [])

        # Extract triage/dispatch from orchestration if available
        if orch.get("triage"):
            t = orch["triage"]
            triage_res = TriageResult(
                triage_level=t.get("triage_level", "ROUTINE"),
                recommended_facility=t.get("recommended_facility", ""),
                clinical_reasoning=t.get("clinical_reasoning", ""),
                severity_score=t.get("severity_score", 5),
                solver_time_ms=t.get("solver_time_ms", 0),
            )
            session["triage_result"] = triage_res.model_dump()

        if orch.get("dispatch"):
            d = orch["dispatch"]
            dispatch_res = DispatchResult(
                assigned_ambulance=d.get("assigned_ambulance", ""),
                ambulance_type=d.get("ambulance_type", "BLS"),
                eta_minutes=d.get("eta_minutes", 0),
                crew_size=d.get("crew_size", 2),
            )
            session["dispatch_result"] = dispatch_res.model_dump()
            ANALYTICS["total_dispatches"] += 1
            ANALYTICS["total_eta_minutes"] += d.get("eta_minutes", 0)
            ANALYTICS["total_solver_time_ms"] += d.get("solver_time_ms", 0)

        # Track actions for analytics
        for action in orch.get("actions", []):
            if action["tool"] == "dispatch_ambulance":
                ANALYTICS["emergency_calls"] += 1
            elif action["tool"] == "book_appointment":
                ANALYTICS["routine_calls"] += 1
    else:
        # ── Fallback: BoW NLU + rule-based triage/dispatch ───────────
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

        system_response = _build_response(nlu["intent"], nlu_result, triage_res, dispatch_res)

    # ── Record system response ───────────────────────────────────────
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
        actions=actions_list,
        response_text=system_response,
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


# ── WebSocket Voice Sessions ─────────────────────────────────────────────

VOICE_SESSIONS: dict[str, dict] = {}


@router.websocket("/ws/{call_id}")
async def voice_call_websocket(websocket: WebSocket, call_id: str, phone: str = "", scenario_id: str = ""):
    """
    Bidirectional voice-to-voice WebSocket endpoint.

    Protocol
    --------
    Client → Server:
      - binary  : raw audio bytes (full recording from MediaRecorder)
      - JSON    : {"type": "audio_end"}   → triggers STT + orchestration
      - JSON    : {"type": "text_input", "text": "..."}  → text fallback
      - JSON    : {"type": "end_call"}    → graceful hangup

    Server → Client:
      - JSON    : {"type": "greeting",  "text": ..., "call_id": ...}
      - JSON    : {"type": "status",    "state": "listening"|"processing"|"speaking"}
      - JSON    : {"type": "transcript", "speaker": ..., "text": ...}
      - JSON    : {"type": "response",  "text": ..., "nlu": ..., ...}
      - binary  : mp3 audio of AI response
      - JSON    : {"type": "audio_end"} → client should play queued audio
      - JSON    : {"type": "error",     "message": ...}
    """
    await websocket.accept()

    now = _now()
    session = {
        "call_id": call_id,
        "conversation_history": [],
        "transcript": [],
        "started_at": now,
        "triage_result": None,
        "dispatch_result": None,
    }
    VOICE_SESSIONS[call_id] = session

    # Register in ACTIVE_CALLS for analytics / status endpoint
    ACTIVE_CALLS[call_id] = {
        "call_session_id": call_id,
        "status": CallStatus.IN_PROGRESS,
        "scenario_id": scenario_id or None,
        "language": "en-US",
        "caller_phone": phone,
        "started_at": now,
        "current_step": 0,
        "transcript": [],
        "triage_result": None,
        "dispatch_result": None,
    }
    ANALYTICS["total_calls"] += 1

    try:
        # ── Greeting ─────────────────────────────────────────────────
        greeting = "Welcome to City Hospital. How can I help you today?"
        
        # Handle patient lookup/registration
        patient = None
        if phone:
            patient = lookup_patient_by_phone(phone)
            if not patient:
                patient_id = f"PAT-{uuid.uuid4().hex[:4].upper()}"
                new_patient_data = {
                    "name": "Unknown",
                    "phone": phone,
                    "age": 0,
                    "gender": "unknown",
                    "allergies": [],
                    "medical_history": [],
                }
                patient = create_patient(patient_id, new_patient_data)
                greeting = "Welcome to City Hospital. I see you are calling for the first time. May I have your name, or how can I help you today?"
            else:
                patient_name = patient.get("name", "there")
                if patient_name == "Unknown":
                    greeting = "Welcome back to City Hospital. How can I help you today?"
                else:
                    greeting = f"Welcome back to City Hospital, {patient_name}. How can I help you today?"

        if scenario_id and scenario_id in SCENARIOS:
            scenario = SCENARIOS[scenario_id]
            if scenario.get("steps"):
                greeting = scenario["steps"][0]["content"]

        session["conversation_history"].append({"role": "assistant", "content": greeting})
        session["transcript"].append(
            {"speaker": "system", "content": greeting, "timestamp": now.isoformat()}
        )

        await websocket.send_json(
            {"type": "greeting", "text": greeting, "call_id": call_id}
        )

        # Synthesize greeting audio
        try:
            from app.routers.tts import synthesize_speech
            audio_bytes = await synthesize_speech(greeting)
            if audio_bytes:  # only send if TTS actually produced audio
                await websocket.send_bytes(audio_bytes)
            await websocket.send_json({"type": "audio_end"})
        except Exception as e:
            await websocket.send_json({"type": "audio_end", "tts_error": str(e)})

        await websocket.send_json({"type": "status", "state": "listening"})

        # ── Main conversation loop ───────────────────────────────────
        audio_buffer = bytearray()

        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            # Binary audio data — accumulate
            if "bytes" in message and message["bytes"]:
                audio_buffer.extend(message["bytes"])
                continue

            # JSON control messages
            if "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue

                if data.get("type") == "end_call":
                    break

                user_text: str | None = None

                if data.get("type") == "audio_end" and audio_buffer:
                    # ── STT ───────────────────────────────────────────
                    await websocket.send_json({"type": "status", "state": "processing"})

                    from app.routers.stt import transcribe_audio_bytes
                    user_text = await transcribe_audio_bytes(bytes(audio_buffer))
                    audio_buffer.clear()

                    if not user_text:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Could not transcribe audio. Please try again.",
                        })
                        await websocket.send_json({"type": "status", "state": "listening"})
                        continue

                elif data.get("type") == "text_input":
                    user_text = (data.get("text") or "").strip()
                    if not user_text:
                        continue
                    await websocket.send_json({"type": "status", "state": "processing"})

                elif data.get("type") == "audio_end":
                    # audio_end with empty buffer — nothing to process
                    await websocket.send_json({"type": "status", "state": "listening"})
                    continue

                else:
                    continue

                # ── Process user text (shared path) ──────────────────
                session["transcript"].append({
                    "speaker": "patient",
                    "content": user_text,
                    "timestamp": _now().isoformat(),
                })
                session["conversation_history"].append({"role": "user", "content": user_text})

                await websocket.send_json({
                    "type": "transcript", "speaker": "patient", "text": user_text,
                })

                # ── Orchestrate ──────────────────────────────────────
                result = await nlu_engine.orchestrate_conversation(
                    user_text=user_text,
                    conversation_history=session["conversation_history"],
                    call_id=call_id,
                )

                response_text = result["response_text"]
                session["conversation_history"].append({"role": "assistant", "content": response_text})
                session["transcript"].append({
                    "speaker": "system",
                    "content": response_text,
                    "timestamp": _now().isoformat(),
                })

                if result.get("triage"):
                    session["triage_result"] = result["triage"]
                if result.get("dispatch"):
                    session["dispatch_result"] = result["dispatch"]

                # Send response metadata
                await websocket.send_json({
                    "type": "response",
                    "text": response_text,
                    "nlu": result.get("nlu"),
                    "triage": result.get("triage"),
                    "dispatch": result.get("dispatch"),
                    "actions": [a["tool"] for a in result.get("actions", [])],
                })

                # ── TTS ──────────────────────────────────────────────
                await websocket.send_json({"type": "status", "state": "speaking"})
                try:
                    from app.routers.tts import synthesize_speech
                    audio = await synthesize_speech(response_text)
                    if audio:  # only send if TTS actually produced audio
                        await websocket.send_bytes(audio)
                except Exception as e:
                    await websocket.send_json({"type": "tts_error", "message": str(e)})

                await websocket.send_json({"type": "audio_end"})
                await websocket.send_json({"type": "status", "state": "listening"})

    except WebSocketDisconnect:
        pass
    finally:
        # ── Cleanup & persist ────────────────────────────────────────
        elapsed = (_now() - session["started_at"]).total_seconds()
        ANALYTICS["total_duration_seconds"] += elapsed

        if call_id in ACTIVE_CALLS:
            ACTIVE_CALLS[call_id]["status"] = CallStatus.COMPLETED
            CALL_HISTORY.append({
                "call_session_id": call_id,
                "status": "completed",
                "duration_seconds": round(elapsed, 1),
                "transcript": session["transcript"],
                "triage_result": session.get("triage_result"),
                "dispatch_result": session.get("dispatch_result"),
            })
            del ACTIVE_CALLS[call_id]

        VOICE_SESSIONS.pop(call_id, None)


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
