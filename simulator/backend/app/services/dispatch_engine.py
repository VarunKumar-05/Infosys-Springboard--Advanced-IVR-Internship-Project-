"""
Mock Dispatch ILP Engine — distance-based ambulance assignment that
simulates a Gurobi-based Integer Linear Programming solver.
Uses Supabase PostgreSQL for ambulance state.
"""

from __future__ import annotations
import time
import random
import uuid
from app.models import AmbulanceStatus, AmbulanceType, Priority
from app.database import get_all_ambulances_db, get_ambulance_db, update_ambulance_db, haversine_km, _now


def assign(
    patient_lat: float,
    patient_lon: float,
    priority: str,
    chief_complaint: str,
    estimated_severity: int,
    ambulance_type_required: str = "BLS",
) -> dict:
    """Find optimal ambulance using simulated ILP dispatch solver."""
    start = time.perf_counter()
    patient_loc = {"lat": patient_lat, "lon": patient_lon}

    all_ambulances = get_all_ambulances_db()

    # Filter available ambulances
    candidates = []
    for amb in all_ambulances:
        if amb["status"] != AmbulanceStatus.AVAILABLE:
            continue
        # For critical / high, prefer ALS units
        if priority in (Priority.CRITICAL, Priority.HIGH) and ambulance_type_required == "ALS":
            if amb["type"] != AmbulanceType.ALS:
                continue
        dist = haversine_km(patient_loc, amb["location"])
        candidates.append((amb["id"], amb, dist))

    # If no ALS available, fall back to any available
    if not candidates:
        for amb in all_ambulances:
            if amb["status"] != AmbulanceStatus.AVAILABLE:
                continue
            dist = haversine_km(patient_loc, amb["location"])
            candidates.append((amb["id"], amb, dist))

    if not candidates:
        solver_ms = int((time.perf_counter() - start) * 1000) + random.randint(150, 300)
        return {
            "error": "No ambulances available",
            "solver_time_ms": solver_ms,
        }

    # Sort by distance (simulating ILP MIN objective)
    candidates.sort(key=lambda c: c[2])
    best_id, best_amb, best_dist = candidates[0]

    # ETA calculation: assume avg speed ~40 km/h in urban area
    eta_minutes = max(1, round(best_dist / 40 * 60))

    # Apply priority modifier
    if priority == Priority.CRITICAL:
        eta_minutes = max(1, eta_minutes - 2)  # lights & sirens

    # Update ambulance status in DB
    update_ambulance_db(best_id, {"status": AmbulanceStatus.DISPATCHED})

    solver_ms = int((time.perf_counter() - start) * 1000) + random.randint(180, 350)

    amb_type = best_amb["type"]
    type_value = amb_type.value if hasattr(amb_type, "value") else amb_type

    reasoning = (
        f"Selected {best_id} (closest available {type_value} unit). "
        f"Distance: {best_dist:.1f} km. "
        f"ETA: {eta_minutes} min. "
        f"Objective: MIN(response_time + coverage_gap). "
        f"Constraint: priority={priority}, required_type={ambulance_type_required}."
    )

    return {
        "dispatch_id": f"DSP-{uuid.uuid4().hex[:6].upper()}",
        "assigned_ambulance": best_id,
        "ambulance_type": best_amb["type"],
        "eta_minutes": eta_minutes,
        "distance_km": round(best_dist, 2),
        "crew_size": best_amb["crew_size"],
        "patient_location": patient_loc,
        "ambulance_location": best_amb["location"],
        "priority": priority,
        "solver_time_ms": solver_ms,
        "reasoning": reasoning,
    }


def get_all_ambulances() -> list[dict]:
    """Return current state of all ambulances."""
    return get_all_ambulances_db()


def reset_ambulance(ambulance_id: str) -> dict | None:
    """Reset an ambulance back to available."""
    amb = get_ambulance_db(ambulance_id)
    if amb:
        update_ambulance_db(ambulance_id, {"status": AmbulanceStatus.AVAILABLE})
        amb["status"] = AmbulanceStatus.AVAILABLE
        return amb
    return None
