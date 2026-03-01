import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { TriageAssessment, ResourceAvailability } from "../api/client";
import { Activity } from "lucide-react";

export default function TriagePanel() {
  const [symptoms, setSymptoms] = useState("chest pain");
  const [severity, setSeverity] = useState(7);
  const [age, setAge] = useState(55);
  const [gender, setGender] = useState("male");
  const [history, setHistory] = useState("hypertension");
  const [duration, setDuration] = useState(30);
  const [result, setResult] = useState<TriageAssessment | null>(null);
  const [resources, setResources] = useState<ResourceAvailability | null>(null);
  const [rules, setRules] = useState<{ rule: string; description: string; action: string }[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getResources().then(setResources).catch(console.error);
    api.getTriageRules().then(setRules).catch(console.error);
  }, []);

  const assess = async () => {
    setLoading(true);
    try {
      const res = await api.assessTriage({
        symptoms: symptoms.split(",").map((s) => s.trim()).filter(Boolean),
        severity_score: severity,
        patient_age: age,
        patient_gender: gender,
        medical_history: history.split(",").map((s) => s.trim()).filter(Boolean),
        duration_minutes: duration,
      });
      setResult(res);
      // Refresh resources after assessment
      api.getResources().then(setResources).catch(console.error);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Error");
    }
    setLoading(false);
  };

  const ResourceBar = ({ label, total, available }: { label: string; total: number; available: number }) => {
    const pct = total ? (available / total) * 100 : 0;
    return (
      <div style={{ marginBottom: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
          <span>{label}</span>
          <span style={{ color: "var(--text-muted)" }}>{available}/{total}</span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{
              width: `${pct}%`,
              background: pct > 50 ? "var(--success)" : pct > 20 ? "var(--warning)" : "var(--danger)",
            }}
          />
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="page-header">
        <h2>Triage Assessment</h2>
        <p>Run ILP-based triage solver (SCIP simulation) on patient symptoms</p>
      </div>

      <div className="grid-2">
        {/* ── Input ─────────────────────────────────────── */}
        <div>
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>
              <Activity size={16} style={{ marginRight: 6 }} />
              Patient Assessment
            </h3>
            <div className="form-group">
              <label>Symptoms (comma-separated)</label>
              <input type="text" value={symptoms} onChange={(e) => setSymptoms(e.target.value)} />
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label>Severity (1-10)</label>
                <input type="number" min={1} max={10} value={severity} onChange={(e) => setSeverity(Number(e.target.value))} />
              </div>
              <div className="form-group">
                <label>Patient Age</label>
                <input type="number" min={0} max={120} value={age} onChange={(e) => setAge(Number(e.target.value))} />
              </div>
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label>Gender</label>
                <select value={gender} onChange={(e) => setGender(e.target.value)}>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="form-group">
                <label>Duration (minutes)</label>
                <input type="number" min={0} value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
              </div>
            </div>
            <div className="form-group">
              <label>Medical History (comma-separated)</label>
              <input type="text" value={history} onChange={(e) => setHistory(e.target.value)} />
            </div>
            <button className="btn btn-primary" onClick={assess} disabled={loading}>
              {loading ? "Assessing..." : "Run Triage"}
            </button>
          </div>

          {/* Resources */}
          {resources && (
            <div className="card" style={{ marginTop: 16 }}>
              <h3 style={{ marginBottom: 12 }}>Hospital Resources</h3>
              <ResourceBar label="Emergency Room" total={resources.emergency_room.total} available={resources.emergency_room.available} />
              <ResourceBar label="Urgent Care" total={resources.urgent_care.total} available={resources.urgent_care.available} />
              <ResourceBar label="General Ward" total={resources.general_ward.total} available={resources.general_ward.available} />
              <div className="result-row" style={{ marginTop: 8 }}>
                <span className="result-key">Queue Length</span>
                <span className="result-val">{resources.queue_length}</span>
              </div>
            </div>
          )}
        </div>

        {/* ── Results ──────────────────────────────────── */}
        <div>
          {result ? (
            <div className="card fade-in">
              <h3 style={{ marginBottom: 16 }}>Triage Result</h3>

              <div style={{ textAlign: "center", marginBottom: 16 }}>
                <span
                  className={`badge badge-${result.triage_level}`}
                  style={{ fontSize: 18, padding: "8px 20px" }}
                >
                  {result.triage_level.toUpperCase()}
                </span>
              </div>

              <div className="result-section">
                <div className="result-row">
                  <span className="result-key">Severity Score</span>
                  <span className="result-val">{result.severity_score}/10</span>
                </div>
                <div className="result-row">
                  <span className="result-key">Recommended Facility</span>
                  <span className="result-val">{result.recommended_facility}</span>
                </div>
                <div className="result-row">
                  <span className="result-key">Solver Time</span>
                  <span className="result-val">{result.solver_time_ms}ms</span>
                </div>
              </div>

              <div className="result-section">
                <h4>Clinical Reasoning</h4>
                <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)" }}>
                  {result.clinical_reasoning}
                </p>
              </div>

              {result.risk_factors.length > 0 && (
                <div className="result-section">
                  <h4>Risk Factors</h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {result.risk_factors.map((rf, i) => (
                      <span key={i} className="badge badge-emergency">{rf}</span>
                    ))}
                  </div>
                </div>
              )}

              {result.constraints_applied.length > 0 && (
                <div className="result-section">
                  <h4>Constraints Applied</h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {result.constraints_applied.map((c, i) => (
                      <span key={i} className="entity-tag">{c}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="card" style={{ textAlign: "center", color: "var(--text-muted)", padding: 60 }}>
              Enter patient data and click Run Triage
            </div>
          )}
        </div>
      </div>

      {/* ── Rules Reference ──────────────────────────────── */}
      <div className="card" style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 12 }}>Clinical Triage Rules (ILP Constraints)</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Rule</th>
              <th>Description</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.rule}>
                <td><code style={{ fontSize: 12, color: "var(--accent)" }}>{r.rule}</code></td>
                <td>{r.description}</td>
                <td><span className="badge badge-info">{r.action}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
