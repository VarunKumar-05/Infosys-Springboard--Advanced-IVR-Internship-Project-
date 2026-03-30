import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";

// ── Types ─────────────────────────────────────────────────────────────────

interface AuthUser {
  user_id: number;
  name: string;
  email: string;
  role: string;
  age?: number;
  phone_number?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoaded: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, age: number, phone_number: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

// ── Helpers ───────────────────────────────────────────────────────────────

const BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");

function decodeJwtPayload(token: string): AuthUser | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    const payload = JSON.parse(json);

    // Check expiration
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      return null;
    }

    return {
      user_id: payload.user_id,
      name: payload.name,
      email: payload.email,
      role: payload.role,
      age: payload.age,
      phone_number: payload.phone_number,
    };
  } catch {
    return null;
  }
}

// ── Provider ──────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  // Restore session from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem("token");
    if (savedToken) {
      const decoded = decodeJwtPayload(savedToken);
      if (decoded) {
        setToken(savedToken);
        setUser(decoded);
      } else {
        // Token expired or invalid — clear it
        localStorage.removeItem("token");
      }
    }
    setIsLoaded(true);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${BASE}/api/auth/signin`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Sign in failed" }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    localStorage.setItem("token", data.token);
    setToken(data.token);

    const decoded = decodeJwtPayload(data.token);
    setUser(decoded);
  }, []);

  const signup = useCallback(
    async (name: string, age: number, phone_number: string, email: string, password: string) => {
      const res = await fetch(`${BASE}/api/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, age, phone_number, email, password }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Sign up failed" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      localStorage.setItem("token", data.token);
      setToken(data.token);

      const decoded = decodeJwtPayload(data.token);
      setUser(decoded);
    },
    []
  );

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoaded,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an <AuthProvider>");
  }
  return ctx;
}
