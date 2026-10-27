import { Eye, X } from "lucide-react";
import { useCopilotStore } from "@/store/copilotStore";

export function ContextPill() {
  const { context, setContext } = useCopilotStore();
  if (!context) return <span className="text-xs text-muted">No page context</span>;
  const label = context.account_id ?? (context.selected_nodes?.length ? `${context.selected_nodes.length} selected nodes` : context.page);
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2 py-0.5 text-xs text-accent">
      <Eye size={12} /> Context: <span className="font-mono">{label}</span>
      <button aria-label="Clear context" onClick={() => setContext(null)}><X size={12} /></button>
    </span>
  );
}
