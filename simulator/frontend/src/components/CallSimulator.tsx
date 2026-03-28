import { useState, useRef, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { Scenario } from "../api/client";
import { Phone, PhoneOff, Send, Mic, MicOff, Volume2 } from "lucide-react";

// ── Types ────────────────────────────────────────────────────────────────

type CallState =
  | "idle"
  | "connecting"
  | "listening"
  | "recording"
  | "processing"
  | "speaking";

interface TranscriptEntry {
  speaker: string;
  content: string;
}

interface NluData {
  intent: string;
  confidence: number;
  entities: Record<string, unknown>;
  sentiment: string;
  distress_score: number;
}

interface ResponseData {
  text: string;
  nlu?: NluData;
  triage?: {
    triage_level: string;
    recommended_facility: string;
    clinical_reasoning: string;
    severity_score: number;
    solver_time_ms?: number;
  };
  dispatch?: {
    assigned_ambulance: string;
    ambulance_type: string;
    eta_minutes: number;
    crew_size: number;
  };
  actions?: string[];
}

// ── Component ────────────────────────────────────────────────────────────

export default function CallSimulator() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState("");
  const [callerPhone, setCallerPhone] = useState("+1-555-000-0000");
  const [callState, setCallState] = useState<CallState>("idle");
  const [callId, setCallId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [input, setInput] = useState("");
  const [lastResponse, setLastResponse] = useState<ResponseData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioQueueRef = useRef<Uint8Array[]>([]);
  const isPlayingRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load scenarios on mount
  useEffect(() => {
    api.listScenarios().then(setScenarios).catch(console.error);
  }, []);

  // Auto-scroll transcript
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // ── Audio Playback ──────────────────────────────────────────────────────

  const audioContextRef = useRef<AudioContext | null>(null);

  const playAudioQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
    isPlayingRef.current = true;

    // Combine all received bytes
    const totalLength = audioQueueRef.current.reduce((acc, curr) => acc + curr.length, 0);
    const combinedBytes = new Uint8Array(totalLength);
    let offset = 0;
    for (const arr of audioQueueRef.current) {
      combinedBytes.set(arr, offset);
      offset += arr.length;
    }
    audioQueueRef.current = [];

    const playNext = () => {
      isPlayingRef.current = false;
      if (audioQueueRef.current.length > 0) playAudioQueue();
    };

    // Skip if the server sent empty audio (e.g. TTS failure)
    if (totalLength === 0) {
      playNext();
      return;
    }

    // Initialize AudioContext on first use (must be after user interaction)
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }

    // .buffer may reference a larger ArrayBuffer than our data when the
    // Uint8Array's byteOffset != 0 or when the engine over-allocates.
    // .slice() guarantees an owned, correctly-sized ArrayBuffer.
    const arrayBuffer = combinedBytes.buffer.slice(
      combinedBytes.byteOffset,
      combinedBytes.byteOffset + combinedBytes.byteLength
    );

    try {
      // Decode the MP3 audio buffer
      const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer);

      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current.destination);

      source.onended = playNext;
      source.start(0);
    } catch (err) {
      console.warn("Web Audio decode failed, falling back to HTMLAudioElement:", err);
      // Fallback: use an <audio> element which has broader codec support
      try {
        const blob = new Blob([arrayBuffer], { type: "audio/mpeg" });
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.onended = () => { URL.revokeObjectURL(url); playNext(); };
        audio.onerror = () => { URL.revokeObjectURL(url); playNext(); };
        audio.play();
      } catch {
        playNext();
      }
    }
  }, []);

  // ── WebSocket Connection ────────────────────────────────────────────────

  const startCall = useCallback(() => {
    const id = `VOICE-${Date.now().toString(36).toUpperCase()}`;
    setCallId(id);
    setCallState("connecting");
    setTranscript([]);
    setLastResponse(null);
    setError(null);

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = new URL(`${protocol}//${window.location.host}/api/calls/ws/${id}`);
    if (callerPhone.trim()) {
      wsUrl.searchParams.append("phone", callerPhone.trim());
    }
    if (selectedScenario) {
      wsUrl.searchParams.append("scenario_id", selectedScenario);
    }
    const ws = new WebSocket(wsUrl.toString());
    wsRef.current = ws;
    ws.binaryType = "arraybuffer";

    ws.onopen = () => setCallState("listening");

    ws.onmessage = (event) => {
      // Binary → queue for playback
      if (event.data instanceof ArrayBuffer) {
        audioQueueRef.current.push(new Uint8Array(event.data));
        return;
      }

      try {
        const msg = JSON.parse(event.data as string);

        switch (msg.type) {
          case "greeting":
            setTranscript((t) => [
              ...t,
              { speaker: "system", content: msg.text },
            ]);
            break;

          case "status":
            if (msg.state === "listening") setCallState("listening");
            else if (msg.state === "processing") setCallState("processing");
            else if (msg.state === "speaking") setCallState("speaking");
            break;

          case "transcript":
            if (msg.speaker === "patient") {
              setTranscript((t) => [
                ...t,
                { speaker: "patient", content: msg.text },
              ]);
            }
            break;

          case "response":
            setTranscript((t) => [
              ...t,
              { speaker: "system", content: msg.text },
            ]);
            setLastResponse({
              text: msg.text,
              nlu: msg.nlu,
              triage: msg.triage,
              dispatch: msg.dispatch,
              actions: msg.actions,
            });
            break;

          case "audio_end":
            playAudioQueue();
            break;

          case "error":
            setError(msg.message);
            break;
        }
      } catch {
        /* non-JSON text, ignore */
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection error. Is the backend running?");
      setCallState("idle");
      setCallId(null);
    };

    ws.onclose = () => {
      setCallState("idle");
      setCallId(null);
    };
  }, [playAudioQueue]);

  // ── End Call ────────────────────────────────────────────────────────────

  const endCall = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "end_call" }));
      wsRef.current.close();
    }
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      mediaRecorderRef.current.stop();
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());

    setCallState("idle");
    setCallId(null);
    wsRef.current = null;
  }, []);

  // ── Voice Recording ─────────────────────────────────────────────────────

  const startRecording = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Microphone not supported in this browser.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      audioChunksRef.current = [];

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        setCallState("processing");

        const audioBlob = new Blob(audioChunksRef.current, {
          type: "audio/webm",
        });
        const arrayBuffer = await audioBlob.arrayBuffer();

        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(arrayBuffer);
          wsRef.current.send(JSON.stringify({ type: "audio_end" }));
        }
      };

      recorder.start(250);
      setCallState("recording");
    } catch {
      setError("Could not access microphone. Please allow permission.");
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const toggleRecording = useCallback(() => {
    if (callState === "recording") stopRecording();
    else if (callState === "listening") startRecording();
  }, [callState, startRecording, stopRecording]);

  // ── Text Input (fallback for no-mic usage) ──────────────────────────────

  const sendTextMessage = useCallback(() => {
    if (
      !input.trim() ||
      !wsRef.current ||
      wsRef.current.readyState !== WebSocket.OPEN
    )
      return;
    const text = input.trim();
    setInput("");
    setCallState("processing");
    wsRef.current.send(JSON.stringify({ type: "text_input", text }));
  }, [input]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendTextMessage();
    }
  };

  // ── State Indicator Helpers ─────────────────────────────────────────────

  const stateLabel: Record<CallState, string> = {
    idle: "",
    connecting: "Connecting...",
    listening: "Listening — Click mic or type below",
    recording: "Recording — Click mic to stop",
    processing: "Processing...",
    speaking: "AI Speaking...",
  };

  const stateColor: Record<CallState, string> = {
    idle: "var(--text-muted)",
    connecting: "var(--warning, #f0ad4e)",
    listening: "var(--success, #5cb85c)",
    recording: "var(--danger, #d9534f)",
    processing: "var(--warning, #f0ad4e)",
    speaking: "var(--accent, #0d6efd)",
  };

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div>
      <div className="page-header">
        <h2>Call Simulator</h2>
        <p>Real-time voice-to-voice conversation with the AI Hospital IVR</p>
      </div>

      {/* ── Start Call Panel ─────────────────────────────────────── */}
      {callState === "idle" && (
        <div className="card fade-in">
          <div className="card-header">
            <h3>New Voice Call</h3>
          </div>
          <div className="form-group">
            <label>Caller Phone Number</label>
            <input
              type="text"
              className="text-input"
              value={callerPhone}
              onChange={(e) => setCallerPhone(e.target.value)}
              placeholder="+1-555-123-4567"
            />
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
          <button className="btn btn-primary" onClick={startCall}>
            <Phone size={16} /> Start Voice Call
          </button>
          {error && (
            <p
              style={{
                color: "var(--danger, #d9534f)",
                marginTop: 8,
                fontSize: 13,
              }}
            >
              {error}
            </p>
          )}
        </div>
      )}

      {/* ── Active Call Panel ────────────────────────────────────── */}
      {callState !== "idle" && (
        <div className="fade-in">
          <div className="card">
            <div className="card-header">
              <h3>
                <span
                  className="pulse"
                  style={{ color: stateColor[callState] }}
                >
                  ●
                </span>{" "}
                {callId && <>Call — {callId}</>}
              </h3>
              <button className="btn btn-danger btn-sm" onClick={endCall}>
                <PhoneOff size={14} /> End Call
              </button>
            </div>

            {/* State Bar */}
            <div
              style={{
                padding: "8px 14px",
                background: "var(--bg-primary, #1a1a2e)",
                borderRadius: 6,
                marginBottom: 12,
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 13,
                color: stateColor[callState],
                fontWeight: 500,
              }}
            >
              {callState === "recording" && (
                <Mic size={14} className="pulse" />
              )}
              {callState === "speaking" && (
                <Volume2 size={14} className="pulse" />
              )}
              {stateLabel[callState]}
            </div>

            {/* Transcript */}
            <div
              className="transcript"
              style={{ minHeight: 200, maxHeight: 400, overflowY: "auto" }}
            >
              {transcript.map((msg, i) => (
                <div key={i} className={`transcript-msg ${msg.speaker}`}>
                  <div>
                    <div className="msg-label">
                      {msg.speaker === "system" ? "AI Assistant" : "You"}
                    </div>
                    <div className="msg-bubble">{msg.content}</div>
                  </div>
                </div>
              ))}
              {callState === "processing" && (
                <div className="transcript-msg system">
                  <div>
                    <div className="msg-label">AI Assistant</div>
                    <div className="msg-bubble" style={{ opacity: 0.6 }}>
                      Thinking...
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Input Area */}
            <div
              style={{
                display: "flex",
                gap: 8,
                marginTop: 12,
                alignItems: "center",
              }}
            >
              {/* Mic Button */}
              <button
                className={`btn ${callState === "recording" ? "btn-danger" : "btn-secondary"}`}
                onClick={toggleRecording}
                disabled={
                  callState === "processing" ||
                  callState === "speaking" ||
                  callState === "connecting"
                }
                title={
                  callState === "recording"
                    ? "Stop Recording"
                    : "Start Recording"
                }
                style={{
                  minWidth: 44,
                  height: 44,
                  padding: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {callState === "recording" ? (
                  <MicOff size={18} />
                ) : (
                  <Mic size={18} />
                )}
              </button>

              {/* Text Input */}
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Or type your message..."
                disabled={
                  callState === "processing" ||
                  callState === "speaking" ||
                  callState === "connecting"
                }
                style={{ flex: 1 }}
              />

              {/* Send Button */}
              <button
                className="btn btn-primary"
                onClick={sendTextMessage}
                disabled={
                  !input.trim() ||
                  callState === "processing" ||
                  callState === "speaking"
                }
                style={{
                  minWidth: 44,
                  height: 44,
                  padding: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Send size={18} />
              </button>
            </div>

            {error && (
              <p
                style={{
                  color: "var(--danger, #d9534f)",
                  marginTop: 8,
                  fontSize: 13,
                }}
              >
                {error}
              </p>
            )}
          </div>

          {/* ── NLU / Triage / Dispatch Results ──────────────────── */}
          {lastResponse && (
            <div className="grid-2" style={{ marginTop: 16 }}>
              {/* NLU */}
              {lastResponse.nlu && (
                <div className="card fade-in">
                  <h3 style={{ marginBottom: 12 }}>NLU Analysis</h3>
                  <div className="result-section">
                    <div className="result-row">
                      <span className="result-key">Intent</span>
                      <span className="result-val">
                        {lastResponse.nlu.intent}
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">Confidence</span>
                      <span className="result-val">
                        {(lastResponse.nlu.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">Sentiment</span>
                      <span className="result-val">
                        {lastResponse.nlu.sentiment}
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">Distress</span>
                      <span className="result-val">
                        {(lastResponse.nlu.distress_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  {lastResponse.nlu.entities &&
                    Object.keys(lastResponse.nlu.entities).length > 0 && (
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
                        <div
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: 4,
                          }}
                        >
                          {Object.entries(lastResponse.nlu.entities).map(
                            ([key, val]) => (
                              <span key={key} className="entity-tag">
                                <span className="entity-type">{key}:</span>{" "}
                                {Array.isArray(val)
                                  ? val.join(", ")
                                  : String(val)}
                              </span>
                            )
                          )}
                        </div>
                      </div>
                    )}
                  {lastResponse.actions &&
                    lastResponse.actions.length > 0 && (
                      <div style={{ marginTop: 10 }}>
                        <h4
                          style={{
                            fontSize: 11,
                            color: "var(--text-muted)",
                            textTransform: "uppercase",
                            marginBottom: 6,
                          }}
                        >
                          Actions Taken
                        </h4>
                        <div
                          style={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: 4,
                          }}
                        >
                          {lastResponse.actions.map((a, i) => (
                            <span key={i} className="badge badge-info">
                              {a}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                </div>
              )}

              {/* Triage */}
              {lastResponse.triage && (
                <div className="card fade-in">
                  <h3 style={{ marginBottom: 12 }}>Triage Assessment</h3>
                  <div className="result-section">
                    <div className="result-row">
                      <span className="result-key">Level</span>
                      <span
                        className={`badge badge-${lastResponse.triage.triage_level}`}
                      >
                        {lastResponse.triage.triage_level}
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">Severity</span>
                      <span className="result-val">
                        {lastResponse.triage.severity_score}/10
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">Facility</span>
                      <span className="result-val">
                        {lastResponse.triage.recommended_facility}
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
                    {lastResponse.triage.clinical_reasoning}
                  </p>
                </div>
              )}

              {/* Dispatch */}
              {lastResponse.dispatch && (
                <div className="card fade-in">
                  <h3 style={{ marginBottom: 12 }}>Ambulance Dispatch</h3>
                  <div className="result-section">
                    <div className="result-row">
                      <span className="result-key">Ambulance</span>
                      <span className="result-val">
                        {lastResponse.dispatch.assigned_ambulance}
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">Type</span>
                      <span className="badge badge-info">
                        {lastResponse.dispatch.ambulance_type}
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">ETA</span>
                      <span className="result-val">
                        {lastResponse.dispatch.eta_minutes} min
                      </span>
                    </div>
                    <div className="result-row">
                      <span className="result-key">Crew</span>
                      <span className="result-val">
                        {lastResponse.dispatch.crew_size} members
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
