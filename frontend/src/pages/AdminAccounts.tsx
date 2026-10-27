import { useMutation } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "@/services/api/client";
import { createAccount } from "@/services/api/copilot";
import type { AccountDetail } from "@/types/copilot";

const input = "w-full rounded-2xl border border-line bg-bg px-4 py-2 text-sm outline-none focus:border-accent";

export function AdminAccounts() {
  const [f, setF] = useState({ type: "user" as "user" | "merchant", name: "", phone: "", card: "", device_id: "" });
  const [created, setCreated] = useState<AccountDetail[]>([]);
  const m = useMutation({
    mutationFn: () => createAccount({ type: f.type, name: f.name, phone: f.phone || undefined, card: f.card || undefined, device_id: f.device_id || undefined }),
    onSuccess: (a) => { setCreated([a, ...created]); setF({ ...f, name: "", phone: "", card: "", device_id: "" }); },
  });
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });
  const err = m.error instanceof ApiError ? (m.error.status === 422 ? "Check the fields: phone is 10-13 digits, card is 16 digits." : m.error.message) : m.error ? "Failed to create account" : "";
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <form onSubmit={(e) => { e.preventDefault(); m.mutate(); }} className="space-y-3 rounded-3xl border border-line bg-card p-5">
        <h2 className="flex items-center gap-2 font-medium"><UserPlus size={16} className="text-accent" /> New account</h2>
        <select value={f.type} onChange={set("type")} className={input}><option value="user">User</option><option value="merchant">Merchant</option></select>
        <input required maxLength={60} value={f.name} onChange={set("name")} placeholder="Name" className={input} />
        <input value={f.phone} onChange={set("phone")} placeholder="Phone (optional), e.g. +919876543210" className={input} />
        <input value={f.card} onChange={set("card")} placeholder="Card number (optional, 16 digits)" className={input} />
        <input value={f.device_id} onChange={set("device_id")} placeholder="Device ID (optional)" className={input} />
        <p className="text-xs text-muted">Only the last 4 digits of phone and card are stored.</p>
        {err && <p className="text-xs text-rose-400">{err}</p>}
        <button disabled={m.isPending || !f.name.trim()} className="w-full rounded-2xl bg-gradient-to-r from-accent to-accent-2 py-2.5 text-sm font-medium text-white disabled:opacity-50">{m.isPending ? "Creating…" : "Create account"}</button>
      </form>
      <div className="rounded-3xl border border-line bg-card p-5">
        <h2 className="mb-2 font-medium">Created this session</h2>
        {created.length === 0 && <p className="text-sm text-muted">New accounts appear here and become searchable, visible to the AI and openable in Investigation.</p>}
        {created.map((a) => (
          <Link key={a.id} to={`/accounts/${a.id}`} className="flex items-center justify-between border-t border-line py-2 text-sm hover:text-accent">
            <span><span className="font-mono">{a.id}</span> <span className="text-muted">· {a.name}</span></span><span className="text-xs text-muted">{a.type} · risk {a.risk_score}</span>
          </Link>))}
      </div>
    </div>
  );
}
