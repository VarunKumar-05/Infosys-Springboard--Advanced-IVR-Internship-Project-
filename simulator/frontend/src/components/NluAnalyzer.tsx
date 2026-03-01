import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { NluAnalysis } from "../api/client";
import { Brain, Send } from "lucide-react";

export default function NluAnalyzer() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<NluAnalysis | null>(null);
  const [intents, setIntents] = useState<{ intent: string; description: string; example: string }[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.listIntents().then(setIntents).catch(console.error);
  }, []);

  const analyze = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const res = await api.analyzeText(text.trim());
      setResult(res);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Error");
    }
    setLoading(false);
  };

  const tryExample = (example: string) => {
    setText(example);
  };

  return (
    <div>
      <div className="page-header">
        <h2>NLU Analyzer</h2>
        <p>Analyze text for intent, entities, and sentiment using the mock NLU engine</p>
      </div>

      <div className="grid-2">
        {/* ── Input ─────────────────────────────────────────── */}
        <div>
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>
              <Brain size={16} style={{ marginRight: 6 }} />
              Text Analysis
            </h3>
            <div className="form-group">
              <label>Input Text</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder='Type a patient message, e.g. "I am having severe chest pain and difficulty breathing"'
                rows={4}
              />
            </div>
            <button className="btn btn-primary" onClick={analyze} disabled={loading || !text.trim()}>
              <Send size={16} />
              {loading ? "Analyzing..." : "Analyze"}
            </button>
          </div>

          {/* Quick examples */}
          <div className="card" style={{ marginTop: 16 }}>
            <h3 style={{ marginBottom: 12 }}>Quick Examples</h3>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {intents.slice(0, 8).map((i) => (
                <button
                  key={i.intent}
                  className="btn btn-sm btn-secondary"
                  onClick={() => tryExample(i.example)}
                  title={i.description}
                >
                  {i.example}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── Results ───────────────────────────────────────── */}
        <div>
          {result ? (
            <div className="card fade-in">
              <h3 style={{ marginBottom: 16 }}>Analysis Results</h3>

              <div className="result-section">
                <h4>Intent & Confidence</h4>
                <div className="result-row">
                  <span className="result-key">Intent</span>
                  <span className="result-val">{result.intent}</span>
                </div>
                <div className="result-row">
                  <span className="result-key">Confidence</span>
                  <span className="result-val">{(result.confidence * 100).toFixed(1)}%</span>
                </div>
                <div style={{ marginTop: 6 }}>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${result.confidence * 100}%`,
                        background:
                          result.confidence > 0.8
                            ? "var(--success)"
                            : result.confidence > 0.5
                            ? "var(--warning)"
                            : "var(--danger)",
                      }}
                    />
                  </div>
                </div>
              </div>

              <div className="result-section">
                <h4>Sentiment & Distress</h4>
                <div className="result-row">
                  <span className="result-key">Sentiment</span>
                  <span
                    className={`badge ${
                      result.sentiment === "negative"
                        ? "badge-emergency"
                        : result.sentiment === "positive"
                        ? "badge-routine"
                        : "badge-info"
                    }`}
                  >
                    {result.sentiment}
                  </span>
                </div>
                <div className="result-row">
                  <span className="result-key">Distress Score</span>
                  <span className="result-val">{(result.distress_score * 100).toFixed(0)}%</span>
                </div>
                <div className="result-row">
                  <span className="result-key">Processing Time</span>
                  <span className="result-val">{result.processing_time_ms}ms</span>
                </div>
              </div>

              {result.entities && Object.keys(result.entities).length > 0 && (
                <div className="result-section">
                  <h4>Extracted Entities</h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {Object.entries(result.entities).map(([key, val]) => (
                      <span key={key} className="entity-tag">
                        <span className="entity-type">{key}:</span>{" "}
                        {Array.isArray(val) ? val.join(", ") : String(val)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="card" style={{ textAlign: "center", color: "var(--text-muted)", padding: 60 }}>
              Enter text and click Analyze to see NLU results
            </div>
          )}
        </div>
      </div>

      {/* ── Intent Reference ──────────────────────────────── */}
      <div className="card" style={{ marginTop: 16 }}>
        <h3 style={{ marginBottom: 12 }}>Supported Intents</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Intent</th>
              <th>Description</th>
              <th>Example</th>
            </tr>
          </thead>
          <tbody>
            {intents.map((i) => (
              <tr key={i.intent}>
                <td><code style={{ fontSize: 12, color: "var(--accent)" }}>{i.intent}</code></td>
                <td>{i.description}</td>
                <td style={{ color: "var(--text-muted)", fontStyle: "italic" }}>{i.example}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
