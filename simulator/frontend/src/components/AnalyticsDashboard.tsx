import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { Analytics } from "../api/client";
import { BarChart3, RefreshCw } from "lucide-react";

export default function AnalyticsDashboard() {
  const [data, setData] = useState<Analytics | null>(null);
  const [history, setHistory] = useState<Record<string, unknown>[]>([]);
  const [activeCalls, setActiveCalls] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [analytics, hist, active] = await Promise.all([
        api.getAnalytics(),
        api.getCallHistory() as Promise<Record<string, unknown>[]>,
        api.getActiveCalls() as Promise<Record<string, unknown>[]>,
      ]);
      setData(analytics);
      setHistory(hist);
      setActiveCalls(active);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  // Auto-refresh every 3 seconds
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const resetAll = async () => {
    await api.resetAnalytics();
    load();
  };

  if (loading || !data) {
    return (
      <div>
        <div className="page-header">
          <h2>Analytics Dashboard</h2>
        </div>
        <p style={{ color: "var(--text-muted)" }}>Loading analytics...</p>
      </div>
    );
  }

  const cm = data.call_metrics;
  const dm = data.dispatch_metrics;

  return (
    <div>
      <div className="page-header">
        <h2>
          <BarChart3 size={22} style={{ marginRight: 6, verticalAlign: "text-bottom" }} />
          Analytics Dashboard
        </h2>
        <p>Real-time performance metrics for the IVR simulator</p>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "center" }}>
        <button className="btn btn-secondary" onClick={load}>
          <RefreshCw size={14} /> Refresh
        </button>
        <button className="btn btn-danger btn-sm" onClick={resetAll}>
          Reset Analytics
        </button>
        <label style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: "auto", fontSize: 13, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            style={{ width: 14, height: 14 }}
          />
          Auto-refresh (3s)
        </label>
      </div>

      {/* ── Call Metrics ──────────────────────────────────── */}
      <h3 style={{ marginBottom: 12 }}>Call Metrics</h3>
      <div className="grid-4" style={{ marginBottom: 24 }}>
        <div className="stat-card">
          <div className="stat-value">{cm.total_calls}</div>
          <div className="stat-label">Total Calls</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--danger)" }}>
            {cm.emergency_calls}
          </div>
          <div className="stat-label">Emergency</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--success)" }}>
            {cm.routine_calls}
          </div>
          <div className="stat-label">Routine</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{cm.avg_duration_seconds}s</div>
          <div className="stat-label">Avg Duration</div>
        </div>
      </div>

      {/* ── Dispatch Metrics ─────────────────────────────── */}
      <h3 style={{ marginBottom: 12 }}>Dispatch Metrics</h3>
      <div className="grid-4" style={{ marginBottom: 24 }}>
        <div className="stat-card">
          <div className="stat-value">{dm.total_dispatches}</div>
          <div className="stat-label">Dispatches</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "var(--warning)" }}>
            {dm.avg_eta_minutes} min
          </div>
          <div className="stat-label">Avg ETA</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {dm.ambulances_available}/{dm.ambulances_total}
          </div>
          <div className="stat-label">Fleet Available</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{dm.avg_solver_time_ms}ms</div>
          <div className="stat-label">Solver Time</div>
        </div>
      </div>

      {/* ── Performance ──────────────────────────────────── */}
      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Performance Indicators</h3>
          <div className="result-section">
            <div className="result-row">
              <span className="result-key">Avg Response Time</span>
              <span className="result-val">{cm.avg_response_time_ms}ms</span>
            </div>
            <div className="result-row">
              <span className="result-key">Triage Accuracy</span>
              <span className="result-val">{cm.triage_accuracy_percent}%</span>
            </div>
            <div className="result-row">
              <span className="result-key">Emergency Rate</span>
              <span className="result-val">
                {cm.total_calls
                  ? ((cm.emergency_calls / cm.total_calls) * 100).toFixed(1)
                  : 0}
                %
              </span>
            </div>
          </div>
        </div>

        {/* ── Recent Calls ─────────────────────────────────── */}
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Recent Calls ({history.length})</h3>
          {history.length === 0 ? (
            <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
              No completed calls yet. Use the Call Simulator to generate data.
            </p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Call ID</th>
                  <th>Steps</th>
                  <th>Duration</th>
                  <th>Triage</th>
                </tr>
              </thead>
              <tbody>
                {history.map((call: Record<string, unknown>, i: number) => (
                  <tr key={i}>
                    <td style={{ fontSize: 12 }}>
                      {String(call.call_session_id ?? "—")}
                    </td>
                    <td>{String(call.total_steps ?? "—")}</td>
                    <td>{String(call.duration_seconds ?? "—")}s</td>
                    <td>
                      {call.final_triage ? (
                        <span
                          className={`badge badge-${call.final_triage}`}
                        >
                          {String(call.final_triage)}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ── Active Calls (live) ────────────────────────────── */}
      <div className="card" style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 12 }}>
          Active Calls
          {activeCalls.length > 0 && (
            <span style={{
              marginLeft: 8,
              background: "rgba(99,102,241,0.15)",
              color: "var(--accent)",
              padding: "2px 10px",
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 600,
            }}>
              {activeCalls.length} live
            </span>
          )}
        </h3>
        {activeCalls.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
            No active calls. Start a call in the Call Simulator.
          </p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Session ID</th>
                <th>Status</th>
                <th>Step</th>
                <th>Duration</th>
                <th>Scenario</th>
              </tr>
            </thead>
            <tbody>
              {activeCalls.map((c: Record<string, unknown>, i: number) => (
                <tr key={i}>
                  <td style={{ fontSize: 12, fontWeight: 600 }}>{String(c.call_session_id ?? "—")}</td>
                  <td><span className="badge badge-info">{String(c.status ?? "—")}</span></td>
                  <td>{String(c.current_step ?? 0)}</td>
                  <td>{String(c.duration_seconds ?? 0)}s</td>
                  <td style={{ fontSize: 12 }}>{String(c.scenario_id ?? "free-form")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
