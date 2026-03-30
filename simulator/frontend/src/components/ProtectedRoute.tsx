import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/**
 * RequireAuth — Redirects unauthenticated users to the landing page.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoaded } = useAuth();

  if (!isLoaded) {
    return (
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        background: "var(--bg-primary)",
        color: "var(--text-muted)",
        fontSize: 14,
      }}>
        <div className="pulse">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

/**
 * RequireRole — Checks user's role from JWT token.
 * Redirects non-matching users to /call (regular user default).
 */
export function RequireRole({
  role,
  children,
}: {
  role: string;
  children: React.ReactNode;
}) {
  const { user, isLoaded } = useAuth();

  if (!isLoaded) {
    return (
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        background: "var(--bg-primary)",
        color: "var(--text-muted)",
        fontSize: 14,
      }}>
        <div className="pulse">Verifying access...</div>
      </div>
    );
  }

  if (user?.role !== role) {
    return <Navigate to="/call" replace />;
  }

  return <>{children}</>;
}
