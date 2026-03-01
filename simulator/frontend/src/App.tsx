import { useState, useEffect } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import CallSimulator from "./components/CallSimulator";
import ScenarioManager from "./components/ScenarioManager";
import NluAnalyzer from "./components/NluAnalyzer";
import TriagePanel from "./components/TriagePanel";
import DispatchPanel from "./components/DispatchPanel";
import AnalyticsDashboard from "./components/AnalyticsDashboard";
import PatientRecords from "./components/PatientRecords";
import SystemLogs from "./components/SystemLogs";
import SettingsPanel from "./components/SettingsPanel";
import { api } from "./api/client";
import type { MenuItem } from "./api/client";
import {
  Phone, List, Brain, Activity, Truck, BarChart3,
  User, FileText, Settings,
} from "lucide-react";

const iconMap: Record<string, React.ReactNode> = {
  phone:       <Phone size={28} />,
  list:        <List size={28} />,
  brain:       <Brain size={28} />,
  activity:    <Activity size={28} />,
  truck:       <Truck size={28} />,
  "bar-chart": <BarChart3 size={28} />,
  user:        <User size={28} />,
  "file-text": <FileText size={28} />,
  settings:    <Settings size={28} />,
};

function HomePage({ items }: { items: MenuItem[] }) {
  const navigate = useNavigate();
  return (
    <div>
      <div className="page-header">
        <h2>Welcome to the AI Hospital IVR Simulator</h2>
        <p>
          Interactive web simulator for the AI-Based Hospital IVR System.
          Select a module below or use the sidebar to navigate.
        </p>
      </div>

      <div className="grid-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="card"
            style={{ cursor: "pointer", transition: "border-color 0.15s" }}
            onClick={() => navigate(item.route)}
            onMouseEnter={(e) =>
              (e.currentTarget.style.borderColor = "var(--accent)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.borderColor = "var(--border)")
            }
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                marginBottom: 10,
                color: "var(--accent)",
              }}
            >
              {iconMap[item.icon] || <List size={28} />}
              <h3 style={{ fontSize: 16 }}>{item.label}</h3>
            </div>
            <p
              style={{
                fontSize: 13,
                color: "var(--text-secondary)",
                lineHeight: 1.5,
                marginBottom: 12,
              }}
            >
              {item.description}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {item.endpoints.slice(0, 3).map((ep) => (
                <code
                  key={ep}
                  style={{
                    fontSize: 10,
                    background: "var(--bg-primary)",
                    padding: "2px 6px",
                    borderRadius: 4,
                    color: "var(--text-muted)",
                  }}
                >
                  {ep}
                </code>
              ))}
              {item.endpoints.length > 3 && (
                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                  +{item.endpoints.length - 3} more
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: 24 }}>
        <h3 style={{ marginBottom: 8 }}>Quick Start</h3>
        <ol
          style={{
            paddingLeft: 20,
            fontSize: 13,
            color: "var(--text-secondary)",
            lineHeight: 2,
          }}
        >
          <li>Go to <strong>Call Simulator</strong> to start a simulated IVR call</li>
          <li>Try the <strong>NLU Analyzer</strong> to test intent detection on custom text</li>
          <li>Use <strong>Triage Assessment</strong> to run the ILP solver on symptoms</li>
          <li>Test <strong>Ambulance Dispatch</strong> to see the Gurobi ILP optimizer</li>
          <li>Check <strong>Analytics</strong> to view aggregated metrics</li>
          <li>
            Visit{" "}
            <a href="/docs" target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>
              /docs
            </a>{" "}
            for the interactive Swagger UI
          </li>
        </ol>
      </div>
    </div>
  );
}

export default function App() {
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);

  useEffect(() => {
    api.getMenu().then((m) => setMenuItems(m.items)).catch(console.error);
  }, []);

  return (
    <div className="app-layout">
      <Sidebar items={menuItems} />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<HomePage items={menuItems} />} />
          <Route path="/simulator" element={<CallSimulator />} />
          <Route path="/scenarios" element={<ScenarioManager />} />
          <Route path="/nlu" element={<NluAnalyzer />} />
          <Route path="/triage" element={<TriagePanel />} />
          <Route path="/dispatch" element={<DispatchPanel />} />
          <Route path="/analytics" element={<AnalyticsDashboard />} />
          <Route path="/patients" element={<PatientRecords />} />
          <Route path="/logs" element={<SystemLogs />} />
          <Route path="/settings" element={<SettingsPanel />} />
        </Routes>
      </main>
    </div>
  );
}
