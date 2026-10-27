import { useMemo, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ChartBlock, TableBlock } from "@/types/copilot";
import { NodeChip } from "./NodeChip";

export function ResultTable({ t }: { t: TableBlock }) {
  const [sort, setSort] = useState<{ i: number; dir: 1 | -1 } | null>(null);
  const rows = useMemo(() => {
    if (!sort) return t.rows;
    return [...t.rows].sort((a, b) => {
      const x = a[sort.i], y = b[sort.i];
      return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))) * sort.dir;
    });
  }, [t, sort]);
  return (
    <div className="mt-2 max-h-56 overflow-auto rounded-xl border border-line scroll-thin">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-card"><tr>
          {t.columns.map((c, i) => (
            <th key={c} onClick={() => setSort({ i, dir: sort?.i === i && sort.dir === 1 ? -1 : 1 })} className="cursor-pointer whitespace-nowrap px-2 py-1 text-left font-medium text-muted hover:text-fg">
              {c.replace(/_/g, " ")}{sort?.i === i ? (sort.dir === 1 ? " ▲" : " ▼") : ""}
            </th>))}
        </tr></thead>
        <tbody>{rows.map((r, ri) => (
          <tr key={ri} className="border-t border-line">
            {r.map((v, ci) => <td key={ci} className="px-2 py-1 font-mono">{/^ACC_\d+$/.test(String(v)) ? <NodeChip id={String(v)} /> : String(v ?? "")}</td>)}
          </tr>))}
        </tbody>
      </table>
    </div>
  );
}

export function ResultChart({ c }: { c: ChartBlock }) {
  return (
    <div className="mt-2 h-36 rounded-xl border border-line p-2">
      <div className="mb-1 text-xs text-muted">{c.title}</div>
      <ResponsiveContainer width="100%" height="85%">
        <BarChart data={c.data}>
          <XAxis dataKey={c.x} tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} width={28} /><Tooltip />
          <Bar dataKey={c.y} fill="#6366F1" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
