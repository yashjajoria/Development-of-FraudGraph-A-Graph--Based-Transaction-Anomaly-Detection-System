import { Copy, Network, RefreshCw, Sparkles, ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import { useNavigate } from "react-router-dom";
import { sendFeedback } from "@/services/api/copilot";
import { useCopilotStore } from "@/store/copilotStore";
import type { ChatMessage } from "@/types/copilot";
import { ConfirmActionCard } from "./ConfirmActionCard";
import { NodeChip } from "./NodeChip";
import { ResultChart, ResultTable } from "./ResultBlocks";
import { ToolTrace } from "./ToolTrace";

/** Turn account IDs into node: links so the markdown renderer can swap them for NodeChips. */
export const linkIds = (s: string) => s.replace(/\b(ACC_\d+)\b/g, "[$1](node:$1)");

export function MessageBubble({ m, onRetry }: { m: ChatMessage; onRetry: (m: ChatMessage) => void }) {
  const nav = useNavigate();
  const [comment, setComment] = useState<string | null>(null);
  const patch = useCopilotStore((s) => s.patchMessage);
  const setHighlighted = useCopilotStore((s) => s.setHighlighted);
  const setOpen = useCopilotStore((s) => s.setOpen);

  if (m.role === "user")
    return <div className="ml-auto max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-accent px-3 py-2 text-sm text-white">{m.content}</div>;

  const rate = (r: "up" | "down", c?: string) => {
    patch(m.id, (x) => ({ ...x, feedback: r }));
    sendFeedback(m.id, r, c).catch(() => {});
  };
  const nodes = m.blocks?.referenced_nodes ?? [];
  return (
    <div className="group flex gap-2">
      <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-2"><Sparkles size={14} className="text-white" /></div>
      <div className="min-w-0 flex-1 rounded-2xl rounded-tl-sm border border-line bg-card px-3 py-2 text-sm">
        <ToolTrace tools={m.tools} streaming={m.streaming} />
        <div className="md break-words">
          <ReactMarkdown remarkPlugins={[remarkGfm]} urlTransform={(u) => (u.startsWith("node:") ? u : defaultUrlTransform(u))}
            components={{ a: ({ href, children }) => href?.startsWith("node:") ? <NodeChip id={href.slice(5)} /> : <a href={href} target="_blank" rel="noreferrer" className="text-accent underline">{children}</a> }}>
            {linkIds(m.content)}
          </ReactMarkdown>
          {m.streaming && <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-accent align-middle" />}
        </div>
        {m.blocks?.table && <ResultTable t={m.blocks.table} />}
        {m.blocks?.chart && <ResultChart c={m.blocks.chart} />}
        {m.confirmations.map((c) => <ConfirmActionCard key={c.action_id} c={c} />)}
        {nodes.length > 0 && !m.streaming && (
          <button onClick={() => { setHighlighted(nodes); setOpen(false); nav("/graph"); }} className="mt-2 inline-flex items-center gap-1 rounded-lg border border-line px-2 py-1 text-xs hover:border-accent">
            <Network size={12} /> Show on graph ({nodes.length})
          </button>
        )}
        {m.error && (
          <div className="mt-2 rounded-xl border border-rose-500/40 bg-rose-500/10 p-2 text-xs text-rose-300">
            {m.error.message}
            {m.error.retryable && <button onClick={() => onRetry(m)} className="ml-2 underline">Retry</button>}
          </div>
        )}
        {!m.streaming && !m.error && m.content && (
          <>
            <div className="mt-1 text-[10px] text-muted">AI generated — verify before acting</div>
            <div className="mt-1 flex gap-2 text-muted opacity-0 transition group-hover:opacity-100">
              <button title="Copy" onClick={() => navigator.clipboard?.writeText(m.content)}><Copy size={13} /></button>
              <button title="Regenerate" onClick={() => onRetry(m)}><RefreshCw size={13} /></button>
              <button title="Good" onClick={() => rate("up")} className={m.feedback === "up" ? "text-emerald-400" : ""}><ThumbsUp size={13} /></button>
              <button title="Bad" onClick={() => { rate("down"); setComment(""); }} className={m.feedback === "down" ? "text-rose-400" : ""}><ThumbsDown size={13} /></button>
            </div>
            {comment !== null && (
              <form className="mt-1 flex gap-1" onSubmit={(e) => { e.preventDefault(); rate("down", comment); setComment(null); }}>
                <input autoFocus value={comment} onChange={(e) => setComment(e.target.value)} placeholder="What was wrong? (optional)" className="flex-1 rounded-lg border border-line bg-bg px-2 py-1 text-xs" />
                <button className="rounded-lg bg-accent px-2 text-xs text-white">Send</button>
              </form>
            )}
          </>
        )}
      </div>
    </div>
  );
}
