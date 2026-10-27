import { useQuery } from "@tanstack/react-query";
import { Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { GraphView } from "@/components/GraphView";
import { RISK } from "@/lib/risk";
import { getAccount, getGraph } from "@/services/api/copilot";
import { useCopilotStore } from "@/store/copilotStore";

export function GraphExplorer() {
  const { data } = useQuery({ queryKey: ["graph"], queryFn: () => getGraph() });
  const { highlighted, setHighlighted, openWith, setContext } = useCopilotStore();
  const [sel, setSel] = useState<string | null>(null);
  const { data: acct } = useQuery({ queryKey: ["acct", sel], queryFn: () => getAccount(sel!), enabled: !!sel });
  useEffect(() => { setContext({ page: "graph", account_id: sel, selected_nodes: sel ? [sel] : [] }); }, [sel, setContext]);
  if (!data) return <div className="p-6 text-muted">Loading graph…</div>;
  return (
    <div className="relative h-full min-h-[480px] overflow-hidden rounded-3xl border border-line bg-card">
      <GraphView data={data} highlighted={highlighted} onSelect={setSel} />
      {highlighted.length > 0 && (
        <button onClick={() => setHighlighted([])} className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full border border-accent bg-card px-3 py-1 text-xs"><X size={12} /> Clear highlight ({highlighted.length})</button>
      )}
      {sel && acct && (
        <aside className="absolute bottom-3 right-3 top-3 w-64 space-y-2 rounded-2xl border border-line bg-card p-4 text-sm shadow-xl">
          <div className="flex items-center justify-between"><b className="font-mono">{acct.id}</b><button onClick={() => setSel(null)}><X size={14} /></button></div>
          <div className={RISK[acct.risk_level].text}>Risk {acct.risk_score} · {acct.risk_level}</div>
          <div className="text-xs text-muted">{acct.type} · {acct.community_id ?? "no community"}</div>
          <Link to={`/accounts/${acct.id}`} className="block text-xs text-accent underline">Open investigation</Link>
          <button onClick={() => openWith({ page: "graph", account_id: acct.id, selected_nodes: [acct.id] })} className="inline-flex w-full items-center justify-center gap-1 rounded-xl bg-gradient-to-r from-accent to-accent-2 py-1.5 text-xs text-white"><Sparkles size={12} /> Ask AI about this account</button>
        </aside>
      )}
    </div>
  );
}
