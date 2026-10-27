import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { deleteSession, getSession, listSessions, renameSession } from "@/services/api/copilot";
import { useCopilotStore } from "@/store/copilotStore";

export function SessionSidebar() {
  const qc = useQueryClient();
  const { sessionId, newChat, loadMessages } = useCopilotStore();
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const { data = [] } = useQuery({ queryKey: ["sessions"], queryFn: listSessions });
  const del = useMutation({ mutationFn: deleteSession, onSuccess: (_, id) => { if (id === sessionId) newChat(); qc.invalidateQueries({ queryKey: ["sessions"] }); } });
  const ren = useMutation({ mutationFn: ({ id, t }: { id: string; t: string }) => renameSession(id, t), onSuccess: () => { setEditing(null); qc.invalidateQueries({ queryKey: ["sessions"] }); } });
  const open = async (id: string) => { const s = await getSession(id); loadMessages(id, s.messages); };

  const day = 86_400_000, now = Date.now();
  const filtered = data.filter((s) => s.title.toLowerCase().includes(q.toLowerCase()));
  const groups = [["Today", (a: number) => a < day], ["This week", (a: number) => a >= day && a < 7 * day], ["Older", (a: number) => a >= 7 * day]] as const;
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-line">
      <div className="space-y-2 p-3">
        <button onClick={newChat} className="flex w-full items-center justify-center gap-1 rounded-xl bg-gradient-to-r from-accent to-accent-2 py-1.5 text-sm text-white"><Plus size={14} /> New chat</button>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search chats" className="w-full rounded-lg border border-line bg-bg px-2 py-1 text-xs" />
      </div>
      <div className="flex-1 overflow-y-auto px-2 scroll-thin">
        {groups.map(([label, test]) => {
          const items = filtered.filter((s) => test(now - new Date(s.updated_at).getTime()));
          return items.length === 0 ? null : (
            <div key={label} className="mb-3">
              <div className="px-2 pb-1 text-[10px] uppercase tracking-wide text-muted">{label}</div>
              {items.map((s) => (
                <div key={s.id} className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs ${s.id === sessionId ? "bg-accent/10" : "hover:bg-card"}`}>
                  {editing === s.id
                    ? <input autoFocus defaultValue={s.title} onBlur={() => setEditing(null)} onKeyDown={(e) => { if (e.key === "Enter") ren.mutate({ id: s.id, t: e.currentTarget.value }); if (e.key === "Escape") setEditing(null); }} className="w-full rounded border border-line bg-bg px-1" />
                    : <button onClick={() => open(s.id)} className="flex-1 truncate text-left">{s.title}</button>}
                  <button title="Rename" onClick={() => setEditing(s.id)} className="hidden text-muted group-hover:block"><Pencil size={12} /></button>
                  <button title="Delete" onClick={() => del.mutate(s.id)} className="hidden text-muted hover:text-rose-400 group-hover:block"><Trash2 size={12} /></button>
                </div>))}
            </div>);
        })}
      </div>
    </aside>
  );
}
