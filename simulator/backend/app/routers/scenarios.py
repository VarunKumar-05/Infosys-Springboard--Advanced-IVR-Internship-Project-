"""
Scenario management endpoints — CRUD operations for test scenarios.
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.models import ScenarioCreate, ScenarioResponse
from app.database import SCENARIOS, _now, _id

router = APIRouter(prefix="/api/scenarios", tags=["Scenarios"])


@router.get("", summary="List all scenarios")
def list_scenarios(category: str | None = None) -> list[dict]:
    """Return all available test scenarios, optionally filtered by category."""
    scenarios = list(SCENARIOS.values())
    if category:
        scenarios = [s for s in scenarios if s.get("category") == category]
    return scenarios


@router.get("/categories", summary="List scenario categories")
def list_categories() -> list[str]:
    """Return distinct scenario categories."""
    return sorted({s.get("category", "general") for s in SCENARIOS.values()})


@router.get("/{scenario_id}", summary="Get scenario by ID")
def get_scenario(scenario_id: str) -> dict:
    """Return a single scenario with full step details."""
    if scenario_id not in SCENARIOS:
        raise HTTPException(404, f"Scenario '{scenario_id}' not found")
    return SCENARIOS[scenario_id]


@router.post("", status_code=201, summary="Create new scenario")
def create_scenario(body: ScenarioCreate) -> dict:
    """Create a new test scenario."""
    sid = f"custom-{_id().lower()}"
    now = _now()
    scenario = {
        "id": sid,
        **body.model_dump(),
        "steps": [s.model_dump() for s in body.steps],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    if body.expected_triage_level:
        scenario["expected_triage_level"] = body.expected_triage_level.value
    SCENARIOS[sid] = scenario
    return scenario


@router.put("/{scenario_id}", summary="Update scenario")
def update_scenario(scenario_id: str, body: ScenarioCreate) -> dict:
    """Update an existing scenario."""
    if scenario_id not in SCENARIOS:
        raise HTTPException(404, f"Scenario '{scenario_id}' not found")
    now = _now()
    scenario = {
        "id": scenario_id,
        **body.model_dump(),
        "steps": [s.model_dump() for s in body.steps],
        "created_at": SCENARIOS[scenario_id]["created_at"],
        "updated_at": now.isoformat(),
    }
    if body.expected_triage_level:
        scenario["expected_triage_level"] = body.expected_triage_level.value
    SCENARIOS[scenario_id] = scenario
    return scenario


@router.delete("/{scenario_id}", summary="Delete scenario")
def delete_scenario(scenario_id: str) -> dict:
    """Delete a scenario by ID."""
    if scenario_id not in SCENARIOS:
        raise HTTPException(404, f"Scenario '{scenario_id}' not found")
    del SCENARIOS[scenario_id]
    return {"deleted": scenario_id, "status": "ok"}
