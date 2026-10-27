import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef } from "react";
import { BASE, authHeaders } from "@/services/api/client";
import { useAuth } from "@/store/authStore";
import { useCopilotStore } from "@/store/copilotStore";
import type { StreamEvent } from "@/types/copilot";

/** Incremental Server-Sent-Events parser: feed it text chunks, get complete events back. */
export function createSSEParser() {
  let buf = "";
  return (chunk: string): StreamEvent[] => {
    buf += chunk.replace(/\r\n/g, "\n");
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? ""; // last piece may be incomplete
    const out: StreamEvent[] = [];
    for (const p of parts) {
      let event = "message", data = "";
      for (const line of p.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!data) continue;
      try { out.push({ event, data: JSON.parse(data) } as StreamEvent); } catch { /* skip malformed frame */ }
    }
    return out;
  };
}

const uid = () => Math.random().toString(36).slice(2);
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function useCopilotStream() {
  const qc = useQueryClient();
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => () => abortRef.current?.abort(), []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    const st = useCopilotStore.getState();
    st.messages.filter((m) => m.streaming).forEach((m) => st.patchMessage(m.id, (x) => ({ ...x, streaming: false })));
    st.setStreaming(false);
  }, []);

  const send = useCallback(async (text: string, opts: { replaceId?: string } = {}) => {
    const st = useCopilotStore.getState();
    if (st.streaming || !text.trim()) return;
    if (opts.replaceId) st.removeMessage(opts.replaceId); // regenerate/retry: drop the old answer, keep the question
    else st.addMessage({ id: uid(), role: "user", content: text, tools: [], confirmations: [] });
    const aid = uid();
    let curId = aid;
    st.addMessage({ id: aid, role: "assistant", content: "", tools: [], confirmations: [], streaming: true });
    st.setStreaming(true);
    const ctl = new AbortController();
    abortRef.current = ctl;
    const patch = (fn: Parameters<typeof st.patchMessage>[1]) => useCopilotStore.getState().patchMessage(curId, fn);
    const fail = (message: string, retryable: boolean) => {
      patch((m) => ({ ...m, streaming: false, error: { message, retryable } }));
      if (retryable) useCopilotStore.getState().setLlmDown(true);
    };
    const handle = (e: StreamEvent) => {
      const s = useCopilotStore.getState();
      switch (e.event) {
        case "session": s.setSession(e.data.session_id); qc.invalidateQueries({ queryKey: ["sessions"] }); break;
        case "tool_start": patch((m) => ({ ...m, tools: [...m.tools, { call_id: e.data.call_id, tool: e.data.tool, label: e.data.label, status: "running" }] })); break;
        case "tool_end": patch((m) => ({ ...m, tools: m.tools.map((t) => (t.call_id === e.data.call_id ? { ...t, status: "done", summary: e.data.summary, duration_ms: e.data.duration_ms } : t)) })); break;
        case "token": patch((m) => ({ ...m, content: m.content + e.data.text })); break;
        case "blocks": patch((m) => ({ ...m, blocks: e.data })); break;
        case "confirmation_required": patch((m) => ({ ...m, confirmations: [...m.confirmations, { ...e.data, status: "pending" }] })); break;
        case "done": s.patchMessage(curId, (m) => ({ ...m, id: e.data.message_id, streaming: false })); curId = e.data.message_id; s.setLlmDown(false); qc.invalidateQueries({ queryKey: ["sessions"] }); break;
        case "error": fail(e.data.message, e.data.retryable); break;
      }
    };

    const attempt = async (n: number): Promise<void> => {
      let gotEvent = false;
      try {
        const cur = useCopilotStore.getState();
        const res = await fetch(`${BASE}/copilot/chat`, {
          method: "POST", signal: ctl.signal,
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({ message: text, session_id: cur.sessionId ?? undefined, context: cur.context ?? undefined }),
        });
        if (res.status === 401) { useAuth.getState().logout(); return fail("Session expired, please sign in again.", false); }
        if (res.status === 429) return fail("You're sending messages too fast. Please wait a minute.", true);
        if (!res.ok || !res.body) return fail(res.status === 422 ? "Message is too long or invalid." : "The request failed.", res.status >= 500);
        const reader = res.body.getReader(), dec = new TextDecoder(), parse = createSSEParser();
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          for (const ev of parse(dec.decode(value, { stream: true }))) { gotEvent = true; handle(ev); }
        }
      } catch (err) {
        if (ctl.signal.aborted) return; // user pressed Stop
        if (n === 0 && !gotEvent) { await sleep(800); return attempt(1); } // one reconnect if nothing arrived yet
        fail("Connection lost. Detection and dashboards still work.", true);
      }
    };
    await attempt(0);
    useCopilotStore.getState().patchMessage(curId, (m) => (m.streaming ? { ...m, streaming: false } : m));
    useCopilotStore.getState().setStreaming(false);
  }, [qc]);

  return { send, stop };
}
