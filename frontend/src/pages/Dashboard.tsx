import { useQuery } from "@tanstack/react-query";
import { NodeChip } from "@/components/copilot/NodeChip";
import { RISK, inr } from "@/lib/risk";
import { getDashboard } from "@/services/api/copilot";
import type { RiskLevel } from "@/types/copilot";

const card = "rounded-3xl border border-line bg-card p-5";

export function Dashboard() {
  const { data } = useQuery({ queryKey: ["dash"], queryFn: getDashboard });
  if (!data) return <div className="p-6 text-muted">Loading…</div>;
  const s = data.stats, levels = s.accounts_by_risk_level as Record<RiskLevel, number>;
  const total = Object.values(levels).reduce((a, b) => a + b, 0) || 1;
  return (
    <div className="grid gap-3 lg:grid-cols-3">
      <div className={`${card} border-rose-500/20 bg-gradient-to-br from-rose-500/15 to-transparent lg:col-span-2`}>
        <div className="text-sm text-muted">Amount at risk</div>
        <div className="mt-1 font-mono text-5xl font-semibold tracking-tight">{inr(s.amount_at_risk)}</div>
        <div className="mt-2 text-sm text-muted">{s.flagged_accounts} flagged accounts · {s.fraud_rate_pct}% of transactions touch them</div>
        <div className="mt-6 flex h-3 overflow-hidden rounded-full bg-bg">
          {(Object.keys(levels) as RiskLevel[]).map((l) => <div key={l} style={{ width: `${(levels[l] / total) * 100}%`, background: RISK[l].hex }} title={`${l}: ${levels[l]}`} />)}
        </div>
        <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted">
          {(Object.keys(levels) as RiskLevel[]).map((l) => <span key={l} className="flex items-center gap-1"><span className={`h-2 w-2 rounded-full ${RISK[l].dot}`} />{l} {levels[l]}</span>)}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-1">
        {[["Active alerts", s.active_alerts], ["Accounts", s.total_accounts], ["Transactions", s.total_transactions]].map(([k, v]) => (
          <div key={String(k)} className={card}><div className="text-xs text-muted">{k}</div><div className="mt-1 font-mono text-2xl">{String(v)}</div></div>
        ))}
      </div>
      <div className={`${card} lg:col-span-3`}>
        <h2 className="mb-3 font-medium">Highest-risk accounts</h2>
        {data.top_risky.map((r) => (
          <div key={r.account_id} className="flex items-center gap-3 border-t border-line py-2 text-sm">
            <NodeChip id={r.account_id} />
            <span className={`rounded-full px-2 py-0.5 text-xs ${RISK[r.risk_level].bg} ${RISK[r.risk_level].text}`}>{r.risk_score} · {r.risk_level}</span>
            <span className="ml-auto flex flex-wrap justify-end gap-1">{r.rules.map((x) => <span key={x} className="rounded-full border border-line px-2 py-0.5 text-[11px] text-muted">{x.toLowerCase().replace(/_/g, " ")}</span>)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
