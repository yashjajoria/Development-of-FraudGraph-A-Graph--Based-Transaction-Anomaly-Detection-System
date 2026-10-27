// Mirrors the backend SSE events and REST schemas (backend/app/api/v1/copilot.py, agent.py).
export type RiskLevel = "Low" | "Medium" | "High" | "Critical";

export interface PageContext {
  page: string;
  account_id?: string | null;
  selected_nodes?: string[];
}

export interface ToolStep {
  call_id: string;
  tool: string;
  label: string;
  status: "running" | "done";
  summary?: string;
  duration_ms?: number;
}

export interface TableBlock { columns: string[]; rows: (string | number | boolean | null)[][] }
export interface ChartBlock { type: "bar"; title: string; x: string; y: string; data: Record<string, string | number>[] }

export interface Confirmation {
  action_id: string;
  tool: string;
  args: Record<string, unknown>;
  description: string;
  status?: "pending" | "approved" | "rejected" | "unknown";
  result?: string;
}

export interface Blocks {
  referenced_nodes: string[];
  table?: TableBlock;
  chart?: ChartBlock;
  confirmations?: Confirmation[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  tools: ToolStep[];
  blocks?: Blocks;
  confirmations: Confirmation[];
  streaming?: boolean;
  error?: { message: string; retryable: boolean };
  feedback?: "up" | "down";
}

export type StreamEvent =
  | { event: "session"; data: { session_id: string } }
  | { event: "tool_start"; data: { call_id: string; tool: string; args: Record<string, unknown>; label: string } }
  | { event: "tool_end"; data: { call_id: string; tool: string; summary: string; duration_ms: number } }
  | { event: "token"; data: { text: string } }
  | { event: "blocks"; data: Blocks }
  | { event: "confirmation_required"; data: Confirmation }
  | { event: "done"; data: { message_id: string } }
  | { event: "error"; data: { message: string; retryable: boolean } };

export interface SessionSummary { id: string; title: string; created_at: string; updated_at: string }

export interface StoredMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  tool_calls: { tool: string; summary: string; duration_ms: number }[] | null;
  blocks: Blocks | null;
}

export interface AccountSummary { id: string; type: string; risk_score: number; risk_level: RiskLevel }
export interface AccountDetail extends AccountSummary {
  name: string; phone: string; card: string; device_id: string; community_id: string | null;
  features: Record<string, number>;
  alerts: string[];
  explanation: { contributions: { rule: string; name: string; points: number; reason: string }[] };
}
