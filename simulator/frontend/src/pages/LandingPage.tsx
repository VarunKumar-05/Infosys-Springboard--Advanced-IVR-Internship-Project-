import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useState, useEffect } from "react";
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
  UserPlus,
  LogIn,
  Eye,
  EyeOff,
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
  const { isAuthenticated, isLoaded, user, login, signup } = useAuth();
  const navigate = useNavigate();

  // Auth form state
  const [authTab, setAuthTab] = useState<"signin" | "signup">("signin");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sign In fields
  const [signInEmail, setSignInEmail] = useState("");
  const [signInPassword, setSignInPassword] = useState("");

  // Sign Up fields
  const [signUpName, setSignUpName] = useState("");
  const [signUpAge, setSignUpAge] = useState("");
  const [signUpPhone, setSignUpPhone] = useState("");
  const [signUpEmail, setSignUpEmail] = useState("");
  const [signUpPassword, setSignUpPassword] = useState("");

  // Show auth modal
  const [showAuthModal, setShowAuthModal] = useState(false);

  // Redirect signed-in users based on role
  useEffect(() => {
    if (isLoaded && isAuthenticated && user) {
      if (user.role === "admin") {
        navigate("/admin/dashboard", { replace: true });
      } else {
        navigate("/call", { replace: true });
      }
    }
  }, [isLoaded, isAuthenticated, user, navigate]);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(signInEmail, signInPassword);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const age = parseInt(signUpAge, 10);
      if (isNaN(age) || age < 1 || age > 150) {
        throw new Error("Please enter a valid age (1-150)");
      }
      await signup(signUpName, age, signUpPhone, signUpEmail, signUpPassword);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setLoading(false);
    }
  };

  const openAuth = (tab: "signin" | "signup") => {
    setAuthTab(tab);
    setShowAuthModal(true);
    setError(null);
  };

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
          <button
            className="btn btn-ghost"
            onClick={() => openAuth("signin")}
            id="header-signin-btn"
          >
            <LogIn size={16} />
            Sign In
          </button>
          <button
            className="btn btn-primary"
            onClick={() => openAuth("signup")}
            id="header-signup-btn"
          >
            <UserPlus size={16} />
            Sign Up
          </button>
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
          <button
            className="btn btn-primary btn-lg"
            onClick={() => openAuth("signup")}
            id="hero-get-started-btn"
          >
            Get Started
            <ArrowRight size={18} />
          </button>

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

      {/* ── Auth Modal ────────────────────────────────────────────── */}
      {showAuthModal && (
        <div className="auth-overlay" onClick={() => setShowAuthModal(false)}>
          <div className="auth-container" onClick={(e) => e.stopPropagation()}>
            {/* Tabs */}
            <div className="auth-tabs">
              <button
                className={`auth-tab ${authTab === "signin" ? "active" : ""}`}
                onClick={() => { setAuthTab("signin"); setError(null); }}
                id="auth-tab-signin"
              >
                <LogIn size={16} />
                Sign In
              </button>
              <button
                className={`auth-tab ${authTab === "signup" ? "active" : ""}`}
                onClick={() => { setAuthTab("signup"); setError(null); }}
                id="auth-tab-signup"
              >
                <UserPlus size={16} />
                Sign Up
              </button>
            </div>

            {/* Error */}
            {error && <div className="auth-error">{error}</div>}

            {/* Sign In Form */}
            {authTab === "signin" && (
              <form className="auth-form" onSubmit={handleSignIn} id="signin-form">
                <div className="auth-field">
                  <label htmlFor="signin-email">Email</label>
                  <input
                    type="email"
                    id="signin-email"
                    placeholder="you@example.com"
                    value={signInEmail}
                    onChange={(e) => setSignInEmail(e.target.value)}
                    required
                    autoFocus
                  />
                </div>
                <div className="auth-field">
                  <label htmlFor="signin-password">Password</label>
                  <div className="auth-password-wrapper">
                    <input
                      type={showPassword ? "text" : "password"}
                      id="signin-password"
                      placeholder="••••••••"
                      value={signInPassword}
                      onChange={(e) => setSignInPassword(e.target.value)}
                      required
                      minLength={6}
                    />
                    <button
                      type="button"
                      className="auth-password-toggle"
                      onClick={() => setShowPassword(!showPassword)}
                      tabIndex={-1}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <button
                  type="submit"
                  className="btn btn-primary btn-lg auth-submit"
                  disabled={loading}
                  id="signin-submit-btn"
                >
                  {loading ? (
                    <span className="auth-spinner" />
                  ) : (
                    <>
                      <Shield size={18} />
                      Sign In
                    </>
                  )}
                </button>
              </form>
            )}

            {/* Sign Up Form */}
            {authTab === "signup" && (
              <form className="auth-form" onSubmit={handleSignUp} id="signup-form">
                <div className="auth-field">
                  <label htmlFor="signup-name">Full Name</label>
                  <input
                    type="text"
                    id="signup-name"
                    placeholder="John Doe"
                    value={signUpName}
                    onChange={(e) => setSignUpName(e.target.value)}
                    required
                    autoFocus
                  />
                </div>
                <div className="auth-row">
                  <div className="auth-field">
                    <label htmlFor="signup-age">Age</label>
                    <input
                      type="number"
                      id="signup-age"
                      placeholder="25"
                      value={signUpAge}
                      onChange={(e) => setSignUpAge(e.target.value)}
                      required
                      min={1}
                      max={150}
                    />
                  </div>
                  <div className="auth-field">
                    <label htmlFor="signup-phone">Phone Number</label>
                    <input
                      type="tel"
                      id="signup-phone"
                      placeholder="+1-555-000-0000"
                      value={signUpPhone}
                      onChange={(e) => setSignUpPhone(e.target.value)}
                      required
                    />
                  </div>
                </div>
                <div className="auth-field">
                  <label htmlFor="signup-email">Email</label>
                  <input
                    type="email"
                    id="signup-email"
                    placeholder="you@example.com"
                    value={signUpEmail}
                    onChange={(e) => setSignUpEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="auth-field">
                  <label htmlFor="signup-password">Password</label>
                  <div className="auth-password-wrapper">
                    <input
                      type={showPassword ? "text" : "password"}
                      id="signup-password"
                      placeholder="Min 6 characters"
                      value={signUpPassword}
                      onChange={(e) => setSignUpPassword(e.target.value)}
                      required
                      minLength={6}
                    />
                    <button
                      type="button"
                      className="auth-password-toggle"
                      onClick={() => setShowPassword(!showPassword)}
                      tabIndex={-1}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <button
                  type="submit"
                  className="btn btn-primary btn-lg auth-submit"
                  disabled={loading}
                  id="signup-submit-btn"
                >
                  {loading ? (
                    <span className="auth-spinner" />
                  ) : (
                    <>
                      <UserPlus size={18} />
                      Create Account
                    </>
                  )}
                </button>
              </form>
            )}

            <p className="auth-footer-text">
              {authTab === "signin" ? (
                <>
                  Don't have an account?{" "}
                  <button className="auth-link" onClick={() => { setAuthTab("signup"); setError(null); }}>
                    Sign up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{" "}
                  <button className="auth-link" onClick={() => { setAuthTab("signin"); setError(null); }}>
                    Sign in
                  </button>
                </>
              )}
            </p>
          </div>
        </div>
      )}

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
