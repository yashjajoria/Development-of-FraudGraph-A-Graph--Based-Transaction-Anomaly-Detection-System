import { useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import { getAccount } from "@/services/api/copilot";
import { RISK } from "@/lib/risk";
import { useCopilotStore } from "@/store/copilotStore";

export function NodeChip({ id }: { id: string }) {
  const nav = useNavigate(), loc = useLocation();
  const { data } = useQuery({ queryKey: ["acct", id], queryFn: () => getAccount(id), staleTime: 300_000, retry: false });
  const level = data?.risk_level;
  const click = () => {
    if (loc.pathname === "/graph") useCopilotStore.getState().setHighlighted([id]);
    else nav(`/accounts/${id}`);
  };
  return (
    <span className="group relative inline-block">
      <button onClick={click} className="inline-flex items-center gap-1 rounded-md border border-line bg-bg px-1.5 py-0.5 font-mono text-xs hover:border-accent">
        <span className={`h-2 w-2 rounded-full ${level ? RISK[level].dot : "bg-muted"}`} />{id}
      </button>
      {data && (
        <span className="pointer-events-none absolute bottom-full left-0 z-50 mb-1 hidden w-44 rounded-xl border border-line bg-card p-2 text-xs shadow-lg group-hover:block">
          <b className="font-mono">{id}</b> · {data.type}<br />
          Risk <span className={RISK[data.risk_level].text}>{data.risk_score} ({data.risk_level})</span>
        </span>
      )}
    </span>
  );
}
