import { useState, useRef, useEffect } from "react";
import { api } from "../api/client";
import type { CallInputResponse, Scenario } from "../api/client";
import { Phone, PhoneOff, Send } from "lucide-react";

interface TranscriptEntry {
  step: number;
  speaker: string;
  content: string;
}

export default function CallSimulator() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState("");
  const [callId, setCallId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [input, setInput] = useState("");
  const [lastResult, setLastResult] = useState<CallInputResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listScenarios().then(setScenarios).catch(console.error);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  const startCall = async () => {
    setLoading(true);
    try {
      const res = await api.startCall({
        scenario_id: selectedScenario || undefined,
        language: "en",
        caller_phone: "+1-555-0100",
      });
      setCallId(res.call_session_id);
      setTranscript([{ step: 0, speaker: "system", content: res.greeting }]);
      setLastResult(null);
    } catch (e: unknown) {
      alert(`Error: ${e instanceof Error ? e.message : e}`);
    }
    setLoading(false);
  };

  const sendMessage = async () => {
    if (!callId || !input.trim()) return;
    setLoading(true);
    const userMsg = input.trim();
    setInput("");
    setTranscript((t) => [...t, { step: t.length, speaker: "patient", content: userMsg }]);
    try {
      const res = await api.sendInput(callId, userMsg);
      setLastResult(res);
      setTranscript((t) => [
        ...t,
        { step: t.length, speaker: "system", content: res.system_response },
      ]);
    } catch (e: unknown) {
      alert(`Error: ${e instanceof Error ? e.message : e}`);
    }
    setLoading(false);
  };

  const endCall = async () => {
    if (!callId) return;
    try {
      await api.endCall(callId);
    } catch { /* ignore if already ended */ }
    setCallId(null);
    setLastResult(null);
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div>
      <div className="page-header">
        <h2>Call Simulator</h2>
        <p>Start a simulated IVR call and interact with the AI system</p>
      </div>

      {/* ── Controls ─────────────────────────────────────────── */}
      {!callId && (
        <div className="card fade-in">
          <div className="card-header">
            <h3>New Call</h3>
          </div>
          <div className="form-group">
            <label>Select Scenario (Optional)</label>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
            >
              <option value="">— Free-form call —</option>
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.category})
                </option>
              ))}
            </select>
          </div>
          <button className="btn btn-primary" onClick={startCall} disabled={loading}>
            <Phone size={16} />
            {loading ? "Connecting..." : "Start Call"}
          </button>
        </div>
      )}

      {/* ── Active Call ──────────────────────────────────────── */}
      {callId && (
        <div className="fade-in">
          <div className="card">
            <div className="card-header">
              <h3>
                <span className="pulse" style={{ color: "var(--success)" }}>●</span>{" "}
                Active Call — {callId}
              </h3>
              <button className="btn btn-danger btn-sm" onClick={endCall}>
                <PhoneOff size={14} /> End Call
              </button>
            </div>

            {/* Transcript */}
            <div className="transcript">
              {transcript.map((msg, i) => (
                <div key={i} className={`transcript-msg ${msg.speaker}`}>
                  <div>
                    <div className="msg-label">{msg.speaker}</div>
                    <div className="msg-bubble">{msg.content}</div>
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Type your message (e.g. 'I have chest pain')..."
                disabled={loading}
                autoFocus
              />
              <button
                className="btn btn-primary"
                onClick={sendMessage}
                disabled={loading || !input.trim()}
              >
                <Send size={16} />
              </button>
            </div>
          </div>

          {/* ── NLU / Triage / Dispatch results ────────────── */}
          {lastResult && (
            <div className="grid-2" style={{ marginTop: 16 }}>
              {/* NLU */}
              <div className="card fade-in">
                <h3 style={{ marginBottom: 12 }}>NLU Analysis</h3>
                <div className="result-section">
                  <div className="result-row">
                    <span className="result-key">Intent</span>
                    <span className="result-val">{lastResult.nlu.intent}</span>
                  </div>
                  <div className="result-row">
                    <span className="result-key">Confidence</span>
                    <span className="result-val">
                      {(lastResult.nlu.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="result-row">
                    <span className="result-key">Sentiment</span>
                    <span className="result-val">{lastResult.nlu.sentiment}</span>
                  </div>
                  <div className="result-row">
                    <span className="result-key">Distress</span>
                    <span className="result-val">
                      {(lastResult.nlu.distress_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                {lastResult.nlu.entities &&
                  Object.keys(lastResult.nlu.entities).length > 0 && (
                    <div style={{ marginTop: 10 }}>
                      <h4
                        style={{
                          fontSize: 11,
                          color: "var(--text-muted)",
                          textTransform: "uppercase",
                          marginBottom: 6,
                        }}
                      >
                        Entities
                      </h4>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                        {Object.entries(lastResult.nlu.entities).map(
                          ([key, val]) => (
                            <span key={key} className="entity-tag">
                              <span className="entity-type">{key}:</span>{" "}
                              {Array.isArray(val) ? val.join(", ") : String(val)}
                            </span>
                          )
                        )}
                      </div>
                    </div>
                  )}
              </div>

              {/* Triage */}
              {lastResult.triage && (
                <div className="card fade-in">
                  <h3 style={{ marginBottom: 12 }}>Triage Assessment</h3>
                  <div className="result-section">
                    <div className="result-row">
                      <span className="result-key">Level</span>
                      <span
                        className={`badge badge-${lastResult.triage.triage_level}`}
                      >
                        {lastResult.triage.triage_level}
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">Severity</span>
                      <span className="result-val">
                        {lastResult.triage.severity_score}/10
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">Facility</span>
                      <span className="result-val">
                        {lastResult.triage.recommended_facility}
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">Solver Time</span>
                      <span className="result-val">
                        {lastResult.triage.solver_time_ms}ms
                      </span>
                    </div>
                  </div>
                  <p
                    style={{
                      fontSize: 12,
                      color: "var(--text-secondary)",
                      marginTop: 10,
                      lineHeight: 1.5,
                    }}
                  >
                    {lastResult.triage.clinical_reasoning}
                  </p>
                </div>
              )}

              {/* Dispatch */}
              {lastResult.dispatch && (
                <div className="card fade-in">
                  <h3 style={{ marginBottom: 12 }}>Ambulance Dispatch</h3>
                  <div className="result-section">
                    <div className="result-row">
                      <span className="result-key">Ambulance</span>
                      <span className="result-val">
                        {lastResult.dispatch.assigned_ambulance}
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">Type</span>
                      <span className="badge badge-info">
                        {lastResult.dispatch.ambulance_type}
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">ETA</span>
                      <span className="result-val">
                        {lastResult.dispatch.eta_minutes} min
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">Crew</span>
                      <span className="result-val">
                        {lastResult.dispatch.crew_size} members
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
