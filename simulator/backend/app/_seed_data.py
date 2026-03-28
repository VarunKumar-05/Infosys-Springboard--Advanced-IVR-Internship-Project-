"""
Seed data for the IVR Simulator — extracted from the original in-memory stores.
Used by postgres_db.init_db() to populate tables on first run.
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from app.models import AmbulanceStatus, AmbulanceType


def _now():
    return datetime.now(timezone.utc)


def _ts(minutes_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


# ── Scenarios ────────────────────────────────────────────────────────────

SEED_SCENARIOS: dict[str, dict] = {
    "emergency-chest-pain": {
        "id": "emergency-chest-pain",
        "name": "Emergency - Chest Pain",
        "description": "Patient experiencing severe chest pain radiating to left arm. High-priority cardiac emergency scenario.",
        "category": "emergency",
        "language": "en-US",
        "expected_triage_level": "EMERGENCY",
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
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I have a question about my hospital bill from last month", "action": None, "expected_intent": "billing.inquiry"},
            {"step_number": 3, "speaker": "system", "content": "I can help with billing questions. Let me transfer you to our billing department. One moment please.", "action": "transfer_billing", "expected_intent": None},
        ],
    },
    "appt-chest-mild": {
        "id": "appt-chest-mild",
        "name": "Appointment - Mild Chest Discomfort",
        "description": "Patient with occasional mild chest tightness, wants cardiologist consultation.",
        "category": "appointment",
        "language": "en-US",
        "expected_triage_level": "ROUTINE",
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I've been having mild chest tightness on and off for a week. I'd like to see a cardiologist.", "action": None, "expected_intent": "appointment.booking"},
            {"step_number": 3, "speaker": "system", "content": "I understand you're experiencing mild chest tightness. Since it's intermittent and mild, I'll schedule you with our cardiology department.", "action": "triage_assess", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "Dr. Patel in Cardiology has availability on Thursday at 9:00 AM or Friday at 3:00 PM. Which would you prefer?", "action": "offer_slots", "expected_intent": None},
            {"step_number": 5, "speaker": "patient", "content": "Thursday at 9 AM please", "action": None, "expected_intent": "appointment.confirm"},
            {"step_number": 6, "speaker": "system", "content": "Your appointment with Dr. Patel (Cardiology) is confirmed for Thursday at 9:00 AM. Please bring any previous ECG reports. Is there anything else?", "action": "confirm_booking", "expected_intent": None},
        ],
    },
    "appt-chest-followup": {
        "id": "appt-chest-followup",
        "name": "Appointment - Chest Pain Follow-up",
        "description": "Patient following up after ER visit for chest pain, needs cardiologist review.",
        "category": "appointment",
        "language": "en-US",
        "expected_triage_level": "URGENT",
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I was in the ER last week with chest pain. They told me to follow up with a cardiologist within 5 days.", "action": None, "expected_intent": "appointment.booking"},
            {"step_number": 3, "speaker": "system", "content": "Thank you for following up. Since this is a post-ER cardiac follow-up, I'll prioritize your appointment.", "action": "triage_assess", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "I have an urgent slot with Dr. Gupta in Cardiology tomorrow at 11:00 AM. Shall I book that?", "action": "offer_slots", "expected_intent": None},
            {"step_number": 5, "speaker": "patient", "content": "Yes, please book it", "action": None, "expected_intent": "appointment.confirm"},
            {"step_number": 6, "speaker": "system", "content": "Confirmed — you'll see Dr. Gupta tomorrow at 11:00 AM, Cardiology Wing, 3rd floor. Please bring your ER discharge papers.", "action": "confirm_booking", "expected_intent": None},
        ],
    },
    "appt-chest-stress-test": {
        "id": "appt-chest-stress-test",
        "name": "Appointment - Cardiac Stress Test",
        "description": "Patient experiencing chest pain during exercise, needs stress test appointment.",
        "category": "appointment",
        "language": "en-US",
        "expected_triage_level": "URGENT",
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I get chest pain every time I exercise. My family doctor said I need a cardiac stress test.", "action": None, "expected_intent": "appointment.booking"},
            {"step_number": 3, "speaker": "system", "content": "Exercise-induced chest pain needs prompt evaluation. I'll schedule you for a stress test with our cardiology lab.", "action": "triage_assess", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "Our cardiac stress test lab has openings on Monday at 8:00 AM (fasting required) or Wednesday at 7:30 AM. Which works for you?", "action": "offer_slots", "expected_intent": None},
            {"step_number": 5, "speaker": "patient", "content": "Monday morning works", "action": None, "expected_intent": "appointment.confirm"},
            {"step_number": 6, "speaker": "system", "content": "Booked for Monday at 8:00 AM at the Cardiology Lab. No food or caffeine for 12 hours prior. Wear comfortable shoes.", "action": "confirm_booking", "expected_intent": None},
        ],
    },
    "appt-cardio-palpitations": {
        "id": "appt-cardio-palpitations",
        "name": "Appointment - Heart Palpitations",
        "description": "Patient with heart palpitations and dizziness wants to see a cardiologist.",
        "category": "appointment",
        "language": "en-US",
        "expected_triage_level": "URGENT",
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I've been having heart palpitations and I feel dizzy sometimes. I need to see a heart doctor.", "action": None, "expected_intent": "appointment.booking"},
            {"step_number": 3, "speaker": "system", "content": "Palpitations with dizziness should be evaluated. Let me get you in with a cardiologist soon.", "action": "triage_assess", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "Dr. Patel can see you Wednesday at 10:30 AM. Does that work?", "action": "offer_slots", "expected_intent": None},
            {"step_number": 5, "speaker": "patient", "content": "Yes, that works fine", "action": None, "expected_intent": "appointment.confirm"},
            {"step_number": 6, "speaker": "system", "content": "Appointment confirmed with Dr. Patel, Cardiology, Wednesday at 10:30 AM. We may run an ECG, so allow 90 minutes.", "action": "confirm_booking", "expected_intent": None},
        ],
    },
    "appt-cardio-bp": {
        "id": "appt-cardio-bp",
        "name": "Appointment - High Blood Pressure Review",
        "description": "Patient on blood pressure medication needs cardiologist follow-up.",
        "category": "appointment",
        "language": "en-US",
        "expected_triage_level": "ROUTINE",
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I need to see my cardiologist for a blood pressure medication review. I've been on Amlodipine for six months.", "action": None, "expected_intent": "appointment.booking"},
            {"step_number": 3, "speaker": "system", "content": "A routine medication review is important. Let me check Dr. Gupta's availability for you.", "action": "check_availability", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "Dr. Gupta has a slot next Tuesday at 2:00 PM or Thursday at 4:00 PM. Which suits you?", "action": "offer_slots", "expected_intent": None},
            {"step_number": 5, "speaker": "patient", "content": "Tuesday at 2 PM", "action": None, "expected_intent": "appointment.confirm"},
            {"step_number": 6, "speaker": "system", "content": "Confirmed with Dr. Gupta on Tuesday at 2:00 PM. Please bring your recent BP readings and medication list.", "action": "confirm_booking", "expected_intent": None},
        ],
    },
    "appt-peds-fever": {
        "id": "appt-peds-fever", "name": "Appointment - Child with Fever",
        "description": "Parent calling about a child with high fever for 2 days, needs pediatrician.",
        "category": "appointment", "language": "en-US", "expected_triage_level": "URGENT",
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "My 4 year old has had a fever of 102 for two days. He's cranky and not eating. I need to see a pediatrician.", "action": None, "expected_intent": "appointment.booking"},
            {"step_number": 3, "speaker": "system", "content": "A fever of 102°F for two days in a young child needs prompt attention. Let me find a pediatrician for today.", "action": "triage_assess", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "Dr. Lee in Pediatrics has a same-day slot at 3:00 PM today. Would that work for you?", "action": "offer_slots", "expected_intent": None},
            {"step_number": 5, "speaker": "patient", "content": "Yes please, we'll be there", "action": None, "expected_intent": "appointment.confirm"},
            {"step_number": 6, "speaker": "system", "content": "Appointment confirmed: Dr. Lee, Pediatrics, today at 3:00 PM. Bring your child's immunization records if available.", "action": "confirm_booking", "expected_intent": None},
        ],
    },
    "appt-peds-vaccination": {
        "id": "appt-peds-vaccination", "name": "Appointment - Child Vaccination",
        "description": "Parent wants to schedule routine vaccinations for their toddler.",
        "category": "appointment", "language": "en-US", "expected_triage_level": "ROUTINE",
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I need to schedule my 18-month-old's vaccination appointment", "action": None, "expected_intent": "appointment.booking"},
            {"step_number": 3, "speaker": "system", "content": "Of course! Let me check the pediatric vaccination clinic schedule for you.", "action": "check_availability", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "Our vaccination clinic runs Monday through Thursday, 9 AM to 12 PM. The next available slot is Tuesday at 10:00 AM with Dr. Lee.", "action": "offer_slots", "expected_intent": None},
            {"step_number": 5, "speaker": "patient", "content": "Tuesday morning is perfect", "action": None, "expected_intent": "appointment.confirm"},
            {"step_number": 6, "speaker": "system", "content": "Booked for Tuesday at 10:00 AM at the Pediatric Vaccination Clinic. Please bring the child's vaccination booklet.", "action": "confirm_booking", "expected_intent": None},
        ],
    },
    "appt-gp-annual": {
        "id": "appt-gp-annual", "name": "Appointment - Annual Physical Exam",
        "description": "Patient scheduling a routine annual health check-up with their GP.",
        "category": "appointment", "language": "en-US", "expected_triage_level": "ROUTINE",
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I'd like to schedule my annual physical exam with any available general doctor", "action": None, "expected_intent": "appointment.booking"},
            {"step_number": 3, "speaker": "system", "content": "Happy to help you schedule your annual check-up. Let me find available GP slots.", "action": "check_availability", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "Dr. Smith has openings next Monday at 10:00 AM or Dr. Johnson on Wednesday at 1:00 PM. Your preference?", "action": "offer_slots", "expected_intent": None},
            {"step_number": 5, "speaker": "patient", "content": "Dr. Smith on Monday please", "action": None, "expected_intent": "appointment.confirm"},
            {"step_number": 6, "speaker": "system", "content": "Confirmed: Annual physical with Dr. Smith, Monday at 10:00 AM. Please fast for 12 hours beforehand for blood work.", "action": "confirm_booking", "expected_intent": None},
        ],
    },
    "appt-gyn-prenatal": {
        "id": "appt-gyn-prenatal", "name": "Appointment - Prenatal Check-up",
        "description": "Pregnant patient scheduling a routine prenatal visit with gynaecologist.",
        "category": "appointment", "language": "en-US", "expected_triage_level": "ROUTINE",
        "steps": [
            {"step_number": 1, "speaker": "system", "content": "Welcome to City Hospital. How can I help you today?", "action": "greeting", "expected_intent": None},
            {"step_number": 2, "speaker": "patient", "content": "I'm 20 weeks pregnant and I need to schedule my next prenatal check-up with a gynaecologist.", "action": None, "expected_intent": "appointment.booking"},
            {"step_number": 3, "speaker": "system", "content": "Congratulations! Let me find a prenatal appointment for you in our OB-GYN department.", "action": "check_availability", "expected_intent": None},
            {"step_number": 4, "speaker": "system", "content": "Dr. Robinson has prenatal appointments on Tuesdays and Thursdays. Next available: Tuesday at 10:00 AM. Would that work?", "action": "offer_slots", "expected_intent": None},
            {"step_number": 5, "speaker": "patient", "content": "Tuesday at 10 AM sounds good", "action": None, "expected_intent": "appointment.confirm"},
            {"step_number": 6, "speaker": "system", "content": "Booked: Dr. Robinson, OB-GYN, Tuesday at 10:00 AM. We'll do an ultrasound at this visit. Drink plenty of water beforehand.", "action": "confirm_booking", "expected_intent": None},
        ],
    },
}

# ── Ambulances ───────────────────────────────────────────────────────────

SEED_AMBULANCES: dict[str, dict] = {
    "AMB-001": {"id": "AMB-001", "location": {"lat": 40.7580, "lon": -73.9855}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.ALS, "crew_size": 3},
    "AMB-002": {"id": "AMB-002", "location": {"lat": 40.7282, "lon": -73.7949}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.BLS, "crew_size": 2},
    "AMB-003": {"id": "AMB-003", "location": {"lat": 40.6892, "lon": -74.0445}, "status": AmbulanceStatus.DISPATCHED, "type": AmbulanceType.ALS, "crew_size": 3},
    "AMB-004": {"id": "AMB-004", "location": {"lat": 40.7484, "lon": -73.9857}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.BLS, "crew_size": 2},
    "AMB-005": {"id": "AMB-005", "location": {"lat": 40.7614, "lon": -73.9776}, "status": AmbulanceStatus.EN_ROUTE, "type": AmbulanceType.ALS, "crew_size": 3},
    "AMB-006": {"id": "AMB-006", "location": {"lat": 40.7831, "lon": -73.9712}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.BLS, "crew_size": 2},
    "AMB-007": {"id": "AMB-007", "location": {"lat": 40.7128, "lon": -74.0060}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.ALS, "crew_size": 3},
    "AMB-008": {"id": "AMB-008", "location": {"lat": 40.7589, "lon": -73.9851}, "status": AmbulanceStatus.AT_HOSPITAL, "type": AmbulanceType.BLS, "crew_size": 2},
    "AMB-009": {"id": "AMB-009", "location": {"lat": 40.7061, "lon": -74.0087}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.ALS, "crew_size": 3},
    "AMB-010": {"id": "AMB-010", "location": {"lat": 40.7527, "lon": -73.9772}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.BLS, "crew_size": 2},
    "AMB-011": {"id": "AMB-011", "location": {"lat": 40.7411, "lon": -74.0018}, "status": AmbulanceStatus.AVAILABLE, "type": AmbulanceType.ALS, "crew_size": 3},
    "AMB-012": {"id": "AMB-012", "location": {"lat": 40.7681, "lon": -73.9819}, "status": AmbulanceStatus.DISPATCHED, "type": AmbulanceType.BLS, "crew_size": 2},
}

# ── Patients ─────────────────────────────────────────────────────────────

SEED_PATIENTS: dict[str, dict] = {}

# ── System Logs ──────────────────────────────────────────────────────────

SEED_LOGS: list[dict] = []
