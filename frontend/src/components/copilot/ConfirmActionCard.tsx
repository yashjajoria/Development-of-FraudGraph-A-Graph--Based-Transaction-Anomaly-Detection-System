import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { confirmAction } from "@/services/api/copilot";
import { useAuth } from "@/store/authStore";
import { useCopilotStore } from "@/store/copilotStore";
import type { Confirmation } from "@/types/copilot";

export function ConfirmActionCard({ c }: { c: Confirmation }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const patch = useCopilotStore((s) => s.patchConfirmation);
  const act = async (approve: boolean) => {
    setBusy(true); setErr("");
    try {
      const r = await confirmAction(c.action_id, approve);
      patch(c.action_id, { status: r.status as Confirmation["status"], result: r.result?.summary });
    } catch (e) { setErr(e instanceof Error ? e.message : "Failed"); } finally { setBusy(false); }
  };
  const canAct = useAuth((s) => s.role) !== "viewer";
  const pending = c.status === "pending";
  return (
    <div className="mt-2 rounded-2xl border border-accent/40 bg-accent/5 p-3 text-sm">
      <div className="flex items-center gap-2 font-medium"><ShieldCheck size={16} className="text-accent" /> Action needs your confirmation</div>
      <p className="mt-1">{c.description}</p>
      {pending && !canAct ? (
        <p className="mt-2 text-xs text-amber-400">Your role (viewer) is read-only and cannot confirm actions.</p>
      ) : pending ? (
        <div className="mt-2 flex gap-2">
          <button disabled={busy} onClick={() => act(true)} className="rounded-lg bg-gradient-to-r from-accent to-accent-2 px-3 py-1 text-xs font-medium text-white disabled:opacity-50">Confirm</button>
          <button disabled={busy} onClick={() => act(false)} className="rounded-lg border border-line px-3 py-1 text-xs disabled:opacity-50">Cancel</button>
        </div>
      ) : (
        <p className="mt-2 text-xs text-muted">{c.status === "approved" ? `✓ Done. ${c.result ?? ""}` : c.status === "rejected" ? "Cancelled. Nothing was changed." : "Status unknown."}</p>
      )}
      {err && <p className="mt-1 text-xs text-rose-400">{err}</p>}
    </div>
  );
}
