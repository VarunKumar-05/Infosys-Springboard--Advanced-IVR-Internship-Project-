# AI Hospital IVR Web Simulator

Interactive web simulator for the **AI-Based Hospital IVR System** built with
**FastAPI** (Python) backend and **React + TypeScript** (Vite) frontend.

## Architecture

```
simulator/
├── backend/                  # FastAPI REST API
│   ├── main.py               # App entry point, CORS, menu, routers
│   ├── requirements.txt
│   └── app/
│       ├── models.py          # Pydantic request/response schemas
│       ├── database.py        # In-memory data store & mock data
│       ├── routers/           # API route handlers
│       │   ├── scenarios.py   # Scenario CRUD
│       │   ├── calls.py       # Call simulation lifecycle
│       │   ├── nlu.py         # NLU text analysis
│       │   ├── triage.py      # Triage assessment (SCIP ILP sim)
│       │   ├── dispatch.py    # Ambulance dispatch (Gurobi ILP sim)
│       │   └── analytics.py   # Metrics & history
│       └── services/          # Business logic engines
│           ├── nlu_engine.py      # Keyword-based NLU
│           ├── triage_engine.py   # Rule-based triage ILP
│           └── dispatch_engine.py # Distance-based dispatch ILP
├── frontend/                 # React + TypeScript (Vite)
│   ├── package.json
│   ├── vite.config.ts         # Dev proxy /api → :8000
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx            # Routing & layout
│       ├── api/client.ts      # Typed API client
│       ├── components/
│       │   ├── Sidebar.tsx
│       │   ├── CallSimulator.tsx
│       │   ├── ScenarioManager.tsx
│       │   ├── NluAnalyzer.tsx
│       │   ├── TriagePanel.tsx
│       │   ├── DispatchPanel.tsx
│       │   └── AnalyticsDashboard.tsx
│       └── index.css          # Global styles
├── run-backend.bat            # Start backend
├── run-frontend.bat           # Start frontend
├── run-all.bat                # Start both
└── README.md
```

## Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** with npm

### Option 1 — Run Scripts (Windows)
```
run-all.bat
```
This starts both servers in separate windows.

### Option 2 — Manual

**Terminal 1 — Backend:**
```bash
cd simulator/backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd simulator/frontend
npm install
npm run dev
```

### Access
| Service         | URL                         |
|-----------------|-----------------------------|
| Frontend        | http://localhost:5173        |
| Backend API     | http://localhost:8000        |
| Swagger Docs    | http://localhost:8000/docs   |
| ReDoc           | http://localhost:8000/redoc  |
| OpenAPI JSON    | http://localhost:8000/openapi.json |

## Features

### Menu-Driven Navigation
The frontend sidebar is built dynamically from `GET /api/menu` — the backend
controls the menu structure, labels, icons, and routes.

### Modules

| Module               | Description                                              |
|----------------------|----------------------------------------------------------|
| **Call Simulator**   | Start IVR calls, type messages, see NLU/triage/dispatch  |
| **Scenario Manager** | Browse, create, and delete test scenarios                |
| **NLU Analyzer**     | Standalone text analysis — intent, entities, sentiment   |
| **Triage Assessment**| ILP-based triage with clinical rules and resource checks |
| **Ambulance Dispatch** | ILP-based dispatch with fleet management               |
| **Analytics**        | Call metrics, dispatch stats, and performance data       |

### API Endpoints (31 total)

#### System
- `GET /` — Health check
- `GET /api/menu` — Menu structure for frontend

#### Scenarios
- `GET /api/scenarios` — List scenarios
- `GET /api/scenarios/categories` — List categories
- `GET /api/scenarios/{id}` — Get scenario
- `POST /api/scenarios` — Create scenario
- `PUT /api/scenarios/{id}` — Update scenario
- `DELETE /api/scenarios/{id}` — Delete scenario

#### Calls
- `POST /api/calls/start` — Start call
- `POST /api/calls/{id}/input` — Send user input
- `GET /api/calls/{id}/status` — Call status & transcript
- `POST /api/calls/{id}/end` — End call
- `GET /api/calls` — List active calls

#### NLU
- `POST /api/nlu/analyze` — Analyze text
- `POST /api/nlu/batch` — Batch analysis
- `GET /api/nlu/intents` — Intent reference

#### Triage
- `POST /api/triage/assess` — Run triage
- `GET /api/triage/resources` — Hospital resources
- `PUT /api/triage/resources` — Update resources
- `GET /api/triage/rules` — Clinical rules

#### Dispatch
- `POST /api/dispatch/assign` — Dispatch ambulance
- `GET /api/dispatch/ambulances` — Fleet list
- `GET /api/dispatch/ambulances/{id}` — Single ambulance
- `POST /api/dispatch/ambulances/{id}/reset` — Reset ambulance
- `POST /api/dispatch/reset-all` — Reset all

#### Analytics
- `GET /api/analytics` — Full dashboard
- `GET /api/analytics/call-history` — History
- `GET /api/analytics/active-calls` — Active calls
- `POST /api/analytics/reset` — Reset stats

## Tech Stack

| Layer     | Technology              | Purpose                          |
|-----------|-------------------------|----------------------------------|
| Backend   | FastAPI 0.115           | REST API, auto-docs, validation  |
| Models    | Pydantic v2             | Request/response type safety     |
| NLU       | Custom keyword engine   | Simulates production NLU pipeline|
| Triage    | Custom rule engine      | Simulates SCIP ILP solver        |
| Dispatch  | Custom distance engine  | Simulates Gurobi ILP solver      |
| Frontend  | React 18 + TypeScript   | SPA with typed API calls         |
| Bundler   | Vite 5                  | HMR, proxy, fast builds          |
| Icons     | Lucide React            | Clean icon set                   |
| Routing   | React Router v6         | Client-side routing              |
