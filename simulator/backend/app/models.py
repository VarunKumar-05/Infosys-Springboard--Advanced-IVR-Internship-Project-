"""
Pydantic models for the AI Hospital IVR Web Simulator.
All request/response schemas for every endpoint.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


# ── Enums ────────────────────────────────────────────────────────────────

class TriageLevel(str, Enum):
    EMERGENCY = "EMERGENCY"
    URGENT = "URGENT"
    ROUTINE = "ROUTINE"

class CallStatus(str, Enum):
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TRANSFERRED = "transferred"
    ERROR = "error"

class AmbulanceStatus(str, Enum):
    AVAILABLE = "available"
    DISPATCHED = "dispatched"
    EN_ROUTE = "en_route"
    AT_SCENE = "at_scene"
    AT_HOSPITAL = "at_hospital"

class AmbulanceType(str, Enum):
    ALS = "ALS"
    BLS = "BLS"

class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class InputType(str, Enum):
    TEXT = "text"
    VOICE = "voice"

class Sentiment(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


# ── Shared Sub-Models ────────────────────────────────────────────────────

class Location(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)

class MenuItem(BaseModel):
    id: str
    label: str
    icon: str
    description: str
    route: str


# ── Scenario Models ──────────────────────────────────────────────────────

class ScenarioStep(BaseModel):
    step_number: int
    speaker: str = Field(..., description="'system' or 'patient'")
    content: str
    action: Optional[str] = None
    expected_intent: Optional[str] = None

class ScenarioCreate(BaseModel):
    name: str
    description: str
    category: str = "general"
    language: str = "en-US"
    steps: list[ScenarioStep]
    expected_triage_level: Optional[TriageLevel] = None

class ScenarioResponse(ScenarioCreate):
    id: str
    created_at: datetime
    updated_at: datetime


# ── Call Simulation Models ────────────────────────────────────────────────

class CallStartRequest(BaseModel):
    scenario_id: Optional[str] = None
    language: str = "en-US"
    caller_phone: str = "+1-555-000-0000"

class CallStartResponse(BaseModel):
    call_session_id: str
    status: CallStatus
    greeting: str
    timestamp: datetime

class CallInputRequest(BaseModel):
    user_input: str
    input_type: InputType = InputType.TEXT

class NluResult(BaseModel):
    intent: str
    confidence: float
    entities: dict
    sentiment: Sentiment
    distress_score: float

class TriageResult(BaseModel):
    triage_level: TriageLevel
    recommended_facility: str
    clinical_reasoning: str
    severity_score: int
    solver_time_ms: int

class DispatchResult(BaseModel):
    assigned_ambulance: Optional[str] = None
    ambulance_type: Optional[AmbulanceType] = None
    eta_minutes: Optional[int] = None
    crew_size: Optional[int] = None

class CallInputResponse(BaseModel):
    step_number: int
    transcript: str
    nlu: NluResult
    triage: Optional[TriageResult] = None
    dispatch: Optional[DispatchResult] = None
    system_response: str
    call_status: CallStatus

class CallStatusResponse(BaseModel):
    call_session_id: str
    status: CallStatus
    current_step: int
    duration_seconds: float
    transcript: list[dict]
    triage_result: Optional[TriageResult] = None
    dispatch_result: Optional[DispatchResult] = None

class CallEndRequest(BaseModel):
    reason: str = "user_ended"

class CallSummary(BaseModel):
    call_session_id: str
    status: CallStatus
    total_steps: int
    duration_seconds: float
    final_triage: Optional[TriageLevel] = None
    ambulance_assigned: Optional[str] = None
    transcript: list[dict]


# ── NLU Models ────────────────────────────────────────────────────────────

class NluAnalyzeRequest(BaseModel):
    text: str
    language: str = "en-US"

class NluAnalyzeResponse(BaseModel):
    transcript: str
    intent: str
    confidence: float
    entities: dict
    sentiment: Sentiment
    distress_score: float
    language: str
    processing_time_ms: int


# ── Triage Models ─────────────────────────────────────────────────────────

class TriageAssessRequest(BaseModel):
    symptoms: list[str]
    severity_score: int = Field(..., ge=1, le=10)
    patient_age: int = Field(..., ge=0, le=150)
    patient_gender: str = "unknown"
    medical_history: list[str] = []
    duration_minutes: Optional[int] = None
    location: Optional[Location] = None

class TriageAssessResponse(BaseModel):
    triage_level: TriageLevel
    recommended_facility: str
    clinical_reasoning: str
    severity_score: int
    risk_factors: list[str]
    constraints_applied: list[str]
    solver_time_ms: int

class ResourceAvailability(BaseModel):
    emergency_room: dict
    urgent_care: dict
    general_ward: dict
    queue_length: int
    last_updated: datetime


# ── Dispatch Models ───────────────────────────────────────────────────────

class DispatchAssignRequest(BaseModel):
    patient_location: Location
    priority: Priority
    chief_complaint: str
    estimated_severity: int = Field(..., ge=1, le=10)
    ambulance_type_required: AmbulanceType = AmbulanceType.BLS

class AmbulanceInfo(BaseModel):
    id: str
    location: Location
    status: AmbulanceStatus
    type: AmbulanceType
    crew_size: int
    last_updated: datetime

class DispatchAssignResponse(BaseModel):
    dispatch_id: str
    assigned_ambulance: str
    ambulance_type: AmbulanceType
    eta_minutes: int
    distance_km: float
    crew_size: int
    patient_location: Location
    ambulance_location: Location
    priority: Priority
    solver_time_ms: int
    reasoning: str


# ── Analytics Models ──────────────────────────────────────────────────────

class CallMetrics(BaseModel):
    total_calls: int
    emergency_calls: int
    routine_calls: int
    avg_duration_seconds: float
    avg_response_time_ms: float
    triage_accuracy_percent: float

class DispatchMetrics(BaseModel):
    total_dispatches: int
    avg_eta_minutes: float
    ambulances_available: int
    ambulances_total: int
    avg_solver_time_ms: float

class AnalyticsResponse(BaseModel):
    call_metrics: CallMetrics
    dispatch_metrics: DispatchMetrics
    recent_calls: list[dict]
    timestamp: datetime
