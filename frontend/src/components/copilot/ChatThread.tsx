import { Sparkles } from "lucide-react";
import { useEffect, useRef } from "react";
import { useCopilotStore } from "@/store/copilotStore";
import type { ChatMessage } from "@/types/copilot";
import { MessageBubble } from "./MessageBubble";
import { SuggestionChips } from "./SuggestionChips";

export function ChatThread({ onSend, onRetry, loading }: { onSend: (q: string) => void; onRetry: (m: ChatMessage) => void; loading?: boolean }) {
  const { messages, context, llmDown } = useCopilotStore();
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  return (
    <div className="flex-1 space-y-3 overflow-y-auto p-3 scroll-thin">
      {llmDown && <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-300">The AI assistant is unavailable right now. Fraud detection, alerts and dashboards still work normally.</div>}
      {loading && [0, 1, 2].map((i) => <div key={i} className="h-12 animate-pulse rounded-2xl bg-card" />)}
      {!loading && messages.length === 0 && (
        <div className="py-6 text-center">
          <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-2"><Sparkles size={18} className="text-white" /></div>
          <h3 className="font-semibold">Hi, I'm FraudGraph Copilot</h3>
          <p className="mt-1 text-xs text-muted">I investigate the transaction graph using real data: risk explanations, money cycles, fraud rings, alerts and more. I assist you; I don't make final fraud decisions.</p>
          <SuggestionChips ctx={context} onPick={onSend} />
        </div>
      )}
      {messages.map((m) => <MessageBubble key={m.id} m={m} onRetry={onRetry} />)}
      <div ref={end} />
    </div>
  );
}
