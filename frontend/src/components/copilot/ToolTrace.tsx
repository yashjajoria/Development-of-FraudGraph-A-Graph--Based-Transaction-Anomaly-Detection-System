import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown, Loader2, Search } from "lucide-react";
import { useState } from "react";
import type { ToolStep } from "@/types/copilot";

export function ToolTrace({ tools, streaming }: { tools: ToolStep[]; streaming?: boolean }) {
  const [open, setOpen] = useState(false);
  if (!tools.length) return null;
  const done = !streaming && tools.every((t) => t.status === "done");
  const show = !done || open;
  return (
    <div className="mb-2 text-xs text-muted">
      {done && (
        <button onClick={() => setOpen(!open)} className="flex items-center gap-1 hover:text-fg">
          <Check size={12} className="text-emerald-400" /> Used {tools.length} tool{tools.length > 1 ? "s" : ""}
          <ChevronDown size={12} className={open ? "rotate-180" : ""} />
        </button>
      )}
      <AnimatePresence initial={false}>
        {show && tools.map((t) => (
          <motion.div key={t.call_id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="mt-1 flex items-center gap-1.5">
            {t.status === "running" ? <Loader2 size={12} className="animate-spin" /> : <Search size={12} />}
            <span>{t.label}</span>
            {t.status === "done" && <span className="text-emerald-400">✓ {t.summary} ({t.duration_ms} ms)</span>}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
