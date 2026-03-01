import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Scenario } from "../api/client";
import { Plus, Trash2, Eye } from "lucide-react";

export default function ScenarioManager() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selected, setSelected] = useState<Scenario | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", category: "emergency" });
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.listScenarios().then((s) => { setScenarios(s); setLoading(false); }).catch(console.error);
  };

  useEffect(load, []);

  const handleCreate = async () => {
    try {
      await api.createScenario({
        name: form.name,
        description: form.description,
        category: form.category,
        steps: [
          { step_number: 1, speaker: "system", content: "Welcome. How can I help you today?", input_type: "text" },
          { step_number: 2, speaker: "patient", content: "(Patient describes issue)", input_type: "text" },
        ],
      });
      setShowCreate(false);
      setForm({ name: "", description: "", category: "emergency" });
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this scenario?")) return;
    try {
      await api.deleteScenario(id);
      if (selected?.id === id) setSelected(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  return (
    <div>
      <div className="page-header">
        <h2>Scenario Manager</h2>
        <p>Create, browse, and manage test scenarios for IVR simulations</p>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
          <Plus size={16} /> New Scenario
        </button>
      </div>

      {/* ── Create form ───────────────────────────────────── */}
      {showCreate && (
        <div className="card fade-in" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 12 }}>Create Scenario</h3>
          <div className="grid-2">
            <div className="form-group">
              <label>Name</label>
              <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Allergic Reaction" />
            </div>
            <div className="form-group">
              <label>Category</label>
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                <option value="emergency">Emergency</option>
                <option value="urgent">Urgent</option>
                <option value="routine">Routine</option>
                <option value="billing">Billing</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label>Description</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Describe the scenario..." />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" onClick={handleCreate} disabled={!form.name.trim()}>Create</button>
            <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
        </div>
      )}

      {/* ── Scenario list ─────────────────────────────────── */}
      {loading ? (
        <p style={{ color: "var(--text-muted)" }}>Loading scenarios...</p>
      ) : (
        <div className="grid-2">
          <div>
            <div className="card">
              <h3 style={{ marginBottom: 12 }}>Scenarios ({scenarios.length})</h3>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Steps</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {scenarios.map((s) => (
                    <tr key={s.id}>
                      <td>{s.name}</td>
                      <td>
                        <span className={`badge badge-${
                          s.category === "emergency" ? "emergency"
                          : s.category === "urgent" ? "urgent"
                          : "routine"
                        }`}>
                          {s.category}
                        </span>
                      </td>
                      <td>{s.steps?.length || 0}</td>
                      <td style={{ display: "flex", gap: 4 }}>
                        <button className="btn btn-sm btn-secondary" onClick={() => setSelected(s)}>
                          <Eye size={12} />
                        </button>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDelete(s.id)}>
                          <Trash2 size={12} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* ── Detail panel ──────────────────────────────── */}
          <div>
            {selected ? (
              <div className="card fade-in">
                <h3 style={{ marginBottom: 4 }}>{selected.name}</h3>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12 }}>
                  {selected.description}
                </p>
                <div className="result-section">
                  <h4>Steps</h4>
                  {selected.steps?.map((step, i) => (
                    <div key={i} className="result-row">
                      <span className="result-key">{step.speaker}</span>
                      <span style={{ fontSize: 13 }}>{step.content}</span>
                    </div>
                  ))}
                </div>
                {selected.expected_triage_level && (
                  <div style={{ marginTop: 10, fontSize: 13 }}>
                    Expected triage:{" "}
                    <span className={`badge badge-${selected.expected_triage_level}`}>
                      {selected.expected_triage_level}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="card" style={{ textAlign: "center", color: "var(--text-muted)", padding: 40 }}>
                Select a scenario to view details
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
