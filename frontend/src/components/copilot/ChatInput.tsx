import { useQuery } from "@tanstack/react-query";
import { Send, Square } from "lucide-react";
import { useRef, useState } from "react";
import { searchAccounts } from "@/services/api/copilot";
import { RISK } from "@/lib/risk";

const MAX = 2000;

export function ChatInput({ onSend, onStop, streaming }: { onSend: (t: string) => void; onStop: () => void; streaming: boolean }) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  const mention = /@(\w*)$/.exec(text.slice(0, ref.current?.selectionStart ?? text.length));
  const { data: hits } = useQuery({ queryKey: ["mention", mention?.[1]], queryFn: () => searchAccounts(mention![1]), enabled: !!mention });
  const submit = () => { if (text.trim() && !streaming) { onSend(text.trim()); setText(""); } };
  const pick = (id: string) => { setText(text.replace(/@(\w*)$/, id + " ")); ref.current?.focus(); };
  return (
    <div className="relative border-t border-line p-3">
      {mention && hits && hits.length > 0 && (
        <div className="absolute bottom-full left-3 right-3 mb-1 max-h-44 overflow-auto rounded-xl border border-line bg-card shadow-lg">
          {hits.map((h) => (
            <button key={h.id} onClick={() => pick(h.id)} className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-accent/10">
              <span className={`h-2 w-2 rounded-full ${RISK[h.risk_level].dot}`} /><span className="font-mono">{h.id}</span><span className="text-muted">{h.type} · {h.risk_level}</span>
            </button>))}
        </div>
      )}
      <div className="flex items-end gap-2 rounded-2xl border border-line bg-bg p-2 focus-within:border-accent">
        <textarea ref={ref} rows={1} value={text} maxLength={MAX} disabled={streaming} placeholder="Ask about accounts, alerts, risk…  (@ to mention an account)"
          onChange={(e) => { setText(e.target.value); e.target.style.height = "auto"; e.target.style.height = Math.min(e.target.scrollHeight, 140) + "px"; }}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
          className="max-h-36 flex-1 resize-none bg-transparent px-1 text-sm outline-none disabled:opacity-50" />
        {streaming
          ? <button aria-label="Stop" onClick={onStop} className="rounded-lg bg-rose-500 p-2 text-white"><Square size={14} /></button>
          : <button aria-label="Send" onClick={submit} disabled={!text.trim()} className="rounded-lg bg-gradient-to-r from-accent to-accent-2 p-2 text-white disabled:opacity-40"><Send size={14} /></button>}
      </div>
      <div className="mt-1 text-right text-[10px] text-muted">{text.length}/{MAX}</div>
    </div>
  );
}
