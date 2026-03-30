import { useState, useRef, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import type { Scenario } from "../api/client";
import { api } from "../api/client";
import {
  Phone,
  PhoneOff,
  Send,
  Mic,
  MicOff,
  Volume2,
  Delete,
  ArrowLeft,
  LogOut,
} from "lucide-react";

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

type DtmfKey = "1" | "2" | "3" | "4";
type DtmfPhase = "idle" | "tts" | "listening" | "submitting" | "done" | "error";

const DTMF_OPTIONS: Array<{ key: DtmfKey; label: string }> = [
  { key: "1", label: "Booking an Appointment" },
  { key: "2", label: "Canceling an Appointment" },
  { key: "3", label: "Booking an Ambulance" },
  { key: "4", label: "Canceling an Ambulance" },
];

// ── Keypad layout ────────────────────────────────────────────────────────

const keypadRows = [
  [
    { digit: "1", sub: "" },
    { digit: "2", sub: "ABC" },
    { digit: "3", sub: "DEF" },
  ],
  [
    { digit: "4", sub: "GHI" },
    { digit: "5", sub: "JKL" },
    { digit: "6", sub: "MNO" },
  ],
  [
    { digit: "7", sub: "PQRS" },
    { digit: "8", sub: "TUV" },
    { digit: "9", sub: "WXYZ" },
  ],
  [
    { digit: "*", sub: "" },
    { digit: "0", sub: "+" },
    { digit: "#", sub: "" },
  ],
];

// ── Component ────────────────────────────────────────────────────────────

export default function CallerUI() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  // Dialer state
  const [phoneNumber, setPhoneNumber] = useState("");
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState("");

  // Call state (mirrors CallSimulator)
  const [callState, setCallState] = useState<CallState>("idle");
  const [callId, setCallId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [input, setInput] = useState("");
  const [lastResponse, setLastResponse] = useState<ResponseData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dtmfPhase, setDtmfPhase] = useState<DtmfPhase>("idle");
  const [dtmfSelection, setDtmfSelection] = useState<DtmfKey | null>(null);
  const [dtmfError, setDtmfError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioQueueRef = useRef<Uint8Array[]>([]);
  const isPlayingRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

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

  // ── Keypad handler ──────────────────────────────────────────────────────

  const captureDtmfResponseAudio = useCallback(async (durationMs = 5000) => {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("Microphone not supported in this browser.");
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks: Blob[] = [];

    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    const recorder = new MediaRecorder(stream, { mimeType });

    return await new Promise<Blob>((resolve, reject) => {
      let done = false;
      const cleanup = () => {
        stream.getTracks().forEach((t) => t.stop());
      };
      const finish = () => {
        if (done) return;
        done = true;
        cleanup();
        resolve(new Blob(chunks, { type: "audio/webm" }));
      };

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };
      recorder.onerror = () => {
        if (done) return;
        done = true;
        cleanup();
        reject(new Error("Could not capture microphone audio."));
      };
      recorder.onstop = finish;

      recorder.start(200);
      window.setTimeout(() => {
        if (recorder.state !== "inactive") recorder.stop();
      }, durationMs);
    });
  }, []);

  const handleKeyPress = (digit: string) => {
    if (callState !== "idle") {
      if (["1", "2", "3", "4"].includes(digit)) {
        if (
          dtmfPhase === "tts" ||
          dtmfPhase === "listening" ||
          dtmfPhase === "submitting"
        ) {
          return;
        }
        handleDtmfPress(digit as DtmfKey);
      }
      return;
    }

    setPhoneNumber((prev) => prev + digit);
  };

  const handleBackspace = () => {
    setPhoneNumber((prev) => prev.slice(0, -1));
  };

  // ── Audio Playback ──────────────────────────────────────────────────────

  const playAudioQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
    isPlayingRef.current = true;

    const totalLength = audioQueueRef.current.reduce(
      (acc, curr) => acc + curr.length,
      0
    );
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

    if (totalLength === 0) {
      playNext();
      return;
    }

    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext ||
        (window as any).webkitAudioContext)();
    }

    const arrayBuffer = combinedBytes.buffer.slice(
      combinedBytes.byteOffset,
      combinedBytes.byteOffset + combinedBytes.byteLength
    );

    try {
      const audioBuffer =
        await audioContextRef.current.decodeAudioData(arrayBuffer);
      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current.destination);
      source.onended = playNext;
      source.start(0);
    } catch (err) {
      console.warn("Web Audio decode failed, falling back:", err);
      try {
        const blob = new Blob([arrayBuffer], { type: "audio/mpeg" });
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.onended = () => {
          URL.revokeObjectURL(url);
          playNext();
        };
        audio.onerror = () => {
          URL.revokeObjectURL(url);
          playNext();
        };
        audio.play();
      } catch {
        playNext();
      }
    }
  }, []);

  const playBase64Audio = useCallback(async (audioBase64?: string) => {
    if (!audioBase64) return;
    const binary = atob(audioBase64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    audioQueueRef.current.push(bytes);
    await playAudioQueue();
  }, [playAudioQueue]);

  const handleDtmfPress = useCallback(async (key: DtmfKey) => {
    if (!callId) {
      setDtmfError("Start a call to use DTMF keypad options.");
      return;
    }

    setDtmfSelection(key);
    setDtmfError(null);
    setDtmfPhase("tts");

    try {
      const prompt = await api.requestDtmfPrompt(callId, key);
      setTranscript((prev) => [
        ...prev,
        { speaker: "system", content: prompt.acknowledgment_text },
      ]);

      await playBase64Audio(prompt.audio_base64);

      setDtmfPhase("listening");
      const capturedAudio = await captureDtmfResponseAudio();

      setDtmfPhase("submitting");
      const submit = await api.submitDtmfInput(callId, key, capturedAudio);

      if (submit.transcript) {
        setTranscript((prev) => [
          ...prev,
          { speaker: "patient", content: submit.transcript },
        ]);
      }

      setTranscript((prev) => [
        ...prev,
        { speaker: "system", content: submit.confirmation_text },
      ]);

      if (submit.nlu) {
        setLastResponse({
          text: submit.confirmation_text,
          nlu: submit.nlu,
        });
      }

      if (submit.errors.length > 0) {
        setDtmfError(submit.errors.join(" | "));
        setDtmfPhase("error");
        return;
      }

      setDtmfPhase("done");
    } catch (err) {
      setDtmfError(err instanceof Error ? err.message : "DTMF request failed.");
      setDtmfPhase("error");
    }
  }, [callId, captureDtmfResponseAudio, playBase64Audio]);

  // ── WebSocket Connection ────────────────────────────────────────────────

  const startCall = useCallback(() => {
    const id = `VOICE-${Date.now().toString(36).toUpperCase()}`;
    setCallId(id);
    setCallState("connecting");
    setTranscript([]);
    setLastResponse(null);
    setError(null);
    setDtmfPhase("idle");
    setDtmfSelection(null);
    setDtmfError(null);

    const apiBase = (import.meta.env.VITE_API_BASE_URL || "").replace(
      /\/+$/,
      ""
    );
    let wsHost = window.location.host;
    let protocol = window.location.protocol === "https:" ? "wss:" : "ws:";

    if (apiBase) {
      try {
        const parsedNode = new URL(apiBase);
        wsHost = parsedNode.host;
        protocol = parsedNode.protocol === "https:" ? "wss:" : "ws:";
      } catch {
        // Fallback to defaults
      }
    }

    const wsUrl = new URL(`${protocol}//${wsHost}/api/calls/ws/${id}`);
    if (phoneNumber.trim()) {
      wsUrl.searchParams.append("phone", phoneNumber.trim());
    }
    if (selectedScenario) {
      wsUrl.searchParams.append("scenario_id", selectedScenario);
    }
    const ws = new WebSocket(wsUrl.toString());
    wsRef.current = ws;
    ws.binaryType = "arraybuffer";

    ws.onopen = () => setCallState("listening");

    ws.onmessage = (event) => {
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
  }, [phoneNumber, selectedScenario, playAudioQueue]);

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
    setDtmfPhase("idle");
    setDtmfSelection(null);
    setDtmfError(null);
    wsRef.current = null;
  }, []);

  // ── Voice Recording ────────────────────────────────────────────────────

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

  // ── Text Input ──────────────────────────────────────────────────────────

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

  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT"
      ) {
        return;
      }

      if (
        callState === "idle" ||
        dtmfPhase === "tts" ||
        dtmfPhase === "listening" ||
        dtmfPhase === "submitting"
      ) {
        return;
      }

      if (["1", "2", "3", "4"].includes(e.key)) {
        e.preventDefault();
        handleDtmfPress(e.key as DtmfKey);
      }
    };

    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, [callState, dtmfPhase, handleDtmfPress]);

  // ── State Labels ────────────────────────────────────────────────────────

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
    connecting: "var(--warning)",
    listening: "var(--success)",
    recording: "var(--danger)",
    processing: "var(--warning)",
    speaking: "var(--accent)",
  };

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="caller-page">
      {/* Header */}
      <header className="caller-header">
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => navigate("/")}
            title="Back to Home"
            id="caller-back-btn"
          >
            <ArrowLeft size={16} />
          </button>
          <h1>
            <Phone size={20} />
            AI-<span>IVR</span> Caller
          </h1>
        </div>
        <button
          className="btn btn-ghost btn-sm"
          onClick={handleLogout}
          id="caller-logout-btn"
          style={{ display: "flex", alignItems: "center", gap: 6 }}
        >
          <LogOut size={16} />
          Sign Out
        </button>
      </header>

      {/* Body */}
      <div className="caller-body">
        {/* ── Left: Dialer ──────────────────────────────────────────── */}
        <div className="caller-dialer">
          {/* Phone display */}
          <div className="phone-display">
            <input
              type="tel"
              className="phone-input-box"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="Enter number"
              disabled={callState !== "idle"}
              id="phone-number-input"
            />
          </div>

          {/* Keypad */}
          <div className="fade-in">
            <div className="keypad">
              {keypadRows.flat().map((key) => (
                <button
                  key={key.digit}
                  className="keypad-btn"
                  onClick={() => handleKeyPress(key.digit)}
                  disabled={
                    callState !== "idle" &&
                    (key.digit === "*" || key.digit === "0" || key.digit === "#")
                  }
                  id={`keypad-${key.digit === "*" ? "star" : key.digit === "#" ? "hash" : key.digit}`}
                >
                  {key.digit}
                  {key.sub && (
                    <span className="keypad-btn-sub">{key.sub}</span>
                  )}
                </button>
              ))}
            </div>

            <div
              style={{
                padding: "10px 10px 0",
                fontSize: 12,
                color: "var(--text-secondary)",
                lineHeight: 1.5,
              }}
            >
              {DTMF_OPTIONS.map((opt) => (
                <div key={opt.key}>{opt.key} - {opt.label}</div>
              ))}
            </div>

            {callState !== "idle" && (
              <div
                style={{
                  padding: "8px 10px 0",
                  fontSize: 12,
                  color: "var(--text-muted)",
                }}
              >
                DTMF status: {dtmfPhase}
                {dtmfSelection ? ` | Last key: ${dtmfSelection}` : ""}
              </div>
            )}

            {dtmfError && (
              <p
                style={{
                  color: "var(--danger)",
                  fontSize: 12,
                  padding: "6px 10px 0",
                }}
              >
                {dtmfError}
              </p>
            )}

            {/* Scenario select */}
            {callState === "idle" && (
              <div style={{ padding: "12px 8px 0" }}>
                <select
                  value={selectedScenario}
                  onChange={(e) => setSelectedScenario(e.target.value)}
                  style={{ fontSize: 13 }}
                  id="scenario-select"
                >
                  <option value="">— Free-form call —</option>
                  {scenarios.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.category})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Call / Backspace */}
            {callState === "idle" && (
              <div className="keypad-actions" style={{ marginTop: 12 }}>
                <button
                  className="call-btn"
                  onClick={startCall}
                  id="start-call-btn"
                >
                  <Phone size={18} />
                  Start Call
                </button>
                <button
                  className="backspace-btn"
                  onClick={handleBackspace}
                  disabled={!phoneNumber}
                  id="backspace-btn"
                >
                  <Delete size={18} />
                </button>
              </div>
            )}
          </div>

          {/* Active call controls */}
          {callState !== "idle" && (
            <div className="fade-in">
              <div
                style={{
                  padding: "12px 16px",
                  background: "rgba(255,255,255,0.03)",
                  borderRadius: 12,
                  border: "1px solid var(--border-glass)",
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
                <span
                  className="pulse"
                  style={{ color: stateColor[callState] }}
                >
                  ●
                </span>
                {stateLabel[callState]}
              </div>

              <div className="keypad-actions" style={{ marginTop: 12 }}>
                <button
                  className="call-btn end-call"
                  onClick={endCall}
                  id="end-call-btn"
                >
                  <PhoneOff size={18} />
                  End Call
                </button>
              </div>
            </div>
          )}

          {error && (
            <p
              style={{
                color: "var(--danger)",
                fontSize: 13,
                padding: "0 8px",
              }}
            >
              {error}
            </p>
          )}
        </div>

        {/* ── Right: Conversation ────────────────────────────────────── */}
        <div className="caller-conversation">
          {callState === "idle" && transcript.length === 0 ? (
            <div
              className="glass-card"
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                gap: 16,
                minHeight: 400,
              }}
            >
              <div
                style={{
                  width: 80,
                  height: 80,
                  background: "var(--gradient-accent)",
                  borderRadius: 24,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 12px 40px -10px rgba(99, 102, 241, 0.4)",
                }}
              >
                <Phone size={36} color="white" />
              </div>
              <h2
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  letterSpacing: "-0.5px",
                }}
              >
                Ready to Call
              </h2>
              <p
                style={{
                  color: "var(--text-secondary)",
                  fontSize: 15,
                  maxWidth: 360,
                  lineHeight: 1.6,
                }}
              >
                Enter a phone number using the keypad or type it directly, then
                press <strong>Start Call</strong> to connect with the AI
                Hospital IVR.
              </p>
            </div>
          ) : (
            <>
              {/* Transcript */}
              <div
                className="glass-card"
                style={{ flex: 1, display: "flex", flexDirection: "column" }}
              >
                <h3
                  style={{
                    marginBottom: 12,
                    fontSize: 15,
                    fontWeight: 600,
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <span
                    className="pulse"
                    style={{ color: stateColor[callState] }}
                  >
                    ●
                  </span>
                  {callId ? `Call — ${callId}` : "Call Ended"}
                </h3>

                <div
                  className="transcript"
                  style={{
                    flex: 1,
                    minHeight: 200,
                    maxHeight: "unset",
                    background: "rgba(0,0,0,0.2)",
                    border: "1px solid var(--border-glass)",
                  }}
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

                {/* Input area */}
                {callState !== "idle" && (
                  <div
                    style={{
                      display: "flex",
                      gap: 8,
                      marginTop: 12,
                      alignItems: "center",
                    }}
                  >
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
                      id="mic-toggle-btn"
                    >
                      {callState === "recording" ? (
                        <MicOff size={18} />
                      ) : (
                        <Mic size={18} />
                      )}
                    </button>

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
                      id="text-input"
                    />

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
                      id="send-btn"
                    >
                      <Send size={18} />
                    </button>
                  </div>
                )}
              </div>

              {/* NLU / Triage / Dispatch Results */}
              {lastResponse && (
                <div className="grid-2">
                  {lastResponse.nlu && (
                    <div className="glass-card fade-in">
                      <h3 style={{ marginBottom: 12 }}>NLU Analysis</h3>
                      <div className="result-section" style={{ background: "rgba(0,0,0,0.2)", border: "1px solid var(--border-glass)" }}>
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
                      </div>
                    </div>
                  )}

                  {lastResponse.triage && (
                    <div className="glass-card fade-in">
                      <h3 style={{ marginBottom: 12 }}>Triage</h3>
                      <div className="result-section" style={{ background: "rgba(0,0,0,0.2)", border: "1px solid var(--border-glass)" }}>
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
                    </div>
                  )}

                  {lastResponse.dispatch && (
                    <div className="glass-card fade-in">
                      <h3 style={{ marginBottom: 12 }}>Dispatch</h3>
                      <div className="result-section" style={{ background: "rgba(0,0,0,0.2)", border: "1px solid var(--border-glass)" }}>
                        <div className="result-row">
                          <span className="result-key">Ambulance</span>
                          <span className="result-val">
                            {lastResponse.dispatch.assigned_ambulance}
                          </span>
                        </div>
                        <div className="result-row">
                          <span className="result-key">ETA</span>
                          <span className="result-val">
                            {lastResponse.dispatch.eta_minutes} min
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
