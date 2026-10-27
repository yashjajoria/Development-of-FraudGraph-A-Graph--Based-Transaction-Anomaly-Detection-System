import { useAuth } from "@/store/authStore";

export const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export const authHeaders = (): Record<string, string> => {
  const t = useAuth.getState().token;
  return t ? { Authorization: `Bearer ${t}` } : {};
};

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init.headers ?? {}) },
  });
  if (res.status === 401 && !path.startsWith("/auth/login")) useAuth.getState().logout();
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = typeof j.detail === "string" ? j.detail : msg; } catch { /* no body */ }
    throw new ApiError(res.status, msg);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}
