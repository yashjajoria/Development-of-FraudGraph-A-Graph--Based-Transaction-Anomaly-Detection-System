import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { RISK } from "@/lib/risk";
import { getAccount, searchAccounts } from "@/services/api/copilot";
import { useCopilotStore } from "@/store/copilotStore";

export function Investigation() {
  const { id } = useParams();
  const [q, setQ] = useState("");
  const openWith = useCopilotStore((s) => s.openWith);
  const { data: hits } = useQuery({ queryKey: ["srch", q], queryFn: () => searchAccounts(q), enabled: !id });
  const { data: a, error } = useQuery({ queryKey: ["acct", id], queryFn: () => getAccount(id!), enabled: !!id, retry: false });
  if (!id)
    return (
      <div className="space-y-3 p-6">
        <h1 className="text-xl font-semibold">Investigation</h1>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search account number, e.g. 9001" className="w-full max-w-sm rounded-lg border border-line bg-card p-2 text-sm" />
        {hits?.map((h) => <Link key={h.id} to={`/accounts/${h.id}`} className="block max-w-sm rounded-lg border border-line bg-card px-3 py-2 font-mono text-sm hover:border-accent">{h.id} <span className={RISK[h.risk_level].text}>{h.risk_level}</span></Link>)}
      </div>
    );
  if (error) return <div className="p-6 text-rose-400">Account {id} not found.</div>;
  if (!a) return <div className="p-6 text-muted">Loading…</div>;
  return (
    <div className="space-y-4 p-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-mono text-xl font-semibold">{a.id}</h1>
        <span className={`rounded-full px-2 py-0.5 text-xs ${RISK[a.risk_level].bg} ${RISK[a.risk_level].text}`}>{a.risk_score} · {a.risk_level}</span>
        <button onClick={() => openWith({ page: "account", account_id: a.id })} className="ml-auto inline-flex items-center gap-1 rounded-xl bg-gradient-to-r from-accent to-accent-2 px-3 py-1.5 text-sm text-white"><Sparkles size={14} /> Ask AI about this account</button>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <div className="rounded-2xl border border-line bg-card p-4 text-sm">
          <h2 className="mb-2 font-medium">Profile</h2>
          {[["Type", a.type], ["Phone", a.phone], ["Card", a.card], ["Device", a.device_id], ["Community", a.community_id ?? "—"], ["Alerts", a.alerts.join(", ") || "—"]].map(([k, v]) => <div key={k} className="flex justify-between border-t border-line py-1"><span className="text-muted">{k}</span><span className="font-mono">{v}</span></div>)}
        </div>
        <div className="rounded-2xl border border-line bg-card p-4 text-sm">
          <h2 className="mb-2 font-medium">Why this score</h2>
          {a.explanation.contributions.length === 0 && <p className="text-muted">No risk rules triggered.</p>}
          {a.explanation.contributions.map((c) => <div key={c.rule} className="border-t border-line py-1"><b>{c.name}</b> <span className="text-muted">+{c.points}</span><div className="text-xs text-muted">{c.reason}</div></div>)}
        </div>
      </div>
    </div>
  );
}
