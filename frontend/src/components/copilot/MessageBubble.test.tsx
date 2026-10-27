import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import type { ChatMessage } from "@/types/copilot";
import { MessageBubble, linkIds } from "./MessageBubble";

vi.mock("@/services/api/copilot", () => ({ getAccount: vi.fn().mockResolvedValue({ id: "ACC_9001", type: "user", risk_score: 70, risk_level: "High" }), sendFeedback: vi.fn() }));

const base: ChatMessage = { id: "1", role: "assistant", content: "", tools: [], confirmations: [] };
const wrap = (m: ChatMessage) => render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><MessageBubble m={m} onRetry={() => {}} /></MemoryRouter></QueryClientProvider>);

it("linkIds wraps account ids", () => expect(linkIds("see ACC_9001, ACC_2")).toBe("see [ACC_9001](node:ACC_9001), [ACC_2](node:ACC_2)"));

it("renders account ids as chips and shows the verify note", () => {
  wrap({ ...base, content: "**ACC_9001** is risky" });
  expect(screen.getByRole("button", { name: /ACC_9001/ })).toBeInTheDocument();
  expect(screen.getByText(/verify before acting/i)).toBeInTheDocument();
});

it("shows Show-on-graph, tool trace, and confirmation card", () => {
  wrap({ ...base, content: "ok", blocks: { referenced_nodes: ["ACC_9001", "ACC_9002"] },
    tools: [{ call_id: "c", tool: "find_cycles", label: "Searching", status: "done", summary: "1 cycle", duration_ms: 5 }],
    confirmations: [{ action_id: "a", tool: "update_alert_status", args: {}, description: "Mark alert ALR_001 as Closed", status: "pending" }] });
  expect(screen.getByText(/Show on graph \(2\)/)).toBeInTheDocument();
  expect(screen.getByText(/Used 1 tool/)).toBeInTheDocument();
  expect(screen.getByText("Mark alert ALR_001 as Closed")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Confirm" })).toBeInTheDocument();
});

it("shows a Retry button on retryable errors", () => {
  wrap({ ...base, error: { message: "AI busy", retryable: true } });
  expect(screen.getByText("Retry")).toBeInTheDocument();
});

it("renders user bubbles", () => {
  wrap({ ...base, role: "user", content: "hello" });
  expect(screen.getByText("hello")).toBeInTheDocument();
});
