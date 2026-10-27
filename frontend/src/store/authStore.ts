import { create } from "zustand";

interface AuthState {
  token: string | null;
  username: string | null;
  role: string | null;
  login: (token: string, username: string, role: string) => void;
  logout: () => void;
}

const read = (k: string) => {
  try { return localStorage.getItem(k); } catch { return null; }
};
const write = (k: string, v: string | null) => {
  try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* storage blocked */ }
};

export const useAuth = create<AuthState>((set) => ({
  token: read("fg_token"), username: read("fg_user"), role: read("fg_role"),
  login: (token, username, role) => { write("fg_token", token); write("fg_user", username); write("fg_role", role); set({ token, username, role }); },
  logout: () => { ["fg_token", "fg_user", "fg_role"].forEach((k) => write(k, null)); set({ token: null, username: null, role: null }); },
}));
