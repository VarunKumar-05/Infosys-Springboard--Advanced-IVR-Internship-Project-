import { useUser } from "@clerk/react";
import { Navigate } from "react-router-dom";

/**
 * RequireAuth — Redirects unauthenticated users to the landing page.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isSignedIn, isLoaded } = useUser();

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

  if (!isSignedIn) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

/**
 * RequireRole — Checks user's publicMetadata.role.
 * Redirects non-matching users to /call (regular user default).
 */
export function RequireRole({
  role,
  children,
}: {
  role: string;
  children: React.ReactNode;
}) {
  const { user, isLoaded } = useUser();

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

  const userRole = (user?.publicMetadata as { role?: string })?.role;

  if (userRole !== role) {
    return <Navigate to="/call" replace />;
  }

  return <>{children}</>;
}
