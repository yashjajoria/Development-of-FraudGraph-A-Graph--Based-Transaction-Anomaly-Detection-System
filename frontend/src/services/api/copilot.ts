import type { AccountDetail, AccountSummary, SessionSummary, StoredMessage } from "@/types/copilot";
import { api } from "./client";

export const login = (username: string, password: string) =>
  api<{ access_token: string; role: string }>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });

export const listSessions = () => api<SessionSummary[]>("/copilot/sessions");
export const getSession = (id: string) => api<{ id: string; title: string; messages: StoredMessage[] }>(`/copilot/sessions/${id}`);
export const deleteSession = (id: string) => api<void>(`/copilot/sessions/${id}`, { method: "DELETE" });
export const renameSession = (id: string, title: string) =>
  api<{ id: string; title: string }>(`/copilot/sessions/${id}`, { method: "PATCH", body: JSON.stringify({ title }) });

export const confirmAction = (actionId: string, approve: boolean) =>
  api<{ status: string; result: { summary: string } | null }>(`/copilot/confirm/${actionId}`, { method: "POST", body: JSON.stringify({ approve }) });

export const sendFeedback = (message_id: string, rating: "up" | "down", comment?: string) =>
  api<{ ok: boolean }>("/copilot/feedback", { method: "POST", body: JSON.stringify({ message_id, rating, comment }) });

export const getSuggestions = (page: string, accountId?: string | null) =>
  api<{ suggestions: string[] }>(`/copilot/suggestions?page=${encodeURIComponent(page)}${accountId ? `&account_id=${accountId}` : ""}`);

export const getAccount = (id: string) => api<AccountDetail>(`/accounts/${id}`);
export const searchAccounts = (q: string) => api<AccountSummary[]>(`/accounts/search?q=${encodeURIComponent(q)}`);
export const getDashboard = () =>
  api<{ stats: Record<string, any>; top_risky: { account_id: string; type: string; risk_score: number; risk_level: AccountSummary["risk_level"]; rules: string[] }[] }>("/dashboard");

export interface GraphData {
  nodes: { id: string; type: string; risk_score: number; risk_level: AccountSummary["risk_level"]; community_id: string | null }[];
  edges: { source: string; target: string; amount: number; count: number }[];
}
export const getGraph = (ids?: string[]) => api<GraphData>(`/graph${ids ? `?ids=${ids.join(",")}` : ""}`);

export interface NewAccount { type: "user" | "merchant"; name: string; phone?: string; card?: string; device_id?: string }
export const createAccount = (b: NewAccount) => api<AccountDetail>("/accounts", { method: "POST", body: JSON.stringify(b) });

export const importCsv = (kind: "accounts" | "transactions", csv: string) =>
  api<{ imported: number; account_ids?: string[]; newly_flagged?: string[]; total_alerts?: number }>(`/import/${kind}`, { method: "POST", body: JSON.stringify({ csv }) });
