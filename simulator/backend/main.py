"""
AI Hospital IVR Web Simulator — FastAPI Backend
================================================
Main entry point.  Registers all routers, configures CORS,
exposes the dynamic menu endpoint, and serves OpenAPI docs.

Run:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import scenarios, calls, nlu, triage, dispatch, analytics, patients, logs, settings

# ── Application ──────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Hospital IVR Simulator",
    description=(
        "Interactive web simulator for the AI-Based Hospital IVR System.  "
        "Provides mock NLU, ILP-based triage (SCIP), and ILP-based dispatch "
        "(Gurobi) engines behind a clean REST API."
    ),
    version="1.0.0",
    docs_url="/docs",          # Swagger UI
    redoc_url="/redoc",        # ReDoc
    openapi_url="/openapi.json",
)

# ── CORS (allow React dev server) ────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ────────────────────────────────────────────────────
app.include_router(scenarios.router)
app.include_router(calls.router)
app.include_router(nlu.router)
app.include_router(triage.router)
app.include_router(dispatch.router)
app.include_router(analytics.router)
app.include_router(patients.router)
app.include_router(logs.router)
app.include_router(settings.router)


# ── Root & menu ──────────────────────────────────────────────────────────
@app.get("/", tags=["System"])
def root():
    """Health-check / welcome endpoint."""
    return {
        "service": "AI Hospital IVR Simulator",
        "version": "1.0.0",
        "docs": "/docs",
        "menu": "/api/menu",
    }


@app.get("/api/menu", tags=["System"], summary="Menu-driven navigation structure")
def get_menu():
    """
    Return the full menu tree so the frontend can build its sidebar
    dynamically.  Each item has a label, icon hint, route, and optional
    children.
    """
    return {
        "title": "AI Hospital IVR Simulator",
        "items": [
            {
                "id": "call-simulator",
                "label": "Call Simulator",
                "icon": "phone",
                "route": "/simulator",
                "description": "Start and interact with simulated IVR calls",
                "endpoints": [
                    "POST /api/calls/start",
                    "POST /api/calls/{id}/input",
                    "GET  /api/calls/{id}/status",
                    "POST /api/calls/{id}/end",
                ],
            },
            {
                "id": "scenarios",
                "label": "Scenario Manager",
                "icon": "list",
                "route": "/scenarios",
                "description": "Create, edit, and browse test scenarios",
                "endpoints": [
                    "GET  /api/scenarios",
                    "POST /api/scenarios",
                    "PUT  /api/scenarios/{id}",
                    "DEL  /api/scenarios/{id}",
                ],
            },
            {
                "id": "nlu",
                "label": "NLU Analyzer",
                "icon": "brain",
                "route": "/nlu",
                "description": "Analyze text for intent, entities, and sentiment",
                "endpoints": [
                    "POST /api/nlu/analyze",
                    "POST /api/nlu/batch",
                    "GET  /api/nlu/intents",
                ],
            },
            {
                "id": "triage",
                "label": "Triage Assessment",
                "icon": "activity",
                "route": "/triage",
                "description": "Run ILP-based triage and check resources",
                "endpoints": [
                    "POST /api/triage/assess",
                    "GET  /api/triage/resources",
                    "GET  /api/triage/rules",
                ],
            },
            {
                "id": "dispatch",
                "label": "Ambulance Dispatch",
                "icon": "truck",
                "route": "/dispatch",
                "description": "Assign ambulances and manage fleet",
                "endpoints": [
                    "POST /api/dispatch/assign",
                    "GET  /api/dispatch/ambulances",
                    "POST /api/dispatch/reset-all",
                ],
            },
            {
                "id": "analytics",
                "label": "Analytics Dashboard",
                "icon": "bar-chart",
                "route": "/analytics",
                "description": "View call metrics, dispatch stats, and history",
                "endpoints": [
                    "GET  /api/analytics",
                    "GET  /api/analytics/call-history",
                    "POST /api/analytics/reset",
                ],
            },
            {
                "id": "patients",
                "label": "Patient Records",
                "icon": "user",
                "route": "/patients",
                "description": "View, register, and manage patient records & risk profiles",
                "endpoints": [
                    "GET  /api/patients",
                    "POST /api/patients",
                    "GET  /api/patients/{id}",
                    "PUT  /api/patients/{id}",
                    "GET  /api/patients/{id}/risk-profile",
                ],
            },
            {
                "id": "logs",
                "label": "System Logs",
                "icon": "file-text",
                "route": "/logs",
                "description": "View system activity logs, errors, and audit trail",
                "endpoints": [
                    "GET  /api/logs",
                    "GET  /api/logs/stats",
                    "GET  /api/logs/sources",
                    "POST /api/logs/clear",
                ],
            },
            {
                "id": "settings",
                "label": "Settings",
                "icon": "settings",
                "route": "/settings",
                "description": "Configure NLU, triage, dispatch, and system parameters",
                "endpoints": [
                    "GET  /api/settings",
                    "GET  /api/settings/{category}",
                    "PUT  /api/settings/{category}/{key}",
                    "POST /api/settings/reset",
                    "GET  /api/settings/health/check",
                ],
            },
        ],
    }
