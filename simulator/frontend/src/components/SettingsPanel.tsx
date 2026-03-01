import { useState, useEffect } from "react";
import { api } from "../api/client";
import { Settings as SettingsIcon, Save, RotateCcw, Heart, ChevronDown, ChevronRight } from "lucide-react";

interface SettingValue {
  [key: string]: string | number | boolean | string[];
}

interface HealthService {
  status: string;
  engine?: string;
  solver?: string;
  fleet_size?: number;
  max_calls?: number;
  type?: string;
}

interface HealthCheck {
  status: string;
  timestamp: string;
  services: Record<string, HealthService>;
}

export default function SettingsPanel() {
  const [settings, setSettings] = useState<Record<string, SettingValue>>({});
  const [categories, setCategories] = useState<string[]>([]);
  const [health, setHealth] = useState<HealthCheck | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const fetchAll = async () => {
    try {
      const [settingsData, healthData] = await Promise.all([
        api.getAllSettings(),
        api.getHealthCheck(),
      ]);
      setSettings(settingsData.settings);
      setCategories(settingsData.categories);
      // Expand all categories by default
      const exp: Record<string, boolean> = {};
      settingsData.categories.forEach((c: string) => (exp[c] = true));
      setExpanded(exp);
      setHealth(healthData);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchAll(); }, []);

  const toggleCategory = (cat: string) => {
    setExpanded((prev) => ({ ...prev, [cat]: !prev[cat] }));
  };

  const handleUpdate = async (category: string, key: string, value: unknown) => {
    setSaving(`${category}.${key}`);
    try {
      await api.updateSetting(category, key, value);
      // Refresh to reflect
      const data = await api.getAllSettings();
      setSettings(data.settings);
      setMessage(`Updated ${category}.${key}`);
      setTimeout(() => setMessage(null), 2000);
    } catch (e) { console.error(e); }
    setSaving(null);
  };

  const handleReset = async () => {
    await api.resetSettings();
    fetchAll();
    setMessage("Settings reset to defaults");
    setTimeout(() => setMessage(null), 2000);
  };

  const renderValue = (category: string, key: string, value: unknown) => {
    const savingKey = `${category}.${key}`;

    if (typeof value === "boolean") {
      return (
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={value}
            onChange={(e) => handleUpdate(category, key, e.target.checked)}
            style={{ width: 16, height: 16 }}
          />
          <span style={{ fontSize: 12, color: value ? "#22c55e" : "var(--text-muted)" }}>
            {value ? "Enabled" : "Disabled"}
          </span>
          {saving === savingKey && <span style={{ fontSize: 10, color: "var(--accent)" }}>Saving...</span>}
        </label>
      );
    }

    if (typeof value === "number") {
      return (
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <input
            type="number"
            defaultValue={value}
            onBlur={(e) => {
              const v = parseFloat(e.target.value);
              if (!isNaN(v) && v !== value) handleUpdate(category, key, v);
            }}
            style={{ width: 100, fontSize: 13 }}
          />
          {saving === savingKey && <span style={{ fontSize: 10, color: "var(--accent)" }}>Saving...</span>}
        </div>
      );
    }

    if (Array.isArray(value)) {
      return (
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {value.map((v, i) => (
            <span key={i} style={{ background: "rgba(99,102,241,0.1)", color: "var(--accent)", padding: "2px 8px", borderRadius: 4, fontSize: 12 }}>
              {String(v)}
            </span>
          ))}
        </div>
      );
    }

    return (
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <input
          type="text"
          defaultValue={String(value)}
          onBlur={(e) => {
            if (e.target.value !== String(value)) handleUpdate(category, key, e.target.value);
          }}
          style={{ flex: 1, fontSize: 13, maxWidth: 350 }}
        />
        {saving === savingKey && <span style={{ fontSize: 10, color: "var(--accent)" }}>Saving...</span>}
      </div>
    );
  };

  const categoryIcons: Record<string, string> = {
    nlu: "🧠",
    triage: "🏥",
    dispatch: "🚑",
    ivr: "📞",
    system: "⚙️",
  };

  return (
    <div>
      <div className="page-header">
        <h2><SettingsIcon size={22} style={{ marginRight: 8, verticalAlign: "middle" }} />Settings</h2>
        <p>Configure NLU, triage, dispatch, IVR, and system parameters</p>
      </div>

      {/* Action bar */}
      <div className="card" style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <button className="btn btn-primary" onClick={handleReset}><RotateCcw size={14} /> Reset to Defaults</button>
        {message && (
          <span style={{ fontSize: 13, color: "#22c55e", marginLeft: 8 }}>
            <Save size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />{message}
          </span>
        )}
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{categories.length} categories • {Object.values(settings).reduce((a, c) => a + Object.keys(c).length, 0)} settings</span>
      </div>

      {/* Health check */}
      {health && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <Heart size={18} style={{ color: health.status === "healthy" ? "#22c55e" : "#ef4444" }} />
            <h3 style={{ margin: 0 }}>System Health</h3>
            <span style={{
              background: health.status === "healthy" ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
              color: health.status === "healthy" ? "#22c55e" : "#ef4444",
              padding: "2px 10px",
              borderRadius: 6,
              fontWeight: 700,
              fontSize: 12,
            }}>
              {health.status.toUpperCase()}
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10 }}>
            {Object.entries(health.services).map(([name, svc]) => (
              <div
                key={name}
                style={{
                  padding: "10px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  background: "var(--bg-primary)",
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{name.replace(/_/g, " ")}</div>
                <div style={{ fontSize: 12, color: svc.status === "operational" ? "#22c55e" : "#ef4444" }}>
                  {svc.status}
                </div>
                {svc.engine && <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{svc.engine}</div>}
                {svc.solver && <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{svc.solver}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Settings categories */}
      {categories.map((cat) => (
        <div className="card" key={cat} style={{ marginBottom: 12 }}>
          <div
            onClick={() => toggleCategory(cat)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              cursor: "pointer",
              userSelect: "none",
            }}
          >
            {expanded[cat] ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            <span style={{ fontSize: 18 }}>{categoryIcons[cat] || "📦"}</span>
            <h3 style={{ margin: 0, textTransform: "capitalize" }}>{cat}</h3>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              ({Object.keys(settings[cat] || {}).length} settings)
            </span>
          </div>

          {expanded[cat] && settings[cat] && (
            <div style={{ marginTop: 12 }}>
              {Object.entries(settings[cat]).map(([key, value]) => (
                <div
                  key={key}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 0",
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  <div style={{ minWidth: 220 }}>
                    <code style={{ fontSize: 13, color: "var(--accent)" }}>{key}</code>
                  </div>
                  <div>{renderValue(cat, key, value)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
