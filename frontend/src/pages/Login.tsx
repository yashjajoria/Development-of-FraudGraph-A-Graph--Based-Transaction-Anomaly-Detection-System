import { useState } from "react";
import { Sparkles } from "lucide-react";
import { login } from "@/services/api/copilot";
import { useAuth } from "@/store/authStore";

export function Login() {
  const [u, setU] = useState("analyst"), [p, setP] = useState(""), [err, setErr] = useState("");
  const doLogin = useAuth((s) => s.login);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setErr("");
    try { const r = await login(u, p); doLogin(r.access_token, u, r.role); } catch { setErr("Invalid username or password"); }
  };
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-3 rounded-2xl border border-line bg-card p-6">
        <div className="flex items-center gap-2 text-lg font-semibold"><Sparkles className="text-accent" /> FraudGraph AI</div>
        <select value={u} onChange={(e) => setU(e.target.value)} className="w-full rounded-lg border border-line bg-bg p-2 text-sm">
          <option value="analyst">analyst</option><option value="admin">admin</option><option value="viewer">viewer (read-only)</option>
        </select>
        <input type="password" value={p} onChange={(e) => setP(e.target.value)} placeholder="Password" className="w-full rounded-lg border border-line bg-bg p-2 text-sm" />
        {err && <p className="text-xs text-rose-400">{err}</p>}
        <button className="w-full rounded-lg bg-gradient-to-r from-accent to-accent-2 py-2 text-sm font-medium text-white">Sign in</button>
      </form>
    </div>
  );
}
