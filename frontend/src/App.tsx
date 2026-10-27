import { Bell, LayoutDashboard, LogOut, Network, Search, Sparkles, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
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

function TopBar() {
  const { username, role } = useAuth();
  const { pathname } = useLocation();
  const go = useNavigate();
  const [q, setQ] = useState("");
  const title = pathname.startsWith("/accounts") ? "Account investigation" : (nav.find(([to]) => to === pathname)?.[1] ?? "FraudGraph AI");
  return (
    <header className="flex h-16 shrink-0 items-center gap-3 rounded-3xl border border-line bg-card px-5">
      <h1 className="font-semibold">{title}</h1>
      <span className="hidden text-xs text-muted sm:inline">Live · synthetic dataset</span>
      <form className="ml-auto hidden w-72 items-center gap-2 rounded-full border border-line bg-bg px-3 py-1.5 md:flex"
        onSubmit={(e) => { e.preventDefault(); const id = /^\d+$/.test(q) ? `ACC_${q}` : q.toUpperCase(); if (/^ACC_\d+$/.test(id)) { go(`/accounts/${id}`); setQ(""); } }}>
        <Search size={14} className="text-muted" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Jump to account, e.g. 9001" className="w-full bg-transparent text-sm outline-none" />
      </form>
      <button aria-label="Notifications" className="rounded-full border border-line bg-bg p-2 text-muted"><Bell size={16} /></button>
      <div className="flex items-center gap-2 rounded-full border border-line bg-bg py-1 pl-1 pr-3 text-sm">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-2 text-xs font-semibold uppercase text-white">{username?.[0]}</span>
        <span className="hidden sm:block">{username} <span className="text-xs text-muted">· {role}</span></span>
      </div>
    </header>
  );
}

export default function App() {
  const { token, logout } = useAuth();
  const { pathname } = useLocation();
  if (!token) return <Login />;
  return (
    <div className="flex h-screen gap-3 p-3">
      <ContextSync />
      <nav className="hidden w-[68px] shrink-0 flex-col items-center gap-2 rounded-3xl border border-line bg-card py-4 md:flex">
        <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-accent to-accent-2"><Network size={18} className="text-white" /></div>
        {nav.map(([to, label, Icon]) => (
          <NavLink key={to} to={to} end={to === "/"} title={label} aria-label={label}
            className={({ isActive }) => `flex h-11 w-11 items-center justify-center rounded-2xl transition ${isActive ? "bg-accent text-white shadow-glow" : "text-muted hover:bg-bg hover:text-fg"}`}><Icon size={18} /></NavLink>
        ))}
        <button title="Toggle theme" onClick={() => document.documentElement.classList.toggle("dark")} className="mt-auto flex h-11 w-11 items-center justify-center rounded-2xl text-muted hover:text-fg"><Sun size={18} /></button>
        <button title="Sign out" onClick={logout} className="flex h-11 w-11 items-center justify-center rounded-2xl text-rose-400 hover:bg-rose-500/10"><LogOut size={18} /></button>
      </nav>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <TopBar />
        <main className="min-h-0 flex-1 overflow-y-auto rounded-3xl">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/investigate" element={<Investigation />} />
            <Route path="/accounts/:id" element={<Investigation />} />
            <Route path="/graph" element={<GraphExplorer />} />
            <Route path="/copilot" element={<div className="h-full overflow-hidden rounded-3xl border border-line bg-card"><CopilotPage /></div>} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
      </div>
      {pathname !== "/copilot" && <CopilotLauncher />}
      {pathname !== "/copilot" && <CopilotPanel />}
    </div>
  );
}
