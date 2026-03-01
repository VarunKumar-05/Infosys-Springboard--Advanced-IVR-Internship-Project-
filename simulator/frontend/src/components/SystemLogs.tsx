import { useState, useEffect } from "react";
import { api } from "../api/client";
import { FileText, Filter, Trash2, RefreshCw, AlertTriangle, AlertCircle, Info } from "lucide-react";

interface LogEntry {
  id: string;
  timestamp: string;
  level: string;
  source: string;
  action: string;
  message: string;
  details: Record<string, unknown> | null;
}

interface LogStats {
  total: number;
  by_level: Record<string, number>;
  by_source: Record<string, number>;
}

export default function SystemLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [stats, setStats] = useState<LogStats | null>(null);
  const [levelFilter, setLevelFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [sources, setSources] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const [logsData, statsData, srcData] = await Promise.all([
        api.getLogs(levelFilter || undefined, sourceFilter || undefined),
        api.getLogStats(),
        api.getLogSources(),
      ]);
      setLogs(logsData);
      setStats(statsData);
      setSources(srcData);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { fetchLogs(); }, [levelFilter, sourceFilter]);

  const clearLogs = async () => {
    await api.clearLogs();
    fetchLogs();
  };

  const levelIcon = (level: string) => {
    switch (level) {
      case "ERROR": case "CRITICAL": return <AlertCircle size={14} style={{ color: "#ef4444" }} />;
      case "WARNING": return <AlertTriangle size={14} style={{ color: "#f59e0b" }} />;
      default: return <Info size={14} style={{ color: "#6366f1" }} />;
    }
  };

  const levelColor = (level: string) => {
    switch (level) {
      case "ERROR": case "CRITICAL": return "#ef4444";
      case "WARNING": return "#f59e0b";
      default: return "#6366f1";
    }
  };

  const fmtTime = (iso: string) => {
    try { return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }); }
    catch { return iso; }
  };

  return (
    <div>
      <div className="page-header">
        <h2><FileText size={22} style={{ marginRight: 8, verticalAlign: "middle" }} />System Logs</h2>
        <p>Monitor system activity, errors, and audit trail</p>
      </div>

      {/* Stats bar */}
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 16 }}>
          {[
            { label: "Total", value: stats.total, color: "var(--text-primary)" },
            { label: "INFO", value: stats.by_level["INFO"] || 0, color: "#6366f1" },
            { label: "WARNING", value: stats.by_level["WARNING"] || 0, color: "#f59e0b" },
            { label: "ERROR", value: stats.by_level["ERROR"] || 0, color: "#ef4444" },
            { label: "Sources", value: Object.keys(stats.by_source).length, color: "#22c55e" },
          ].map((s) => (
            <div className="card" key={s.label} style={{ textAlign: "center", padding: "12px 8px" }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="card" style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <Filter size={16} style={{ color: "var(--text-muted)" }} />
        <select value={levelFilter} onChange={(e) => setLevelFilter(e.target.value)} style={{ minWidth: 120 }}>
          <option value="">All Levels</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>
        <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)} style={{ minWidth: 120 }}>
          <option value="">All Sources</option>
          {sources.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <div style={{ flex: 1 }} />
        <button className="btn btn-primary" onClick={fetchLogs}><RefreshCw size={14} /> Refresh</button>
        <button className="btn" onClick={clearLogs}><Trash2 size={14} /> Clear</button>
      </div>

      {/* Log list */}
      <div className="card" style={{ padding: 0, maxHeight: 500, overflowY: "auto" }}>
        {loading && <p style={{ padding: 16, color: "var(--text-muted)" }}>Loading...</p>}
        {logs.length === 0 && !loading && (
          <p style={{ padding: 24, textAlign: "center", color: "var(--text-muted)" }}>No log entries found</p>
        )}
        {logs.map((log) => (
          <div
            key={log.id}
            onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
            style={{
              padding: "10px 16px",
              borderBottom: "1px solid var(--border)",
              cursor: "pointer",
              background: expandedId === log.id ? "rgba(99,102,241,0.05)" : "transparent",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {levelIcon(log.level)}
              <span style={{
                fontSize: 10,
                fontWeight: 700,
                padding: "1px 6px",
                borderRadius: 4,
                background: levelColor(log.level) + "22",
                color: levelColor(log.level),
                minWidth: 52,
                textAlign: "center",
              }}>
                {log.level}
              </span>
              <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "monospace" }}>
                {fmtTime(log.timestamp)}
              </span>
              <span style={{
                fontSize: 10,
                color: "var(--accent)",
                background: "rgba(99,102,241,0.1)",
                padding: "1px 6px",
                borderRadius: 4,
              }}>
                {log.source}
              </span>
              <span style={{ fontSize: 13, flex: 1 }}>{log.message}</span>
            </div>

            {expandedId === log.id && (
              <div style={{
                marginTop: 8,
                padding: "8px 12px",
                background: "var(--bg-primary)",
                borderRadius: 6,
                fontSize: 12,
              }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, marginBottom: 8 }}>
                  <div><strong>ID:</strong> {log.id}</div>
                  <div><strong>Action:</strong> {log.action}</div>
                  <div><strong>Source:</strong> {log.source}</div>
                  <div><strong>Timestamp:</strong> {log.timestamp}</div>
                </div>
                {log.details && (
                  <pre style={{
                    background: "var(--bg-secondary)",
                    padding: 8,
                    borderRadius: 4,
                    fontSize: 11,
                    overflow: "auto",
                    color: "var(--text-secondary)",
                    margin: 0,
                  }}>
                    {JSON.stringify(log.details, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
