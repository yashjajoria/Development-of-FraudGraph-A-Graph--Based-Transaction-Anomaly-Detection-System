import type { RiskLevel } from "@/types/copilot";

export const RISK: Record<RiskLevel, { hex: string; text: string; bg: string; dot: string }> = {
  Low: { hex: "#10b981", text: "text-emerald-400", bg: "bg-emerald-500/10", dot: "bg-emerald-500" },
  Medium: { hex: "#f59e0b", text: "text-amber-400", bg: "bg-amber-500/10", dot: "bg-amber-500" },
  High: { hex: "#f97316", text: "text-orange-400", bg: "bg-orange-500/10", dot: "bg-orange-500" },
  Critical: { hex: "#f43f5e", text: "text-rose-400", bg: "bg-rose-500/10", dot: "bg-rose-500" },
};

const inrFmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
export const inr = (n: number) => inrFmt.format(n);
