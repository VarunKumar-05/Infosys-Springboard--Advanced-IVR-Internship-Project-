"""
Mock NLU Engine — keyword-based intent detection, entity extraction,
and sentiment analysis for the IVR simulator.
"""

from __future__ import annotations
import re
import time
import random
from app.models import Sentiment


# ── Intent keyword map ───────────────────────────────────────────────────

_INTENT_MAP: list[tuple[str, list[str], float]] = [
    # (intent, keywords, base_confidence)
    ("symptom.emergency", [
        "chest pain", "heart attack", "can't breathe", "cannot breathe",
        "difficulty breathing", "shortness of breath", "stroke", "unconscious",
        "seizure", "heavy bleeding", "severe bleeding", "choking",
        "anaphylaxis", "allergic reaction severe", "collapsed", "not breathing",
    ], 0.95),
    ("symptom.urgent", [
        "high fever", "fever", "vomiting blood", "broken bone", "fracture",
        "deep cut", "bad headache", "migraine", "abdominal pain",
        "stomach pain", "dizziness", "fainting", "rash spreading",
        "burn", "sprain", "infected wound", "swelling",
    ], 0.88),
    ("symptom.routine", [
        "cold", "cough", "sore throat", "runny nose", "mild headache",
        "back pain", "joint pain", "fatigue", "tired", "insomnia",
        "minor cut", "bruise", "mild rash", "congestion",
    ], 0.85),
    ("appointment.booking", [
        "book appointment", "schedule appointment", "make appointment",
        "see doctor", "see dr", "check-up", "checkup", "follow up",
        "follow-up", "book a visit", "available slots", "next available",
    ], 0.92),
    ("appointment.cancel", [
        "cancel appointment", "cancel my appointment", "reschedule",
        "change appointment", "move appointment",
    ], 0.90),
    ("appointment.confirm", [
        "that works", "sounds good", "yes please", "confirm",
        "book it", "monday", "tuesday", "wednesday", "thursday",
        "friday", "morning", "afternoon", "pm", "am",
    ], 0.88),
    ("prescription.refill", [
        "refill", "prescription", "medication", "medicine refill",
        "need more", "ran out of", "renew prescription",
    ], 0.87),
    ("billing.inquiry", [
        "bill", "billing", "charge", "payment", "insurance",
        "cost", "price", "invoice", "statement", "account balance",
    ], 0.86),
    ("general.greeting", [
        "hello", "hi", "hey", "good morning", "good afternoon",
    ], 0.80),
    ("general.help", [
        "help", "what can you do", "options", "menu", "services",
    ], 0.82),
    ("general.goodbye", [
        "bye", "goodbye", "thank you", "thanks", "that's all",
        "nothing else", "no thanks",
    ], 0.85),
]


# ── Entity patterns ──────────────────────────────────────────────────────

_SYMPTOM_KEYWORDS = [
    "chest pain", "headache", "migraine", "fever", "cough", "nausea",
    "vomiting", "dizziness", "shortness of breath", "difficulty breathing",
    "abdominal pain", "stomach pain", "back pain", "joint pain",
    "sore throat", "rash", "swelling", "bleeding", "fatigue",
    "wheezing", "heart palpitations", "numbness", "tingling",
    "chest tightness", "body aches",
]

_BODY_PARTS = [
    "chest", "head", "arm", "left arm", "right arm", "leg", "left leg",
    "right leg", "back", "neck", "stomach", "abdomen", "throat",
    "knee", "shoulder", "wrist", "ankle", "hip", "eye", "ear",
]

_SEVERITY_MODIFIERS = {
    "really bad": 9, "very bad": 9, "severe": 9, "terrible": 9,
    "extreme": 10, "worst": 10, "excruciating": 10,
    "bad": 7, "strong": 7, "intense": 8,
    "moderate": 5, "mild": 3, "slight": 2, "minor": 2, "little": 2,
}

_DISTRESS_WORDS = [
    "help", "please", "hurry", "dying", "scared", "afraid",
    "can't", "won't stop", "emergency", "desperate", "panic",
    "terrible", "worst", "unbearable",
]


def analyze(text: str, language: str = "en-US") -> dict:
    """Run full NLU pipeline on input text.  Returns dict with all fields."""
    start = time.perf_counter()
    lower = text.lower().strip()

    # Intent detection
    intent, confidence = _detect_intent(lower)

    # Entity extraction
    entities = _extract_entities(lower)

    # Sentiment & distress
    sentiment, distress = _analyze_sentiment(lower)

    elapsed_ms = int((time.perf_counter() - start) * 1000) + random.randint(80, 250)

    return {
        "transcript": text,
        "intent": intent,
        "confidence": round(min(confidence + random.uniform(-0.03, 0.03), 1.0), 2),
        "entities": entities,
        "sentiment": sentiment,
        "distress_score": round(distress, 2),
        "language": language,
        "processing_time_ms": elapsed_ms,
    }


def _detect_intent(text: str) -> tuple[str, float]:
    best_intent = "general.unknown"
    best_score = 0.0
    for intent, keywords, base_conf in _INTENT_MAP:
        matches = sum(1 for kw in keywords if kw in text)
        if matches > 0:
            score = base_conf * min(matches / 2, 1.0)
            if score > best_score:
                best_score = score
                best_intent = intent
    if best_score == 0:
        best_score = 0.35
    return best_intent, best_score


def _extract_entities(text: str) -> dict:
    entities: dict = {}

    # Symptoms
    found_symptoms = [s for s in _SYMPTOM_KEYWORDS if s in text]
    if found_symptoms:
        entities["symptoms"] = found_symptoms

    # Body parts
    found_parts = [p for p in _BODY_PARTS if p in text]
    if found_parts:
        entities["body_parts"] = found_parts

    # Severity
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

    # Medication
    meds = ["lisinopril", "metoprolol", "aspirin", "ibuprofen", "amoxicillin",
            "metformin", "atorvastatin", "omeprazole", "amlodipine", "losartan"]
    found_meds = [m for m in meds if m in text]
    if found_meds:
        entities["medications"] = found_meds

    return entities


def _analyze_sentiment(text: str) -> tuple[str, float]:
    distress_count = sum(1 for w in _DISTRESS_WORDS if w in text)
    negative_signal = any(kw in text for kw in [
        "pain", "hurt", "bad", "worse", "terrible", "scared", "bleeding",
        "can't", "emergency", "severe", "dying",
    ])
    positive_signal = any(kw in text for kw in [
        "thank", "good", "great", "fine", "okay", "happy", "better",
    ])

    if distress_count >= 2 or (negative_signal and distress_count >= 1):
        return Sentiment.NEGATIVE, min(0.5 + distress_count * 0.15, 1.0)
    elif negative_signal:
        return Sentiment.NEGATIVE, 0.55
    elif positive_signal:
        return Sentiment.POSITIVE, 0.15
    else:
        return Sentiment.NEUTRAL, 0.25
