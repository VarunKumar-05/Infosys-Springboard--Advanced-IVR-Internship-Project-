/**
 * Typed API client for the FastAPI backend.
 * Uses the Vite proxy so all calls go to /api/...
 */

const BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

// ── Generic fetch helper ────────────────────────────────────────────

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function get<T>(path: string) { return request<T>(path); }
function post<T>(path: string, body?: unknown) {
  return request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
}
function put<T>(path: string, body?: unknown) {
  return request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined });
}
function del<T>(path: string) {
  return request<T>(path, { method: "DELETE" });
}

// ── Types ───────────────────────────────────────────────────────────

export interface MenuItem {
  id: string;
  label: string;
  icon: string;
  route: string;
  description: string;
  endpoints: string[];
}

export interface MenuResponse {
  title: string;
  items: MenuItem[];
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
  category: string;
  steps: { step_number: number; speaker: string; content: string; input_type: string }[];
  expected_triage_level?: string;
  created_at: string;
  updated_at: string;
}

export interface CallStartResponse {
  call_session_id: string;
  status: string;
  greeting: string;
  timestamp: string;
}

export interface NluResult {
  intent: string;
  confidence: number;
  entities: Record<string, unknown>;
  sentiment: string;
  distress_score: number;
}

export interface TriageResult {
  triage_level: string;
  recommended_facility: string;
  clinical_reasoning: string;
  severity_score: number;
  solver_time_ms: number;
}

export interface DispatchResult {
  assigned_ambulance: string;
  ambulance_type: string;
  eta_minutes: number;
  crew_size: number;
}

export interface CallInputResponse {
  step_number: number;
  transcript: string;
  nlu: NluResult;
  triage?: TriageResult;
  dispatch?: DispatchResult;
  system_response: string;
  call_status: string;
}

export interface CallStatus {
  call_session_id: string;
  status: string;
  current_step: number;
  duration_seconds: number;
  transcript: { step: number; speaker: string; content: string; timestamp: string }[];
  triage_result?: TriageResult;
  dispatch_result?: DispatchResult;
}

export interface NluAnalysis {
  intent: string;
  confidence: number;
  entities: Record<string, unknown>;
  sentiment: string;
  distress_score: number;
  processing_time_ms: number;
}

export interface TriageAssessment {
  triage_level: string;
  recommended_facility: string;
  clinical_reasoning: string;
  severity_score: number;
  risk_factors: string[];
  constraints_applied: string[];
  solver_time_ms: number;
}

export interface ResourceAvailability {
  emergency_room: { total: number; available: number; staffed: number };
  urgent_care: { total: number; available: number; staffed: number };
  general_ward: { total: number; available: number; staffed: number };
  queue_length: number;
  last_updated: string;
}

export interface AmbulanceInfo {
  id: string;
  location: { lat: number; lon: number };
  status: string;
  type: string;
  crew_size: number;
  last_updated: string;
}

export interface DispatchAssignment {
  dispatch_id: string;
  assigned_ambulance: string;
  ambulance_type: string;
  distance_km: number;
  eta_minutes: number;
  crew_size: number;
  patient_location: { lat: number; lon: number };
  ambulance_location: { lat: number; lon: number };
  priority: string;
  solver_time_ms: number;
  reasoning: string;
}

export interface CallMetrics {
  total_calls: number;
  emergency_calls: number;
  routine_calls: number;
  avg_duration_seconds: number;
  avg_response_time_ms: number;
  triage_accuracy_percent: number;
}

export interface DispatchMetrics {
  total_dispatches: number;
  avg_eta_minutes: number;
  ambulances_available: number;
  ambulances_total: number;
  avg_solver_time_ms: number;
}

export interface Analytics {
  call_metrics: CallMetrics;
  dispatch_metrics: DispatchMetrics;
  recent_calls: unknown[];
  timestamp: string;
}

// ── API Functions ───────────────────────────────────────────────────

export const api = {
  // Menu
  getMenu: () => get<MenuResponse>("/api/menu"),

  // Scenarios
  listScenarios: () => get<Scenario[]>("/api/scenarios"),
  getScenario: (id: string) => get<Scenario>(`/api/scenarios/${id}`),
  createScenario: (body: Partial<Scenario>) => post<Scenario>("/api/scenarios", body),
  deleteScenario: (id: string) => del<{ deleted: string }>(`/api/scenarios/${id}`),

  // Calls
  startCall: (body: { scenario_id?: string; language?: string; caller_phone?: string }) =>
    post<CallStartResponse>("/api/calls/start", body),
  sendInput: (callId: string, input: string) =>
    post<CallInputResponse>(`/api/calls/${callId}/input`, { user_input: input }),
  getCallStatus: (callId: string) => get<CallStatus>(`/api/calls/${callId}/status`),
  endCall: (callId: string) =>
    post<unknown>(`/api/calls/${callId}/end`, { reason: "user_ended" }),
  listActiveCalls: () => get<unknown[]>("/api/calls"),
  getActiveCalls: () => get<unknown[]>("/api/analytics/active-calls"),

  // NLU
  analyzeText: (text: string, language?: string) =>
    post<NluAnalysis>("/api/nlu/analyze", { text, language: language || "en" }),
  listIntents: () => get<{ intent: string; description: string; example: string }[]>("/api/nlu/intents"),

  // Triage
  assessTriage: (body: {
    symptoms: string[];
    severity_score: number;
    patient_age?: number;
    patient_gender?: string;
    medical_history?: string[];
    duration_minutes?: number;
  }) => post<TriageAssessment>("/api/triage/assess", body),
  getResources: () => get<ResourceAvailability>("/api/triage/resources"),
  getTriageRules: () => get<{ rule: string; description: string; action: string }[]>("/api/triage/rules"),

  // Dispatch
  assignAmbulance: (body: {
    patient_location: { lat: number; lon: number };
    priority: string;
    chief_complaint: string;
    estimated_severity?: number;
    ambulance_type_required?: string;
  }) => post<DispatchAssignment>("/api/dispatch/assign", body),
  listAmbulances: () => get<AmbulanceInfo[]>("/api/dispatch/ambulances"),
  resetAmbulance: (id: string) => post<AmbulanceInfo>(`/api/dispatch/ambulances/${id}/reset`),
  resetAllAmbulances: () => post<{ reset_count: number }>("/api/dispatch/reset-all"),

  // Analytics
  getAnalytics: () => get<Analytics>("/api/analytics"),
  getCallHistory: () => get<unknown[]>("/api/analytics/call-history"),
  resetAnalytics: () => post<unknown>("/api/analytics/reset"),

  // Patients
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  listPatients: (search?: string) =>
    get<any[]>(search ? `/api/patients?search=${encodeURIComponent(search)}` : "/api/patients"),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getPatient: (id: string) => get<any>(`/api/patients/${id}`),
  createPatient: (body: {
    name: string; age: number; gender?: string; phone?: string;
    blood_type?: string; allergies?: string[]; medical_history?: string[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  }) => post<any>("/api/patients", body),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  deletePatient: (id: string) => del<any>(`/api/patients/${id}`),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getPatientRisk: (id: string) => get<any>(`/api/patients/${id}/risk-profile`),

  // Logs
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getLogs: (level?: string, source?: string) => {
    const params = new URLSearchParams();
    if (level) params.set("level", level);
    if (source) params.set("source", source);
    const qs = params.toString();
    return get<any[]>(`/api/logs${qs ? "?" + qs : ""}`);
  },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getLogStats: () => get<any>("/api/logs/stats"),
  getLogSources: () => get<string[]>("/api/logs/sources"),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  clearLogs: () => post<any>("/api/logs/clear"),

  // Settings
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getAllSettings: () => get<{ settings: Record<string, any>; categories: string[] }>("/api/settings"),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  updateSetting: (category: string, key: string, value: any) =>
    put<any>(`/api/settings/${category}/${key}`, { value }),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  resetSettings: () => post<any>("/api/settings/reset"),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getHealthCheck: () => get<any>("/api/settings/health/check"),
};
