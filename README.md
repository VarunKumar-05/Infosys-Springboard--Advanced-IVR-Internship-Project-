# AI-Based Hospital IVR System

An AI-powered Interactive Voice Response (IVR) system for hospitals that replaces traditional DTMF-based menu navigation with intelligent natural language understanding.

## Key Features

- **Voice Understanding** - Speech-to-Text with medical vocabulary, multi-language support (10+ languages)
- **Clinical Triage** - AI-powered symptom assessment with risk-based routing
- **Ambulance Dispatch** - ILP-optimized assignment with real-time GPS tracking
- **System Integration** - EHR connectivity (Epic, Cerner via HL7/FHIR), Legacy PBX bridging

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SYSTEM COMPONENTS                                │
├─────────────────────────────────────────────────────────────────────────┤
│   VOICE LAYER      │   AI LAYER        │  OPTIMIZATION   │ INTEGRATION │
│   • Twilio/ACS     │   • Speech-to-Text│  • Triage ILP   │ • EHR API   │
│   • SIP Gateway    │   • NLU Engine    │  • Dispatch ILP │ • CAD System│
│   • TTS Engine     │   • Sentiment     │  • Resource Mgr │ • HL7/FHIR  │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      BUSINESS LOGIC LAYER                               │
│  Patient Auth │ Appointment │ Symptom Triage │ Ambulance │ Staff       │
│   Service     │   Booking   │    Service     │  Dispatch │ Routing     │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  DATA PERSISTENCE              │  EXTERNAL INTEGRATION                  │
│  • PostgreSQL (PHI)            │  • Epic/Cerner EHR (HL7/FHIR)         │
│  • MongoDB (Logs)              │  • Legacy PBX (SIP)                   │
│  • Redis (Cache/Session)       │  • Ambulance CAD (REST/WebSocket)    │
└─────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Voice | Twilio, Azure ACS, FreeSWITCH |
| AI/NLU | Dialogflow CX, Deepgram, spaCy |
| Optimization | SCIP, Gurobi |
| Backend | Node.js (NestJS), Python |
| Database | PostgreSQL, MongoDB, Redis |
| Infrastructure | Kubernetes, Docker |

## Target Metrics

| Metric | Target |
|--------|--------|
| Call handling time | < 2 minutes |
| First-call resolution | > 80% |
| Emergency response | 25% faster |
| System uptime | 99.9% |
| Concurrent calls | 1000+ |

## License

MIT License
