import { NavLink } from "react-router-dom";
import type { MenuItem } from "../api/client";
import {
  Phone, List, Brain, Activity, Truck, BarChart3, Home,
  User, FileText, Settings,
} from "lucide-react";

const iconMap: Record<string, React.ReactNode> = {
  phone:      <Phone size={18} />,
  list:       <List size={18} />,
  brain:      <Brain size={18} />,
  activity:   <Activity size={18} />,
  truck:      <Truck size={18} />,
  "bar-chart": <BarChart3 size={18} />,
  user:       <User size={18} />,
  "file-text": <FileText size={18} />,
  settings:   <Settings size={18} />,
};

interface Props {
  items: MenuItem[];
  children?: React.ReactNode;
}

export default function Sidebar({ items, children }: Props) {
  // Detect if admin-prefixed routes are being used
  const homeRoute = items.length > 0 && items[0].route.startsWith("/admin")
    ? "/admin/dashboard"
    : "/";

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>🏥 <span>IVR Simulator</span></h1>
        <p>AI-Based Hospital IVR System</p>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to={homeRoute}
          end
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <Home size={18} />
          <span>Dashboard</span>
        </NavLink>

        {items.map((item) => (
          <NavLink
            key={item.id}
            to={item.route}
            className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
          >
            {iconMap[item.icon] || <List size={18} />}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {children}

      <div className="sidebar-footer">
        v1.0.0 •{" "}
        <a href="/docs" target="_blank" rel="noreferrer">
          API Docs
        </a>
      </div>
    </aside>
  );
}
