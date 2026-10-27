import { useCallback } from "react";
import { useCopilotStream } from "@/hooks/useCopilotStream";
import { useCopilotStore } from "@/store/copilotStore";
import type { ChatMessage } from "@/types/copilot";
import { ChatInput } from "./ChatInput";
import { ChatThread } from "./ChatThread";

/** Thread + input wired to the stream hook. Used by both the slide-in panel and the full page. */
export function CopilotChat({ loading }: { loading?: boolean }) {
  const { send, stop } = useCopilotStream();
  const streaming = useCopilotStore((s) => s.streaming);
  const retry = useCallback((m: ChatMessage) => {
    const msgs = useCopilotStore.getState().messages;
    const q = [...msgs.slice(0, msgs.findIndex((x) => x.id === m.id))].reverse().find((x) => x.role === "user");
    if (q) send(q.content, { replaceId: m.id });
  }, [send]);
  return (
    <>
      <ChatThread onSend={send} onRetry={retry} loading={loading} />
      <ChatInput onSend={send} onStop={stop} streaming={streaming} />
    </>
  );
}
