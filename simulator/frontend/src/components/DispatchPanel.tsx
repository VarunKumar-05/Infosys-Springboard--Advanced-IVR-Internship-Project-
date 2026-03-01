import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { AmbulanceInfo, DispatchAssignment } from "../api/client";
import { Truck, MapPin, RotateCcw } from "lucide-react";

const statusColor: Record<string, string> = {
  available: "var(--success)",
  dispatched: "var(--warning)",
  en_route: "var(--accent)",
  at_scene: "var(--danger)",
  returning: "var(--text-muted)",
};

export default function DispatchPanel() {
  const [ambulances, setAmbulances] = useState<AmbulanceInfo[]>([]);
  const [lat, setLat] = useState(40.7128);
  const [lon, setLon] = useState(-74.006);
  const [priority, setPriority] = useState("critical");
  const [complaint, setComplaint] = useState("chest pain, difficulty breathing");
  const [severity, setSeverity] = useState(8);
  const [ambType, setAmbType] = useState("ALS");
  const [result, setResult] = useState<DispatchAssignment | null>(null);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadAmbulances = () => {
    api.listAmbulances().then(setAmbulances).catch(console.error);
  };

  useEffect(loadAmbulances, []);

  // Auto-refresh fleet every 3 seconds
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(loadAmbulances, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const dispatch = async () => {
    setLoading(true);
    try {
      const res = await api.assignAmbulance({
        patient_location: { lat, lon },
        priority,
        chief_complaint: complaint,
        estimated_severity: severity,
        ambulance_type_required: ambType,
      });
      setResult(res);
      loadAmbulances(); // refresh fleet status
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Error");
    }
    setLoading(false);
  };

  const resetAll = async () => {
    await api.resetAllAmbulances();
    setResult(null);
    loadAmbulances();
  };

  const resetOne = async (id: string) => {
    await api.resetAmbulance(id);
    loadAmbulances();
  };

  const available = ambulances.filter((a) => a.status === "available").length;

  return (
    <div>
      <div className="page-header">
        <h2>Ambulance Dispatch</h2>
        <p>Run ILP dispatch solver (Gurobi simulation) to assign optimal ambulance</p>
      </div>

      <div className="grid-2">
        {/* ── Dispatch form ──────────────────────────────── */}
        <div>
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>
              <Truck size={16} style={{ marginRight: 6 }} />
              Dispatch Request
            </h3>
            <div className="grid-2">
              <div className="form-group">
                <label>Latitude</label>
                <input type="number" step="0.0001" value={lat} onChange={(e) => setLat(Number(e.target.value))} />
              </div>
              <div className="form-group">
                <label>Longitude</label>
                <input type="number" step="0.0001" value={lon} onChange={(e) => setLon(Number(e.target.value))} />
              </div>
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label>Priority</label>
                <select value={priority} onChange={(e) => setPriority(e.target.value)}>
                  <option value="critical">Critical</option>
                  <option value="urgent">Urgent</option>
                  <option value="standard">Standard</option>
                </select>
              </div>
              <div className="form-group">
                <label>Ambulance Type</label>
                <select value={ambType} onChange={(e) => setAmbType(e.target.value)}>
                  <option value="ALS">ALS (Advanced Life Support)</option>
                  <option value="BLS">BLS (Basic Life Support)</option>
                  <option value="MICU">MICU (Mobile ICU)</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Chief Complaint</label>
              <input type="text" value={complaint} onChange={(e) => setComplaint(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Estimated Severity (1-10)</label>
              <input type="number" min={1} max={10} value={severity} onChange={(e) => setSeverity(Number(e.target.value))} />
            </div>
            <button className="btn btn-primary" onClick={dispatch} disabled={loading}>
              <MapPin size={16} />
              {loading ? "Dispatching..." : "Dispatch Ambulance"}
            </button>
          </div>

          {/* Result */}
          {result && (
            <div className="card fade-in" style={{ marginTop: 16 }}>
              <h3 style={{ marginBottom: 12 }}>Dispatch Result</h3>
              <div className="result-section">
                <div className="result-row">
                  <span className="result-key">Ambulance</span>
                  <span className="result-val">{result.assigned_ambulance}</span>
                </div>
                <div className="result-row">
                  <span className="result-key">Type</span>
                  <span className="badge badge-info">{result.ambulance_type}</span>
                </div>
                <div className="result-row">
                  <span className="result-key">Distance</span>
                  <span className="result-val">{result.distance_km} km</span>
                </div>
                <div className="result-row">
                  <span className="result-key">ETA</span>
                  <span className="result-val" style={{ color: "var(--warning)" }}>
                    {result.eta_minutes} min
                  </span>
                </div>
                <div className="result-row">
                  <span className="result-key">Crew Size</span>
                  <span className="result-val">{result.crew_size}</span>
                </div>
                <div className="result-row">
                  <span className="result-key">Solver Time</span>
                  <span className="result-val">{result.solver_time_ms}ms</span>
                </div>
              </div>
              <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>
                {result.reasoning}
              </p>
            </div>
          )}
        </div>

        {/* ── Fleet status ──────────────────────────────── */}
        <div>
          <div className="card">
            <div className="card-header">
              <h3>Fleet Status ({available}/{ambulances.length} available)</h3>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={autoRefresh}
                    onChange={(e) => setAutoRefresh(e.target.checked)}
                    style={{ width: 13, height: 13 }}
                  />
                  Live
                </label>
                <button className="btn btn-sm btn-secondary" onClick={loadAmbulances}>
                  <RotateCcw size={12} /> Refresh
                </button>
                <button className="btn btn-sm btn-secondary" onClick={resetAll}>
                  <RotateCcw size={12} /> Reset All
                </button>
              </div>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Crew</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {ambulances.map((a) => (
                  <tr key={a.id}>
                    <td style={{ fontWeight: 600 }}>{a.id}</td>
                    <td><span className="badge badge-info">{a.type}</span></td>
                    <td>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                        <span
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            background: statusColor[a.status] ?? "var(--text-muted)",
                          }}
                        />
                        {a.status}
                      </span>
                    </td>
                    <td>{a.crew_size}</td>
                    <td>
                      {a.status !== "available" && (
                        <button className="btn btn-sm btn-secondary" onClick={() => resetOne(a.id)}>
                          <RotateCcw size={10} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
