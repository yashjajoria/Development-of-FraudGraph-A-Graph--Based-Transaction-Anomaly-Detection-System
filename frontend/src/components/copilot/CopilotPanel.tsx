import { AnimatePresence, motion } from "framer-motion";
import { Maximize2, Plus, Sparkles, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useCopilotStore } from "@/store/copilotStore";
import { ContextPill } from "./ContextPill";
import { CopilotChat } from "./CopilotChat";

export function CopilotPanel() {
  const { open, setOpen, newChat } = useCopilotStore();
  const nav = useNavigate();
  return (
    <AnimatePresence>
      {open && (
        <motion.aside initial={{ x: 440 }} animate={{ x: 0 }} exit={{ x: 440 }} transition={{ type: "spring", stiffness: 320, damping: 32 }}
          className="fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-line bg-bg shadow-2xl sm:w-[420px]" aria-label="FraudGraph Copilot">
          <header className="border-b border-line p-3">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-accent" /><b>FraudGraph Copilot</b>
              <span className="rounded bg-gradient-to-r from-accent to-accent-2 px-1.5 text-[10px] font-bold text-white">AI</span>
              <div className="ml-auto flex gap-1 text-muted">
                <button title="New chat" onClick={newChat} className="rounded p-1 hover:text-fg"><Plus size={16} /></button>
                <button title="Expand" onClick={() => { setOpen(false); nav("/copilot"); }} className="rounded p-1 hover:text-fg"><Maximize2 size={16} /></button>
                <button title="Close" onClick={() => setOpen(false)} className="rounded p-1 hover:text-fg"><X size={16} /></button>
              </div>
            </div>
            <div className="mt-2"><ContextPill /></div>
          </header>
          <CopilotChat />
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
