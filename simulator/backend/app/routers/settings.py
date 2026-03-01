"""
Settings endpoints — simulator configuration and system tuning.
"""

from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timezone

router = APIRouter(prefix="/api/settings", tags=["Settings"])


# ── Configuration state ──────────────────────────────────────────────────

CONFIG: dict = {
    "nlu": {
        "engine": "keyword-rule-based",
        "confidence_threshold": 0.60,
        "default_language": "en-US",
        "max_input_length": 500,
        "enable_sentiment": True,
        "enable_entity_extraction": True,
        "fallback_intent": "general.unknown",
    },
    "triage": {
        "solver": "SCIP-ILP-simulation",
        "max_severity": 10,
        "emergency_threshold": 8,
        "urgent_threshold": 5,
        "enable_cardiac_hard_constraint": True,
        "enable_pediatric_priority": True,
        "age_risk_threshold": 50,
        "resource_check_enabled": True,
    },
    "dispatch": {
        "solver": "Gurobi-ILP-simulation",
        "fleet_size": 12,
        "default_speed_kmh": 40,
        "priority_speed_modifier": 1.3,
        "max_dispatch_range_km": 50,
        "prefer_als_for_critical": True,
        "enable_lights_and_sirens_eta_reduction": True,
        "eta_reduction_minutes": 2,
    },
    "ivr": {
        "greeting_message": "Welcome to City Hospital. How can I help you today?",
        "max_call_duration_seconds": 600,
        "auto_end_on_goodbye": True,
        "transfer_timeout_seconds": 30,
        "recording_enabled": False,
        "language_options": ["en-US", "es-MX", "fr-FR", "de-DE", "zh-CN"],
    },
    "system": {
        "version": "1.0.0",
        "environment": "simulator",
        "log_level": "INFO",
        "max_active_calls": 50,
        "analytics_retention_days": 30,
        "api_rate_limit": 100,
        "cors_origins": ["*"],
    },
}


# ── Request models ───────────────────────────────────────────────────────

class SettingUpdate(BaseModel):
    value: str | int | float | bool | list


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("", summary="Get all settings")
def get_all_settings() -> dict:
    """Return the complete configuration tree."""
    return {
        "settings": CONFIG,
        "categories": list(CONFIG.keys()),
        "last_modified": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{category}", summary="Get settings for a category")
def get_category_settings(category: str) -> dict:
    """Return settings for a specific category (nlu, triage, dispatch, ivr, system)."""
    if category not in CONFIG:
        return {"error": f"Unknown category '{category}'", "available": list(CONFIG.keys())}
    return {
        "category": category,
        "settings": CONFIG[category],
    }


@router.put("/{category}/{key}", summary="Update a single setting")
def update_setting(category: str, key: str, body: SettingUpdate) -> dict:
    """Update a specific configuration value."""
    if category not in CONFIG:
        return {"error": f"Unknown category '{category}'"}
    if key not in CONFIG[category]:
        return {"error": f"Unknown key '{key}' in category '{category}'", "available_keys": list(CONFIG[category].keys())}

    old_value = CONFIG[category][key]
    CONFIG[category][key] = body.value
    return {
        "category": category,
        "key": key,
        "old_value": old_value,
        "new_value": body.value,
        "status": "updated",
    }


@router.post("/reset", summary="Reset all settings to defaults")
def reset_settings() -> dict:
    """Reset configuration to factory defaults."""
    CONFIG["nlu"]["confidence_threshold"] = 0.60
    CONFIG["nlu"]["enable_sentiment"] = True
    CONFIG["nlu"]["enable_entity_extraction"] = True
    CONFIG["triage"]["emergency_threshold"] = 8
    CONFIG["triage"]["urgent_threshold"] = 5
    CONFIG["triage"]["enable_cardiac_hard_constraint"] = True
    CONFIG["dispatch"]["default_speed_kmh"] = 40
    CONFIG["dispatch"]["prefer_als_for_critical"] = True
    CONFIG["dispatch"]["eta_reduction_minutes"] = 2
    CONFIG["ivr"]["max_call_duration_seconds"] = 600
    CONFIG["ivr"]["auto_end_on_goodbye"] = True
    CONFIG["system"]["log_level"] = "INFO"
    CONFIG["system"]["max_active_calls"] = 50
    return {"status": "reset_to_defaults", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/check", summary="System health check")
def health_check() -> dict:
    """Return status of all subsystems."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "nlu_engine": {"status": "operational", "engine": CONFIG["nlu"]["engine"]},
            "triage_engine": {"status": "operational", "solver": CONFIG["triage"]["solver"]},
            "dispatch_engine": {"status": "operational", "solver": CONFIG["dispatch"]["solver"], "fleet_size": CONFIG["dispatch"]["fleet_size"]},
            "ivr_system": {"status": "operational", "max_calls": CONFIG["system"]["max_active_calls"]},
            "database": {"status": "operational", "type": "in-memory"},
        },
    }
