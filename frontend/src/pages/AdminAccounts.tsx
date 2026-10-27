import { useMutation } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "@/services/api/client";
import { createAccount, importCsv } from "@/services/api/copilot";
import type { AccountDetail } from "@/types/copilot";

const TEMPLATES = {
  accounts: "type,name,phone,card,device_id\nuser,Asha Verma,+919876543210,4111111111111111,DEV_A1\nmerchant,Corner Store,,,\n",
  transactions: "sender_id,receiver_id,amount,timestamp,note\nACC_10000,ACC_10001,9000,2026-10-01T10:00:00,payment\n",
};

function CsvUpload({ kind, hint }: { kind: "accounts" | "transactions"; hint: string }) {
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const m = useMutation({
    mutationFn: async (f: File) => importCsv(kind, await f.text()),
    onSuccess: (r) => setMsg({ ok: true, text: `Imported ${r.imported} ${kind}.` + (r.newly_flagged ? ` Newly flagged accounts: ${r.newly_flagged.length ? r.newly_flagged.join(", ") : "none"}. Total alerts: ${r.total_alerts}.` : "") }),
    onError: (e) => setMsg({ ok: false, text: e instanceof ApiError ? e.message : "Upload failed" }),
  });
  return (
    <div className="rounded-3xl border border-line bg-card p-5">
      <h2 className="font-medium">Import {kind} (CSV)</h2>
      <p className="mt-1 text-xs text-muted">{hint}</p>
      <div className="mt-3 flex items-center gap-3">
        <input type="file" accept=".csv,text/csv" disabled={m.isPending} onChange={(e) => { const f = e.target.files?.[0]; if (f) { setMsg(null); m.mutate(f); } e.target.value = ""; }} className="text-xs" />
        <a download={`${kind}_template.csv`} href={`data:text/csv;charset=utf-8,${encodeURIComponent(TEMPLATES[kind])}`} className="text-xs text-accent underline">Template</a>
      </div>
      {m.isPending && <p className="mt-2 text-xs text-muted">Importing and re-scoring…</p>}
      {msg && <pre className={`mt-2 whitespace-pre-wrap text-xs ${msg.ok ? "text-emerald-400" : "text-rose-400"}`}>{msg.text}</pre>}
    </div>
  );
}

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
      <div className="space-y-3">
        <CsvUpload kind="accounts" hint="Columns: type (user|merchant), name; optional phone, card, device_id. Up to 500 rows. If any row is invalid nothing is imported." />
        <CsvUpload kind="transactions" hint="Columns: sender_id, receiver_id, amount, timestamp (ISO); optional note. Both accounts must exist. Up to 5,000 rows. Risk scores, cycles and alerts are recalculated after upload." />
      </div>
      <div className="rounded-3xl border border-line bg-card p-5 lg:col-span-2">
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
