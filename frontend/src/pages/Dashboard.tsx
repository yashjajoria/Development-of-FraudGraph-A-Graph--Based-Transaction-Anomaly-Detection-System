import { useQuery } from "@tanstack/react-query";
import { NodeChip } from "@/components/copilot/NodeChip";
import { RISK, inr } from "@/lib/risk";
import { getDashboard } from "@/services/api/copilot";

export function Dashboard() {
  const { data } = useQuery({ queryKey: ["dash"], queryFn: getDashboard });
  if (!data) return <div className="p-6 text-muted">Loading…</div>;
  const s = data.stats;
  const cards = [["Accounts", s.total_accounts], ["Transactions", s.total_transactions], ["Flagged accounts", s.flagged_accounts],
    ["Fraud rate", `${s.fraud_rate_pct}%`], ["Amount at risk", inr(s.amount_at_risk)], ["Active alerts", s.active_alerts]];
  return (
    <div className="space-y-6 p-6">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        {cards.map(([k, v]) => <div key={String(k)} className="rounded-2xl border border-line bg-card p-4"><div className="text-xs text-muted">{k}</div><div className="mt-1 font-mono text-xl">{String(v)}</div></div>)}
      </div>
      <div className="rounded-2xl border border-line bg-card p-4">
        <h2 className="mb-2 text-sm font-medium">Top risky accounts</h2>
        <table className="w-full text-sm"><tbody>
          {data.top_risky.map((r) => (
            <tr key={r.account_id} className="border-t border-line">
              <td className="py-1.5"><NodeChip id={r.account_id} /></td>
              <td className={RISK[r.risk_level].text}>{r.risk_score} · {r.risk_level}</td>
              <td className="text-xs text-muted">{r.rules.join(", ")}</td>
            </tr>))}
        </tbody></table>
      </div>
    </div>
  );
}
