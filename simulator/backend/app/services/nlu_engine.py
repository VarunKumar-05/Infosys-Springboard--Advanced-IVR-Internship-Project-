"""
NLU Engine — Bag of Words (BoW) intent detection, entity extraction,
LLM inference (Google Gemini), and LLM orchestration with
Function Calling / Tools for the IVR simulator.
"""

from __future__ import annotations
import asyncio
import json
import re
import time
import os
import random
from typing import Dict, Any, Tuple
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Google Gemini SDK
try:
    from google import genai
    from google.genai import types as genai_types
    has_gemini = True
except ImportError:
    has_gemini = False

try:
    from huggingface_hub import InferenceClient
    has_hf = True
except ImportError:
    has_hf = False

from app.models import Sentiment

# ── Intent keyword map (For Bag of Words) ──────────────────────────────────
_INTENT_MAP = [
    ("symptom.emergency", ["chest pain", "heart attack", "breathe", "stroke", "unconscious", "seizure", "bleeding", "choking", "anaphylaxis", "collapsed"]),
    ("symptom.urgent", ["fever", "vomiting", "broken bone", "fracture", "cut", "headache", "migraine", "abdominal", "stomach", "dizziness", "fainting", "rash", "burn", "sprain", "swelling"]),
    ("symptom.routine", ["cold", "cough", "throat", "runny", "fatigue", "tired", "insomnia", "bruise", "congestion"]),
    ("appointment.booking", ["book", "schedule", "make", "doctor", "check-up", "checkup", "follow", "visit", "available", "slots"]),
    ("appointment.cancel", ["cancel", "reschedule", "change", "move"]),
    ("appointment.confirm", ["works", "sounds", "yes", "confirm", "monday", "tuesday", "wednesday", "thursday", "friday", "morning", "afternoon"]),
    ("prescription.refill", ["refill", "prescription", "medication", "medicine", "renew"]),
    ("billing.inquiry", ["bill", "billing", "charge", "payment", "insurance", "cost", "price", "invoice", "statement", "balance"]),
    ("general.greeting", ["hello", "hi", "hey", "morning", "afternoon"]),
    ("general.help", ["help", "options", "menu", "services"]),
    ("general.goodbye", ["bye", "goodbye", "thank", "thanks", "nothing", "no"]),
]

_INTENTS = [item[0] for item in _INTENT_MAP]
_CORPUS = [" ".join(item[1]) for item in _INTENT_MAP]

# Initialize Bag of Words Vectorizer
vectorizer = CountVectorizer(stop_words='english')
X_bow = vectorizer.fit_transform(_CORPUS)

# ── Entity patterns ────────────────────────────────────────────────────────
_SYMPTOM_KEYWORDS = ["chest pain", "headache", "migraine", "fever", "cough", "nausea", "vomiting", "dizziness", "shortness of breath", "difficulty breathing", "abdominal pain", "back pain", "sore throat", "rash", "swelling", "bleeding", "fatigue", "wheezing", "numbness"]
_BODY_PARTS = ["chest", "head", "arm", "left arm", "right arm", "leg", "left leg", "right leg", "back", "neck", "stomach", "abdomen", "throat", "knee", "shoulder"]
_SEVERITY_MODIFIERS = {"really bad": 9, "severe": 9, "terrible": 9, "extreme": 10, "excruciating": 10, "bad": 7, "strong": 7, "intense": 8, "moderate": 5, "mild": 3, "slight": 2, "minor": 2}
_DISTRESS_WORDS = ["help", "please", "hurry", "dying", "scared", "afraid", "can't", "emergency", "desperate", "panic", "terrible", "unbearable"]

def _llm_inference(text: str) -> Dict[str, Any]:
    """Uses Google Gemini or HuggingFace inference for intent & entities."""
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if gemini_key and has_gemini:
        try:
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Patient says: {text}\nPredict the intent (appointment, emergency, symptom, billing, greeting, goodbye) and sentiment (positive, neutral, negative). Reply as JSON.",
                config=genai_types.GenerateContentConfig(temperature=0.3, max_output_tokens=100),
            )
            return {"llm_used": "gemini", "raw": response.text}
        except Exception as e:
            return {"llm_used": "gemini_error", "error": str(e)}

    # HuggingFace STT / Inference fallback model
    if hf_token and has_hf:
        try:
            client = InferenceClient(token=hf_token)
            # Use inference to query a hosted model on HuggingFace for sentiment/intent
            res = client.text_generation(prompt=f"Patient says: {text}\nAnalyze intent:", max_new_tokens=20)
            return {"llm_used": "huggingface", "raw": res}
        except Exception as e:
            return {"llm_used": "hf_error", "error": str(e)}

    return {"llm_used": "none"}

def analyze(text: str, language: str = "en-US") -> dict:
    start = time.perf_counter()
    lower = text.lower().strip()

    # Intent detection using Bag of Words (Cosine Similarity)
    user_bow = vectorizer.transform([lower])
    similarities = cosine_similarity(user_bow, X_bow).flatten()
    best_idx = np.argmax(similarities)
    best_score = similarities[best_idx]
    
    if best_score > 0.05:
        intent = _INTENTS[best_idx]
        confidence = float(min(best_score + 0.3, 0.95))
    else:
        intent = "general.unknown"
        confidence = 0.35

    entities = _extract_entities(lower)
    sentiment, distress = _analyze_sentiment(lower)
    llm_data = _llm_inference(text)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    if llm_data.get("llm_used") not in ["none", "hf_error", "gemini_error"]:
        entities["llm_metadata"] = llm_data

    return {
        "transcript": text,
        "intent": intent,
        "confidence": round(confidence, 2),
        "entities": entities,
        "sentiment": sentiment,
        "distress_score": round(distress, 2),
        "language": language,
        "processing_time_ms": elapsed_ms,
    }

def _extract_entities(text: str) -> dict:
    entities: dict = {}
    found_symptoms = [s for s in _SYMPTOM_KEYWORDS if s in text]
    if found_symptoms: entities["symptoms"] = found_symptoms
    found_parts = [p for p in _BODY_PARTS if p in text]
    if found_parts: entities["body_parts"] = found_parts
    for modifier, score in _SEVERITY_MODIFIERS.items():
        if modifier in text:
            entities["severity_modifier"] = modifier
            entities["severity_score"] = score
            break
            
    # Duration (simple pattern)
    dur_match = re.search(r"(\d+)\s*(hour|hr|minute|min|day|week|month)", text) 
    if dur_match:
        entities["duration"] = f"{dur_match.group(1)} {dur_match.group(2)}s"    

    # Doctor name
    dr_match = re.search(r"(?:dr\.?|doctor)\s+([a-zA-Z]+)", text)
    if dr_match:
        entities["doctor_name"] = f"Dr. {dr_match.group(1).title()}"
        
    return entities

def _analyze_sentiment(text: str) -> tuple[str, float]:
    distress_count = sum(1 for w in _DISTRESS_WORDS if w in text)
    negative_signal = any(kw in text for kw in ["pain", "hurt", "bad", "worse", "terrible", "scared", "bleeding", "can't", "emergency", "severe", "dying"])
    positive_signal = any(kw in text for kw in ["thank", "good", "great", "fine", "okay", "happy", "better"])

    if distress_count >= 2 or (negative_signal and distress_count >= 1):
        return Sentiment.NEGATIVE, min(0.5 + distress_count * 0.15, 1.0)
    elif negative_signal:
        return Sentiment.NEGATIVE, 0.55
    elif positive_signal:
        return Sentiment.POSITIVE, 0.15
    else:
        return Sentiment.NEUTRAL, 0.25


# ═══════════════════════════════════════════════════════════════════════════
# LLM Orchestration with Function Calling / Tools
# ═══════════════════════════════════════════════════════════════════════════
#
# Required API key (set in .env or environment):
#   GEMINI_API_KEY — for Google Gemini — the primary LLM brain
#

SYSTEM_PROMPT = """You are an AI medical assistant for City Hospital's IVR (Interactive Voice Response) system.

Your role:
1. Greet callers warmly and ask how you can help
2. Listen to symptoms and medical concerns carefully
3. Assess severity and recommend appropriate care
4. For emergencies (severe chest pain, difficulty breathing, stroke symptoms,
   severe bleeding, unconsciousness), IMMEDIATELY dispatch an ambulance
5. Book appointments for non-emergency situations — route to the correct specialist
6. Always take action using tools — do NOT just talk about what you could do

CRITICAL RULES — ALWAYS FOLLOW:
- If a patient says they are a new caller or their name is unknown, kindly ask for their name early in the conversation, then use update_patient_record to save it. 
- When a patient describes a non-emergency medical concern AND requests an appointment,
  IMMEDIATELY call book_appointment. Do NOT ask for their name first — use 'Unknown'
  as patient_name if they haven't given it. Do NOT ask about severity for booking.
  Pick a reasonable date/time if they haven't specified one (e.g. 'Tomorrow', '10:00 AM').
- When a patient describes EMERGENCY symptoms (severe chest pain, can't breathe, stroke,
  heavy bleeding, unconscious), IMMEDIATELY call dispatch_ambulance with severity >= 8.
  Do NOT ask questions first — act immediately.
- When asked to confirm or book, ALWAYS call the tool. Never just say "I'll book that"
  without actually calling book_appointment.
- Be empathetic, professional, and concise (responses are spoken aloud via TTS).
- Keep responses under 3 sentences.
- Never diagnose — only triage and route.

ROUTING — which doctor for which condition:
- Chest discomfort / chest pain (mild-moderate) / heart palpitations / blood pressure → Cardiology: Dr. Patel or Dr. Gupta
- Child / infant / pediatric concerns → Pediatrics: Dr. Lee or Dr. Martinez
- Pregnancy / prenatal / periods / pelvic pain → Gynaecology: Dr. Robinson or Dr. Chen
- General complaints (cough, back pain, fatigue, cold, allergies, headache) → General Medicine: Dr. Smith or Dr. Johnson

TOOL USAGE:
- book_appointment: Use for ALL non-emergency appointment requests. Required: doctor_name, department, date, time, reason. Optional: patient_name (default 'Unknown').
- dispatch_ambulance: Use ONLY for life-threatening emergencies (severity >= 8).
- query_patient_history: Use to look up existing records by name/phone/symptoms.
- update_patient_record: Use to log call notes and new symptoms.
"""

ORCHESTRATION_TOOLS = [
    genai_types.Tool(function_declarations=[
        genai_types.FunctionDeclaration(
            name="query_patient_history",
            description=(
                "Search the hospital database for patient records. "
                "Can search by symptoms/conditions in medical history, "
                "patient name, or phone number."
            ),
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={
                    "symptoms": genai_types.Schema(
                        type="ARRAY",
                        items=genai_types.Schema(type="STRING"),
                        description="Conditions/symptoms to match in patient history",
                    ),
                    "patient_name": genai_types.Schema(
                        type="STRING",
                        description="Patient name to look up",
                    ),
                    "phone": genai_types.Schema(
                        type="STRING",
                        description="Phone number to search",
                    ),
                },
            ),
        ),
        genai_types.FunctionDeclaration(
            name="update_patient_record",
            description=(
                "Update an existing patient record with new symptoms, "
                "notes, caller's name, or call information. Creates a timestamped entry."
            ),
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={
                    "patient_id": genai_types.Schema(
                        type="STRING",
                        description="Patient ID (e.g. PAT-001). Use 'NEW' if unknown.",
                    ),
                    "name": genai_types.Schema(
                        type="STRING",
                        description="The caller's full name, if they provided it during the call.",
                    ),
                    "new_symptoms": genai_types.Schema(
                        type="ARRAY",
                        items=genai_types.Schema(type="STRING"),
                        description="New symptoms to add to the patient record",
                    ),
                    "notes": genai_types.Schema(
                        type="STRING",
                        description="Call notes to add to the record",
                    ),
                },
                required=["notes"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="dispatch_ambulance",
            description=(
                "Dispatch an ambulance for a medical emergency. "
                "Use ONLY for severe, life-threatening situations (severity >= 8)."
            ),
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={
                    "chief_complaint": genai_types.Schema(
                        type="STRING",
                        description="Primary complaint / reason for dispatch",
                    ),
                    "severity": genai_types.Schema(
                        type="INTEGER",
                        description="Severity score 1-10 (dispatch if >= 8)",
                    ),
                    "patient_location_lat": genai_types.Schema(
                        type="NUMBER",
                        description="Patient latitude (default 40.7128)",
                    ),
                    "patient_location_lon": genai_types.Schema(
                        type="NUMBER",
                        description="Patient longitude (default -74.0060)",
                    ),
                },
                required=["chief_complaint", "severity"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="book_appointment",
            description=(
                "Book a doctor appointment for the patient. Use this for ALL "
                "non-emergency appointment requests. Pick the right department "
                "and doctor based on the patient's condition."
            ),
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={
                    "patient_name": genai_types.Schema(
                        type="STRING",
                        description="Patient name (or 'Unknown' if not provided)",
                    ),
                    "doctor_name": genai_types.Schema(
                        type="STRING",
                        description="Doctor name (e.g. 'Dr. Patel')",
                    ),
                    "department": genai_types.Schema(
                        type="STRING",
                        description="Department: Cardiology, Pediatrics, Gynaecology, or General Medicine",
                    ),
                    "date": genai_types.Schema(
                        type="STRING",
                        description="Appointment date (e.g. 'Monday', '2026-03-16')",
                    ),
                    "time": genai_types.Schema(
                        type="STRING",
                        description="Appointment time (e.g. '10:00 AM')",
                    ),
                    "reason": genai_types.Schema(
                        type="STRING",
                        description="Reason for appointment / chief complaint",
                    ),
                },
                required=["doctor_name", "department", "date", "time", "reason"],
            ),
        ),
    ])
] if has_gemini else []


def _execute_tool_call(name: str, arguments: dict, call_id: str) -> str:
    """Execute a tool call and return the result as a JSON string."""
    from app.database import (
        lookup_patient_by_symptoms, lookup_patient_by_name,
        lookup_patient_by_phone, update_patient_record, log_call_event,
        book_appointment,
    )
    from app.services import dispatch_engine, triage_engine

    if name == "query_patient_history":
        results = []
        if arguments.get("symptoms"):
            results.extend(lookup_patient_by_symptoms(arguments["symptoms"]))
        if arguments.get("patient_name"):
            results.extend(lookup_patient_by_name(arguments["patient_name"]))
        if arguments.get("phone"):
            patient = lookup_patient_by_phone(arguments["phone"])
            if patient:
                results.append(patient)
        if results:
            seen: set[str] = set()
            unique = []
            for r in results:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    unique.append(r)
            return json.dumps(unique, default=str)
        return json.dumps({"message": "No matching patient records found"})

    elif name == "update_patient_record":
        from app.database import lookup_patient_by_phone, ACTIVE_CALLS # needed for fallback lookup
        
        patient_id = arguments.get("patient_id", "NEW")
        name_arg = arguments.get("name")
        
        if patient_id == "NEW" or not patient_id:
            # Try to resolve patient_id from the active call session phone number
            session = ACTIVE_CALLS.get(call_id)
            if session and session.get("caller_phone"):
                patient = lookup_patient_by_phone(session["caller_phone"])
                if patient:
                    patient_id = patient["id"]

        new_symptoms = arguments.get("new_symptoms", [])
        notes = arguments.get("notes", "")
        
        if patient_id != "NEW":
            result = update_patient_record(patient_id, new_symptoms, notes, name=name_arg)
            if result:
                log_call_event(call_id, "record_updated", {
                    "patient_id": patient_id, "notes": notes, "name": name_arg
                })
                return json.dumps({"status": "updated", "patient_id": patient_id})
        log_call_event(call_id, "call_note", {"notes": notes, "symptoms": new_symptoms, "name": name_arg})
        return json.dumps({"status": "logged", "call_id": call_id})

    elif name == "dispatch_ambulance":
        complaint = arguments["chief_complaint"]
        severity = arguments["severity"]
        lat = arguments.get("patient_location_lat", 40.7128)
        lon = arguments.get("patient_location_lon", -74.0060)

        triage_result = triage_engine.assess(
            symptoms=[complaint], severity_score=severity, patient_age=45,
        )
        dispatch_result = dispatch_engine.assign(
            patient_lat=lat, patient_lon=lon,
            priority="critical" if severity >= 8 else "high",
            chief_complaint=complaint,
            estimated_severity=severity,
            ambulance_type_required="ALS" if severity >= 8 else "BLS",
        )
        log_call_event(call_id, "ambulance_dispatched", dispatch_result)
        return json.dumps({"triage": triage_result, "dispatch": dispatch_result}, default=str)

    elif name == "book_appointment":
        appointment = book_appointment(
            patient_name=arguments.get("patient_name", "Unknown"),
            doctor_name=arguments["doctor_name"],
            department=arguments["department"],
            date=arguments["date"],
            time=arguments["time"],
            reason=arguments["reason"],
        )
        log_call_event(call_id, "appointment_booked", appointment)
        return json.dumps(appointment, default=str)

    return json.dumps({"error": f"Unknown tool: {name}"})


def _run_llm_with_tools(messages: list[dict], call_id: str, system_instruction: str = SYSTEM_PROMPT) -> tuple[str, list[dict], dict | None, dict | None]:
    """Synchronous LLM call with iterative tool execution via Gemini.
    Returns (response_text, actions, triage_result, dispatch_result).
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not gemini_key:
        raise RuntimeError(
            "GEMINI_API_KEY not configured. "
            "Set it in .env to enable Gemini orchestration."
        )

    client = genai.Client(api_key=gemini_key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Convert OpenAI-style messages to Gemini contents
    contents: list[genai_types.Content] = []
    for msg in messages:
        role = msg["role"]
        if role == "system":
            continue  # system prompt handled via config
        gemini_role = "user" if role == "user" else "model"
        contents.append(genai_types.Content(
            role=gemini_role,
            parts=[genai_types.Part(text=msg["content"])],
        ))

    actions: list[dict] = []
    triage_result = None
    dispatch_result = None

    config = genai_types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=ORCHESTRATION_TOOLS,
        temperature=0.4,
        max_output_tokens=400,
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )

    # Iteratively process function calls (max 5 rounds)
    rounds = 0
    while rounds < 5:
        rounds += 1

        # Check for function calls in the response
        function_calls = []
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    function_calls.append(part)

        if not function_calls:
            break

        # Add the model's response to contents
        contents.append(response.candidates[0].content)

        # Execute each function call and build function response parts
        fn_response_parts = []
        for part in function_calls:
            fn_name = part.function_call.name
            fn_args = dict(part.function_call.args) if part.function_call.args else {}
            result_str = _execute_tool_call(fn_name, fn_args, call_id)
            actions.append({"tool": fn_name, "args": fn_args, "result": result_str})

            # Extract triage/dispatch for the UI
            if fn_name == "dispatch_ambulance":
                try:
                    result_data = json.loads(result_str)
                    triage_result = result_data.get("triage")
                    dispatch_result = result_data.get("dispatch")
                except Exception:
                    pass

            fn_response_parts.append(genai_types.Part(
                function_response=genai_types.FunctionResponse(
                    name=fn_name,
                    response=json.loads(result_str),
                ),
            ))

        contents.append(genai_types.Content(
            role="user",
            parts=fn_response_parts,
        ))

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

    response_text = ""
    if response.candidates and response.candidates[0].content:
        for part in response.candidates[0].content.parts:
            if part.text:
                response_text += part.text
    if not response_text:
        # Provide meaningful fallback based on what tools were called
        if any(a["tool"] == "dispatch_ambulance" for a in actions):
            response_text = "An ambulance has been dispatched to your location immediately. Please stay on the line and remain calm. Help is on the way."
        elif any(a["tool"] == "book_appointment" for a in actions):
            response_text = "Your appointment has been booked successfully. Is there anything else I can help with?"
        else:
            response_text = "I understand. How can I help you further?"

    return response_text, actions, triage_result, dispatch_result


def _generate_fallback_response(nlu_result: dict, call_id: str) -> str:
    """Generate response using BoW NLU when no LLM API key is available."""
    intent = nlu_result["intent"]

    if intent == "symptom.emergency":
        from app.services import dispatch_engine, triage_engine
        from app.database import log_call_event
        symptoms = nlu_result["entities"].get("symptoms", ["unknown emergency"])
        triage_engine.assess(symptoms=symptoms, severity_score=9, patient_age=45)
        dispatch = dispatch_engine.assign(
            patient_lat=40.7128, patient_lon=-74.0060,
            priority="critical", chief_complaint=", ".join(symptoms),
            estimated_severity=9, ambulance_type_required="ALS",
        )
        log_call_event(call_id, "emergency_dispatch", dispatch)
        if "error" not in dispatch:
            return (
                f"This is being treated as an EMERGENCY. "
                f"Ambulance {dispatch['assigned_ambulance']} "
                f"({dispatch['ambulance_type'].value}) has been dispatched. "
                f"ETA: {dispatch['eta_minutes']} minutes. Please stay on the line."
            )
        return "This is an emergency. All ambulances are currently deployed. Please call 911 immediately."

    if intent == "symptom.urgent":
        return ("Your symptoms sound urgent. I recommend visiting our "
                "Urgent Care center as soon as possible. Would you like me to check availability?")
    if intent == "symptom.routine":
        return ("Your symptoms sound like they can be addressed in a routine appointment. "
                "Would you like me to schedule one for you?")
    if intent == "appointment.booking":
        return ("I'd be happy to help schedule an appointment. Dr. Smith has openings "
                "on Monday at 10 AM and Wednesday at 2:30 PM. Which works better?")
    if intent == "appointment.confirm":
        return "Your appointment has been confirmed. You'll receive an SMS confirmation shortly."
    if intent == "prescription.refill":
        return "I can process your prescription refill. Your request has been submitted to the pharmacy."
    if intent == "billing.inquiry":
        return "I'll transfer you to our billing department for assistance. One moment please."
    if intent == "general.greeting":
        return "Hello! Welcome to City Hospital. How can I help you today?"
    if intent == "general.goodbye":
        return "Thank you for calling City Hospital. Take care!"
    return "I understand. Could you tell me more about how I can help you today?"


async def orchestrate_conversation(
    user_text: str,
    conversation_history: list[dict],
    call_id: str,
) -> dict:
    """
    Main orchestration function — runs BoW NLU as baseline, then attempts
    LLM function-calling orchestration.  Falls back to BoW when no API key.

    Returns dict with: response_text, nlu, actions, triage, dispatch
    """
    # Always run BoW NLU as baseline analysis
    nlu_result = analyze(user_text)

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not gemini_key or not has_gemini:
        # No Gemini key → use BoW fallback responses
        return {
            "response_text": _generate_fallback_response(nlu_result, call_id),
            "nlu": nlu_result,
            "actions": [],
            "triage": None,
            "dispatch": None,
        }

    # Inject detected scenario from BoW NLU or session into system prompt
    system_instruction = SYSTEM_PROMPT
    intent = nlu_result.get("intent")
    if intent and intent != "general.unknown":
        system_instruction += (
            f"\n\nKNOWN SCENARIO CONTEXT (Detected via NLU):\n"
            f"The patient's current situation is primarily categorized as: {intent}.\n"
            f"Use this context to anticipate their needs, optimize tool usage, and respond faster."
        )

    # Bring in call scenario description if available
    try:
        from app.database import ACTIVE_CALLS, SCENARIOS
        call_scenario_id = ACTIVE_CALLS.get(call_id, {}).get("scenario_id")
        if call_scenario_id and call_scenario_id in SCENARIOS:
            scenario_desc = SCENARIOS[call_scenario_id].get("description", "")
            if scenario_desc:
                system_instruction += (
                    f"\n\nKNOWN CALL SCENARIO:\n{scenario_desc}\n"
                    f"Use this scenario context for faster state inference."
                )
    except Exception:
        pass

    # Build message list for the LLM
    messages = [{"role": "system", "content": system_instruction}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_text})

    try:
        response_text, actions, triage_result, dispatch_result = await asyncio.to_thread(
            _run_llm_with_tools, messages, call_id, system_instruction
        )
        return {
            "response_text": response_text,
            "nlu": nlu_result,
            "actions": actions,
            "triage": triage_result,
            "dispatch": dispatch_result,
        }
    except Exception as e:
        # Fallback to BoW on any LLM error
        return {
            "response_text": _generate_fallback_response(nlu_result, call_id),
            "nlu": nlu_result,
            "actions": [],
            "triage": None,
            "dispatch": None,
            "llm_error": str(e),
        }