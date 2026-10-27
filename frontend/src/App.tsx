import { LayoutDashboard, LogOut, Network, Search, Sparkles, Sun } from "lucide-react";
import { useEffect } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { CopilotLauncher } from "@/components/copilot/CopilotLauncher";
import { CopilotPage } from "@/components/copilot/CopilotPage";
import { CopilotPanel } from "@/components/copilot/CopilotPanel";
import { Dashboard } from "@/pages/Dashboard";
import { GraphExplorer } from "@/pages/GraphExplorer";
import { Investigation } from "@/pages/Investigation";
import { Login } from "@/pages/Login";
import { useAuth } from "@/store/authStore";
import { useCopilotStore } from "@/store/copilotStore";

const nav = [["/", "Dashboard", LayoutDashboard], ["/investigate", "Investigation", Search], ["/graph", "Graph Explorer", Network], ["/copilot", "AI Copilot", Sparkles]] as const;

/** Keeps the Copilot's page context in sync with the route (the Graph page manages its own selection). */
function ContextSync() {
  const { pathname } = useLocation();
  useEffect(() => {
    const m = /^\/accounts\/(ACC_\d+)/.exec(pathname);
    const page = m ? "account" : pathname === "/" ? "dashboard" : pathname.startsWith("/graph") ? "graph" : pathname.startsWith("/copilot") ? "copilot" : "other";
    if (page !== "graph") useCopilotStore.getState().setContext({ page, account_id: m?.[1] ?? null });
    useCopilotStore.getState().setHighlighted(pathname.startsWith("/graph") ? useCopilotStore.getState().highlighted : []);
  }, [pathname]);
  return null;
}

export default function App() {
  const { token, logout, username, role } = useAuth();
  const { pathname } = useLocation();
  if (!token) return <Login />;
  return (
    <div className="flex h-screen">
      <ContextSync />
      <aside className="hidden w-56 shrink-0 flex-col border-r border-line bg-card p-3 md:flex">
        <div className="mb-4 flex items-center gap-2 px-2 font-semibold"><Sparkles size={16} className="text-accent" /> FraudGraph AI</div>
        {nav.map(([to, label, Icon]) => (
          <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `mb-1 flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${isActive ? "bg-accent/15 text-accent" : "text-muted hover:text-fg"}`}><Icon size={16} />{label}</NavLink>
        ))}
        <div className="mt-auto space-y-1 text-xs text-muted">
          <button onClick={() => document.documentElement.classList.toggle("dark")} className="flex items-center gap-2 px-3 py-1 hover:text-fg"><Sun size={14} /> Toggle theme</button>
          <button onClick={logout} className="flex items-center gap-2 px-3 py-1 hover:text-fg"><LogOut size={14} /> {username} ({role})</button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/investigate" element={<Investigation />} />
          <Route path="/accounts/:id" element={<Investigation />} />
          <Route path="/graph" element={<GraphExplorer />} />
          <Route path="/copilot" element={<CopilotPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
      {pathname !== "/copilot" && <CopilotLauncher />}
      {pathname !== "/copilot" && <CopilotPanel />}
    </div>
  );
}
