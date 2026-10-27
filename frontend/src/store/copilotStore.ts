import { create } from "zustand";
import type { ChatMessage, Confirmation, PageContext, StoredMessage } from "@/types/copilot";

interface CopilotState {
  open: boolean;
  sessionId: string | null;
  messages: ChatMessage[];
  context: PageContext | null;
  streaming: boolean;
  llmDown: boolean;
  highlighted: string[]; // nodes to glow in the Graph Explorer (shared with it)
  setOpen: (o: boolean) => void;
  openWith: (ctx: PageContext) => void;
  setContext: (c: PageContext | null) => void;
  newChat: () => void;
  setSession: (id: string | null) => void;
  loadMessages: (id: string, msgs: StoredMessage[]) => void;
  addMessage: (m: ChatMessage) => void;
  removeMessage: (id: string) => void;
  patchMessage: (id: string, fn: (m: ChatMessage) => ChatMessage) => void;
  patchConfirmation: (actionId: string, patch: Partial<Confirmation>) => void;
  setStreaming: (s: boolean) => void;
  setLlmDown: (d: boolean) => void;
  setHighlighted: (ids: string[]) => void;
}

export const useCopilotStore = create<CopilotState>((set) => ({
  open: false, sessionId: null, messages: [], context: null, streaming: false, llmDown: false, highlighted: [],
  setOpen: (open) => set({ open }),
  openWith: (context) => set({ open: true, context }),
  setContext: (context) => set({ context }),
  newChat: () => set({ sessionId: null, messages: [], streaming: false }),
  setSession: (sessionId) => set({ sessionId }),
  loadMessages: (sessionId, msgs) =>
    set({
      sessionId,
      messages: msgs.map((m) => ({
        id: m.id, role: m.role, content: m.content, blocks: m.blocks ?? undefined,
        confirmations: m.blocks?.confirmations ?? [],
        tools: (m.tool_calls ?? []).map((t, i) => ({ call_id: `${m.id}-${i}`, tool: t.tool, label: t.tool.replace(/_/g, " "), status: "done" as const, summary: t.summary, duration_ms: t.duration_ms })),
      })),
    }),
  addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  removeMessage: (id) => set((s) => ({ messages: s.messages.filter((m) => m.id !== id) })),
  patchMessage: (id, fn) => set((s) => ({ messages: s.messages.map((m) => (m.id === id ? fn(m) : m)) })),
  patchConfirmation: (actionId, patch) =>
    set((s) => ({ messages: s.messages.map((m) => ({ ...m, confirmations: m.confirmations.map((c) => (c.action_id === actionId ? { ...c, ...patch } : c)) })) })),
  setStreaming: (streaming) => set({ streaming }),
  setLlmDown: (llmDown) => set({ llmDown }),
  setHighlighted: (highlighted) => set({ highlighted }),
}));
