import { useQuery } from "@tanstack/react-query";
import { getSuggestions } from "@/services/api/copilot";
import type { PageContext } from "@/types/copilot";

export function SuggestionChips({ ctx, onPick }: { ctx: PageContext | null; onPick: (q: string) => void }) {
  const { data } = useQuery({ queryKey: ["suggest", ctx?.page, ctx?.account_id], queryFn: () => getSuggestions(ctx?.page ?? "default", ctx?.account_id) });
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {(data?.suggestions ?? []).map((q) => (
        <button key={q} onClick={() => onPick(q)} className="rounded-full border border-line bg-card px-3.5 py-1.5 text-xs hover:border-accent hover:text-accent">{q}</button>
      ))}
    </div>
  );
}
