import { useQuery } from "@tanstack/react-query";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { useMemo, useState } from "react";
import { GraphView } from "@/components/GraphView";
import { getGraph } from "@/services/api/copilot";
import { useCopilotStore } from "@/store/copilotStore";
import { ContextPill } from "./ContextPill";
import { CopilotChat } from "./CopilotChat";
import { SessionSidebar } from "./SessionSidebar";

export function CopilotPage() {
  const [showGraph, setShowGraph] = useState(true);
  const messages = useCopilotStore((s) => s.messages);
  // every account the AI has referenced in this conversation, in order
  const ids = useMemo(() => [...new Set(messages.flatMap((m) => m.blocks?.referenced_nodes ?? []))].slice(0, 40), [messages]);
  const key = ids.join(",");
  const { data } = useQuery({ queryKey: ["mini", key], queryFn: () => getGraph(ids), enabled: ids.length > 0 && showGraph });
  return (
    <div className="flex h-full">
      <SessionSidebar />
      <section className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center justify-between border-b border-line p-3">
          <ContextPill />
          <button onClick={() => setShowGraph(!showGraph)} title="Toggle graph" className="text-muted hover:text-fg">{showGraph ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}</button>
        </div>
        <CopilotChat />
      </section>
      {showGraph && (
        <aside className="hidden w-80 shrink-0 border-l border-line lg:block">
          <div className="border-b border-line p-3 text-xs text-muted">Accounts in this conversation ({ids.length})</div>
          <div className="h-[calc(100%-2.5rem)]">
            {data ? <GraphView data={data} compact /> : <p className="p-4 text-xs text-muted">Referenced accounts will appear here as the AI mentions them.</p>}
          </div>
        </aside>
      )}
    </div>
  );
}
