import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { RISK, inr } from "@/lib/risk";
import { getAccount, searchAccounts } from "@/services/api/copilot";
import { useCopilotStore } from "@/store/copilotStore";

const card = "rounded-3xl border border-line bg-card p-5";

export function Investigation() {
  const { id } = useParams();
  const [q, setQ] = useState("");
  const openWith = useCopilotStore((s) => s.openWith);
  const { data: hits } = useQuery({ queryKey: ["srch", q], queryFn: () => searchAccounts(q), enabled: !id });
  const { data: a, error } = useQuery({ queryKey: ["acct", id], queryFn: () => getAccount(id!), enabled: !!id, retry: false });
  if (!id)
    return (
      <div className={`${card} space-y-3`}>
        <h2 className="font-medium">Find an account</h2>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Account number, e.g. 9001" className="w-full max-w-sm rounded-full border border-line bg-bg px-4 py-2 text-sm" />
        {hits?.map((h) => <Link key={h.id} to={`/accounts/${h.id}`} className="flex max-w-sm items-center justify-between rounded-2xl border border-line bg-bg px-4 py-2 font-mono text-sm hover:border-accent">{h.id}<span className={`text-xs ${RISK[h.risk_level].text}`}>{h.risk_level}</span></Link>)}
      </div>
    );
  if (error) return <div className={`${card} text-rose-400`}>Account {id} not found.</div>;
  if (!a) return <div className="p-6 text-muted">Loading…</div>;
  const R = RISK[a.risk_level];
  return (
    <div className="grid gap-3 lg:grid-cols-3">
      <div className={`${card} flex flex-wrap items-center gap-3 lg:col-span-3`}>
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-bg font-mono text-xs text-muted">{a.type.slice(0, 3).toUpperCase()}</div>
        <div><div className="font-mono text-xl font-semibold">{a.id}</div><div className="text-xs text-muted">{a.name} · {a.community_id ?? "no community"}</div></div>
        <div className="ml-auto flex flex-wrap gap-2">
          {a.explanation.contributions.map((c) => <span key={c.rule} className="rounded-full border border-line px-3 py-1 text-xs">{c.rule.toLowerCase().replace(/_/g, " ")}</span>)}
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${R.bg} ${R.text}`}>● {a.risk_level}</span>
        </div>
      </div>

      <div className={`${card} lg:col-span-2`} style={{ background: `linear-gradient(135deg, ${R.hex}22, transparent 60%)`, borderColor: `${R.hex}33` }}>
        <div className="text-sm text-muted">Risk score</div>
        <div className="mt-1 flex items-end gap-2"><span className="font-mono text-7xl font-semibold leading-none">{a.risk_score}</span><span className="pb-2 text-xl text-muted">/100</span></div>
        <div className="relative mt-8 h-3 rounded-full" style={{ background: "linear-gradient(90deg,#10b981 0 25%,#f59e0b 25% 50%,#f97316 50% 75%,#f43f5e 75%)" }}>
          <div className="absolute -top-1.5 h-6 w-1 rounded bg-white shadow" style={{ left: `calc(${a.risk_score}% - 2px)` }} />
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-muted"><span>0 Low</span><span>25 Medium</span><span>50 High</span><span>75 Critical</span><span>100</span></div>
      </div>

      <div className={`${card} flex flex-col`}>
        <h2 className="font-medium">Investigate with AI</h2>
        <p className="mt-1 text-sm text-muted">Ask why this account is flagged, who it moved money to, or whether it belongs to a ring. Answers use live tool data.</p>
        <button onClick={() => openWith({ page: "account", account_id: a.id })} className="mt-auto inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-accent to-accent-2 py-3 text-sm font-medium text-white shadow-glow"><Sparkles size={16} /> Ask AI about this account</button>
      </div>

      <div className={card}>
        <h2 className="mb-2 font-medium">Why this score</h2>
        {a.explanation.contributions.length === 0 && <p className="text-sm text-muted">No risk rules triggered.</p>}
        {a.explanation.contributions.map((c) => (
          <div key={c.rule} className="border-t border-line py-2 text-sm">
            <div className="flex justify-between"><b>{c.name}</b><span className="font-mono text-muted">+{c.points}</span></div>
            <div className="mt-1 h-1.5 rounded-full bg-bg"><div className="h-full rounded-full" style={{ width: `${c.points}%`, background: R.hex }} /></div>
            <div className="mt-1 text-xs text-muted">{c.reason}</div>
          </div>))}
      </div>

      <div className={card}>
        <h2 className="mb-2 font-medium">Linked accounts</h2>
        {a.neighbors.length === 0 && <p className="text-sm text-muted">No connected accounts.</p>}
        {a.neighbors.map((n) => (
          <Link key={n.account_id} to={`/accounts/${n.account_id}`} className="flex items-center justify-between border-t border-line py-2 text-sm hover:text-accent">
            <span><span className="font-mono">{n.account_id}</span><span className={`block text-xs ${RISK[n.risk_level].text}`}>{n.risk_level}</span></span>
            <span className="text-right font-mono">{inr(n.total_amount)}<span className="block text-xs text-muted">{n.txn_count} txns</span></span>
          </Link>))}
      </div>

      <div className={card}>
        <h2 className="mb-2 font-medium">Profile</h2>
        {[["Type", a.type], ["Phone", a.phone], ["Card", a.card], ["Device", a.device_id], ["Alerts", a.alerts.join(", ") || "—"]].map(([k, v]) => <div key={k} className="flex justify-between border-t border-line py-2 text-sm"><span className="text-muted">{k}</span><span className="font-mono">{v}</span></div>)}
      </div>
    </div>
  );
}
