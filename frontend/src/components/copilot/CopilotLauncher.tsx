import { Sparkles } from "lucide-react";
import { useEffect } from "react";
import { useCopilotStore } from "@/store/copilotStore";

export function CopilotLauncher() {
  const { open, setOpen } = useCopilotStore();
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "j") { e.preventDefault(); useCopilotStore.setState((s) => ({ open: !s.open })); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);
  if (open) return null;
  return (
    <button onClick={() => setOpen(true)} aria-label="Ask FraudGraph AI (Ctrl/Cmd+J)"
      className="pulse-ring fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-gradient-to-r from-accent to-accent-2 px-4 py-3 text-sm font-medium text-white shadow-glow">
      <Sparkles size={16} /> <span className="hidden sm:inline">Ask FraudGraph AI</span>
    </button>
  );
}
