import { useUser, SignInButton, UserButton } from "@clerk/react";
import { useNavigate } from "react-router-dom";
import { useEffect } from "react";
import {
  Brain,
  Activity,
  Truck,
  BarChart3,
  MessageSquare,
  Volume2,
  ArrowRight,
  Sparkles,
  Phone,
  Shield,
} from "lucide-react";

const features = [
  {
    icon: <Brain size={24} />,
    title: "Natural Language Understanding",
    description:
      "Advanced NLU engine detects caller intent, extracts medical entities, and measures distress in real time.",
  },
  {
    icon: <Activity size={24} />,
    title: "ILP-Based Triage",
    description:
      "SCIP-powered Integer Linear Programming solver prioritizes patients based on clinical rules and severity.",
  },
  {
    icon: <Truck size={24} />,
    title: "Smart Ambulance Dispatch",
    description:
      "Gurobi ILP optimizer assigns the nearest available ambulance with optimal crew configuration.",
  },
  {
    icon: <BarChart3 size={24} />,
    title: "Real-Time Analytics",
    description:
      "Live dashboard with call metrics, dispatch statistics, response times, and historical trends.",
  },
  {
    icon: <MessageSquare size={24} />,
    title: "Live Transcription",
    description:
      "Google Cloud Speech-to-Text converts caller audio to text with medical vocabulary enhancement.",
  },
  {
    icon: <Volume2 size={24} />,
    title: "Voice AI Synthesis",
    description:
      "Google Cloud Text-to-Speech delivers natural, empathetic AI voice responses to callers.",
  },
];

export default function LandingPage() {
  const { isSignedIn, user, isLoaded } = useUser();
  const navigate = useNavigate();

  // Redirect signed-in users based on role
  useEffect(() => {
    if (isLoaded && isSignedIn && user) {
      const role = (user.publicMetadata as { role?: string })?.role;
      if (role === "admin") {
        navigate("/admin/dashboard", { replace: true });
      } else {
        navigate("/call", { replace: true });
      }
    }
  }, [isLoaded, isSignedIn, user, navigate]);

  return (
    <div className="landing-page">
      {/* ── Header ────────────────────────────────────────────────── */}
      <header className="landing-header" id="landing-header">
        <div className="landing-logo">
          <div className="landing-logo-icon">🏥</div>
          <div className="landing-logo-text">
            AI-<span>IVR</span> Advanced
          </div>
        </div>

        <div className="landing-header-actions">
          {isSignedIn ? (
            <UserButton
              appearance={{
                elements: {
                  avatarBox: { width: 36, height: 36 },
                },
              }}
            />
          ) : (
            <SignInButton mode="modal">
              <button className="btn btn-primary" id="login-btn">
                <Shield size={16} />
                Sign In
              </button>
            </SignInButton>
          )}
        </div>
      </header>

      {/* ── Hero Section ──────────────────────────────────────────── */}
      <section className="hero-section" id="hero-section">
        <div className="hero-badge">
          <span className="hero-badge-dot" />
          AI-Powered Hospital IVR System
        </div>

        <h1 className="hero-title">
          Intelligent Call Routing
          <br />
          for <span className="gradient-text">Modern Healthcare</span>
        </h1>

        <p className="hero-subtitle">
          An advanced Interactive Voice Response system that combines
          natural language understanding, real-time clinical triage, and
          optimized ambulance dispatch — all powered by cutting-edge AI.
        </p>

        <div className="hero-actions">
          <SignInButton mode="modal">
            <button className="btn btn-primary btn-lg" id="hero-get-started-btn">
              Get Started
              <ArrowRight size={18} />
            </button>
          </SignInButton>

          <a
            href="#features"
            className="btn btn-ghost btn-lg"
            id="hero-learn-more-btn"
            style={{ textDecoration: "none" }}
          >
            <Sparkles size={18} />
            Explore Features
          </a>
        </div>
      </section>

      {/* ── Features Section ──────────────────────────────────────── */}
      <section className="features-section" id="features">
        <p className="features-label">Capabilities</p>
        <h2 className="features-title">
          Everything you need for{" "}
          <span className="gradient-text" style={{
            background: "var(--gradient-accent)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}>
            intelligent triage
          </span>
        </h2>

        <div className="feature-grid">
          {features.map((feature, i) => (
            <div
              key={i}
              className="feature-card"
              style={{
                animation: `fadeInUp 0.5s ease-out ${0.1 * i}s both`,
              }}
            >
              <div className="feature-icon">{feature.icon}</div>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────── */}
      <footer
        style={{
          padding: "32px 40px",
          textAlign: "center",
          borderTop: "1px solid var(--border-glass)",
          color: "var(--text-muted)",
          fontSize: 13,
          position: "relative",
          zIndex: 1,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 8 }}>
          <Phone size={14} />
          <span>AI-IVR Advanced System</span>
        </div>
        <p>
          Built with FastAPI, React, Google Cloud AI &amp; ILP Optimization
        </p>
      </footer>
    </div>
  );
}
