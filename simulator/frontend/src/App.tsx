import { Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import CallerUI from "./pages/CallerUI";
import AdminDashboard from "./pages/AdminDashboard";
import { RequireAuth, RequireRole } from "./components/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      {/* Public route — Landing page */}
      <Route path="/" element={<LandingPage />} />

      {/* Authenticated route — Caller UI (any logged-in user) */}
      <Route
        path="/call"
        element={
          <RequireAuth>
            <CallerUI />
          </RequireAuth>
        }
      />

      {/* Admin-only routes — Full dashboard with all modules */}
      <Route
        path="/admin/*"
        element={
          <RequireAuth>
            <RequireRole role="admin">
              <AdminDashboard />
            </RequireRole>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
