"""
NLU analysis endpoints — standalone text analysis without a call session.
"""

from __future__ import annotations
from fastapi import APIRouter
from app.models import NluAnalyzeRequest, NluAnalyzeResponse
from app.services import nlu_engine

router = APIRouter(prefix="/api/nlu", tags=["NLU Analysis"])


@router.post("/analyze", summary="Analyze text for intent, entities & sentiment")
def analyze_text(body: NluAnalyzeRequest) -> NluAnalyzeResponse:
    """Run the full NLU pipeline on arbitrary text input."""
    result = nlu_engine.analyze(body.text, body.language)
    return NluAnalyzeResponse(**result)


@router.post("/batch", summary="Batch-analyze multiple texts")
def batch_analyze(texts: list[str]) -> list[NluAnalyzeResponse]:
    """Analyze a list of texts and return results for each."""
    results = []
    for text in texts:
        r = nlu_engine.analyze(text)
        results.append(NluAnalyzeResponse(**r))
    return results


@router.get("/intents", summary="List all recognized intents")
def list_intents() -> list[dict]:
    """Return the list of intents the NLU engine can detect."""
    return [
        {"intent": "symptom.emergency", "description": "Life-threatening symptoms requiring immediate action", "example": "I'm having chest pain"},
        {"intent": "symptom.urgent", "description": "Serious symptoms needing prompt attention", "example": "I have a high fever for 3 days"},
        {"intent": "symptom.routine", "description": "Minor symptoms for scheduled care", "example": "I have a mild cough"},
        {"intent": "appointment.booking", "description": "Request to schedule an appointment", "example": "I'd like to see Dr. Smith"},
        {"intent": "appointment.cancel", "description": "Cancel or reschedule appointment", "example": "I need to cancel my appointment"},
        {"intent": "appointment.confirm", "description": "Confirm a proposed appointment slot", "example": "Monday at 10 works for me"},
        {"intent": "prescription.refill", "description": "Request prescription renewal", "example": "I need to refill my Lisinopril"},
        {"intent": "billing.inquiry", "description": "Billing or payment question", "example": "I have a question about my bill"},
        {"intent": "general.greeting", "description": "Greeting or salutation", "example": "Hello"},
        {"intent": "general.help", "description": "Request for help or menu options", "example": "What can you do?"},
        {"intent": "general.goodbye", "description": "End conversation", "example": "Thank you, goodbye"},
        {"intent": "general.unknown", "description": "Unrecognized input", "example": "..."},
    ]
