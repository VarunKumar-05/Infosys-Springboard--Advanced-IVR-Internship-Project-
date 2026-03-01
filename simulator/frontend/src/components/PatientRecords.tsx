import { useState, useEffect } from "react";
import { api } from "../api/client";
import { User, Search, Shield, Plus, Trash2, RefreshCw } from "lucide-react";

interface Patient {
  id: string;
  name: string;
  age: number;
  gender: string;
  phone: string;
  blood_type: string;
  allergies: string[];
  medical_history: string[];
  emergency_contact: { name: string; phone: string; relation: string } | null;
  insurance: { provider: string; policy: string; status: string } | null;
  last_visit: string | null;
  created_at: string;
}

interface RiskProfile {
  patient_id: string;
  risk_level: string;
  risk_score: number;
  risk_factors: string[];
  recommendation: string;
}

export default function PatientRecords() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Patient | null>(null);
  const [riskProfile, setRiskProfile] = useState<RiskProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [newPatient, setNewPatient] = useState({ name: "", age: 30, gender: "unknown", phone: "", blood_type: "", allergies: "", history: "" });

  const fetchPatients = async () => {
    setLoading(true);
    try {
      const data = await api.listPatients(search || undefined);
      setPatients(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { fetchPatients(); }, []);

  const handleSearch = () => fetchPatients();

  const selectPatient = async (p: Patient) => {
    setSelected(p);
    setRiskProfile(null);
    try {
      const risk = await api.getPatientRisk(p.id);
      setRiskProfile(risk);
    } catch (e) { console.error(e); }
  };

  const handleAdd = async () => {
    try {
      await api.createPatient({
        name: newPatient.name,
        age: newPatient.age,
        gender: newPatient.gender,
        phone: newPatient.phone,
        blood_type: newPatient.blood_type,
        allergies: newPatient.allergies ? newPatient.allergies.split(",").map(s => s.trim()) : [],
        medical_history: newPatient.history ? newPatient.history.split(",").map(s => s.trim()) : [],
      });
      setShowAdd(false);
      setNewPatient({ name: "", age: 30, gender: "unknown", phone: "", blood_type: "", allergies: "", history: "" });
      fetchPatients();
    } catch (e) { console.error(e); }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deletePatient(id);
      if (selected?.id === id) { setSelected(null); setRiskProfile(null); }
      fetchPatients();
    } catch (e) { console.error(e); }
  };

  const riskColor = (level: string) =>
    level === "HIGH" ? "#ef4444" : level === "MODERATE" ? "#f59e0b" : "#22c55e";

  return (
    <div>
      <div className="page-header">
        <h2><User size={22} style={{ marginRight: 8, verticalAlign: "middle" }} />Patient Records</h2>
        <p>Browse, register, and manage patient records with risk profiling</p>
      </div>

      {/* Search + actions */}
      <div className="card" style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 16 }}>
        <Search size={16} style={{ color: "var(--text-muted)" }} />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search by name or phone..."
          style={{ flex: 1 }}
        />
        <button className="btn btn-primary" onClick={handleSearch}><RefreshCw size={14} /> Search</button>
        <button className="btn btn-primary" onClick={() => setShowAdd(!showAdd)}><Plus size={14} /> Add Patient</button>
      </div>

      {/* Add patient form */}
      {showAdd && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 12 }}>Register New Patient</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
            <div>
              <label>Name *</label>
              <input value={newPatient.name} onChange={(e) => setNewPatient({ ...newPatient, name: e.target.value })} placeholder="Full name" />
            </div>
            <div>
              <label>Age *</label>
              <input type="number" value={newPatient.age} onChange={(e) => setNewPatient({ ...newPatient, age: +e.target.value })} />
            </div>
            <div>
              <label>Gender</label>
              <select value={newPatient.gender} onChange={(e) => setNewPatient({ ...newPatient, gender: e.target.value })}>
                <option value="unknown">Unknown</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
              </select>
            </div>
            <div>
              <label>Phone</label>
              <input value={newPatient.phone} onChange={(e) => setNewPatient({ ...newPatient, phone: e.target.value })} placeholder="+1-555-0000" />
            </div>
            <div>
              <label>Blood Type</label>
              <input value={newPatient.blood_type} onChange={(e) => setNewPatient({ ...newPatient, blood_type: e.target.value })} placeholder="O+, A-, etc" />
            </div>
            <div>
              <label>Allergies (comma-sep)</label>
              <input value={newPatient.allergies} onChange={(e) => setNewPatient({ ...newPatient, allergies: e.target.value })} placeholder="Penicillin, Latex" />
            </div>
            <div style={{ gridColumn: "span 3" }}>
              <label>Medical History (comma-sep)</label>
              <input value={newPatient.history} onChange={(e) => setNewPatient({ ...newPatient, history: e.target.value })} placeholder="hypertension, diabetes" />
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleAdd} style={{ marginTop: 12 }} disabled={!newPatient.name}>Register Patient</button>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: 16 }}>
        {/* Patient list */}
        <div className="card" style={{ maxHeight: 550, overflowY: "auto" }}>
          <h3 style={{ marginBottom: 12 }}>Patients ({patients.length})</h3>
          {loading && <p style={{ color: "var(--text-muted)" }}>Loading...</p>}
          {patients.map((p) => (
            <div
              key={p.id}
              onClick={() => selectPatient(p)}
              style={{
                padding: "10px 12px",
                borderRadius: 8,
                marginBottom: 6,
                cursor: "pointer",
                border: selected?.id === p.id ? "1px solid var(--accent)" : "1px solid var(--border)",
                background: selected?.id === p.id ? "rgba(99,102,241,0.08)" : "transparent",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <strong style={{ fontSize: 14 }}>{p.name}</strong>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                  {p.id} • Age {p.age} • {p.gender} • {p.blood_type || "—"}
                </div>
              </div>
              <button
                className="btn"
                style={{ padding: "4px 8px", fontSize: 11 }}
                onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }}
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>

        {/* Patient detail + risk */}
        <div>
          {selected ? (
            <>
              <div className="card" style={{ marginBottom: 16 }}>
                <h3 style={{ marginBottom: 12 }}>{selected.name}</h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 13 }}>
                  <div><strong>ID:</strong> {selected.id}</div>
                  <div><strong>Age:</strong> {selected.age}</div>
                  <div><strong>Gender:</strong> {selected.gender}</div>
                  <div><strong>Phone:</strong> {selected.phone || "—"}</div>
                  <div><strong>Blood Type:</strong> {selected.blood_type || "—"}</div>
                  <div><strong>Last Visit:</strong> {selected.last_visit || "Never"}</div>
                </div>

                {selected.allergies.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <strong>Allergies:</strong>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                      {selected.allergies.map((a) => (
                        <span key={a} style={{ background: "rgba(239,68,68,0.15)", color: "#ef4444", padding: "2px 8px", borderRadius: 4, fontSize: 12 }}>{a}</span>
                      ))}
                    </div>
                  </div>
                )}

                {selected.medical_history.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <strong>Medical History:</strong>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                      {selected.medical_history.map((h) => (
                        <span key={h} style={{ background: "rgba(99,102,241,0.15)", color: "var(--accent)", padding: "2px 8px", borderRadius: 4, fontSize: 12 }}>{h}</span>
                      ))}
                    </div>
                  </div>
                )}

                {selected.emergency_contact && (
                  <div style={{ marginTop: 12, fontSize: 13 }}>
                    <strong>Emergency Contact:</strong> {selected.emergency_contact.name} ({selected.emergency_contact.relation}) — {selected.emergency_contact.phone}
                  </div>
                )}

                {selected.insurance && (
                  <div style={{ marginTop: 8, fontSize: 13 }}>
                    <strong>Insurance:</strong> {selected.insurance.provider} — {selected.insurance.policy}{" "}
                    <span style={{ color: selected.insurance.status === "active" ? "#22c55e" : "#ef4444" }}>({selected.insurance.status})</span>
                  </div>
                )}
              </div>

              {riskProfile && (
                <div className="card">
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                    <Shield size={20} style={{ color: riskColor(riskProfile.risk_level) }} />
                    <h3 style={{ margin: 0 }}>Risk Profile</h3>
                    <span style={{
                      background: riskColor(riskProfile.risk_level) + "22",
                      color: riskColor(riskProfile.risk_level),
                      padding: "2px 10px",
                      borderRadius: 6,
                      fontWeight: 700,
                      fontSize: 13,
                    }}>
                      {riskProfile.risk_level} (Score: {riskProfile.risk_score})
                    </span>
                  </div>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8 }}>
                    <strong>Recommendation:</strong> {riskProfile.recommendation}
                  </p>
                  {riskProfile.risk_factors.length > 0 && (
                    <ul style={{ fontSize: 13, paddingLeft: 20, color: "var(--text-secondary)" }}>
                      {riskProfile.risk_factors.map((f, i) => <li key={i}>{f}</li>)}
                    </ul>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="card" style={{ textAlign: "center", padding: 40, color: "var(--text-muted)" }}>
              <User size={40} style={{ marginBottom: 10, opacity: 0.3 }} />
              <p>Select a patient to view details and risk profile</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
