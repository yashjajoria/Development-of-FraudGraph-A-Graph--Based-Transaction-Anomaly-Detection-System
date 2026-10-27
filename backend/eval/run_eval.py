"""Run the 20-question eval against the configured LLM_PROVIDER.
Reports tool-selection accuracy, answer grounding (IDs and ₹ amounts must appear in tool results) and latency.
Usage (from backend/): .venv/bin/python eval/run_eval.py [--delay 2]"""
import asyncio
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.copilot.agent import CopilotAgent  # noqa: E402
from app.services.copilot.tools import registry  # noqa: E402
from app.services.llm import get_provider  # noqa: E402

ID_RE = re.compile(r"\b(?:ACC|ALR|COM|TXN)_\d+\b")
AMT_RE = re.compile(r"₹\s*([\d,]+(?:\.\d+)?)\s*(lakh|crore|k)?", re.I)
MULT = {"lakh": 1e5, "crore": 1e7, "k": 1e3, None: 1}


def numbers(blob: str) -> list[float]:
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", blob.replace(",", ""))]


def grounding(answer: str, question: str, results_blob: str) -> list[str]:
    """Return ungrounded items: IDs/amounts in the answer that no tool result (or the question) contains."""
    bad = [i for i in set(ID_RE.findall(answer)) if i not in results_blob and i not in question]
    nums = numbers(results_blob)
    for m in AMT_RE.finditer(answer):
        v = float(m.group(1).replace(",", "")) * MULT[(m.group(2) or "").lower() or None]
        if v and not any(abs(n - v) <= max(1.0, 0.01 * v) for n in nums):
            bad.append(m.group(0).strip())  # ponytail: derived sums (e.g. totals) may be flagged; review manually
    return bad


async def one(item: dict, provider) -> dict:
    called, blobs = [], []
    real = registry.run

    def spy(name, args, confirmed=False):
        called.append(name)
        try:
            r = real(name, args, confirmed)
            blobs.append(json.dumps(r, default=str))
            return r
        except Exception:
            raise
    registry.run = spy
    t0, answer, err, pending = time.perf_counter(), "", None, False
    try:
        async for ev in CopilotAgent(provider).run([], item["q"], None, "eval", lambda t, a: "eval-action"):
            if ev["event"] == "_final":
                answer = ev["data"]["content"]
            elif ev["event"] == "error":
                err = ev["data"]["message"]
            elif ev["event"] == "confirmation_required":
                pending = True
    finally:
        registry.run = real
    latency = time.perf_counter() - t0
    ok_tools = any(set(alt) <= set(called) and (alt or not called) for alt in item["expected"])
    ok_tools = ok_tools and not (set(item.get("forbidden", [])) & set(called))
    if item.get("pending_action"):
        ok_tools = ok_tools and pending
    low = answer.lower()
    missing = [f for f in item["facts"] if f.lower() not in low]
    bad = grounding(answer, item["q"], "\n".join(blobs))
    return {"q": item["q"], "called": called, "tool_ok": ok_tools, "facts_missing": missing, "ungrounded": bad,
            "latency_s": round(latency, 2), "error": err, "answer": answer[:300]}


async def main(delay: float):
    provider = get_provider()
    items = json.loads((Path(__file__).parent / "questions.json").read_text())
    rows = []
    for i, it in enumerate(items, 1):
        r = await one(it, provider)
        rows.append(r)
        flag = "OK " if r["tool_ok"] and not r["ungrounded"] and not r["error"] else "BAD"
        print(f"{i:2}. {flag} {r['latency_s']:5.1f}s tools={r['called']} missing={r['facts_missing']} "
              f"ungrounded={r['ungrounded']} err={r['error']} | {r['q']}", flush=True)
        await asyncio.sleep(delay)
    n = len(rows)
    ans = [r for r in rows if r["answer"]]
    summary = {
        "provider": get_provider().__class__.__name__, "questions": n,
        "tool_selection_accuracy": round(sum(r["tool_ok"] for r in rows) / n, 3),
        "grounded_answers": round(sum(not r["ungrounded"] for r in ans) / max(1, len(ans)), 3),
        "key_facts_present": round(sum(not r["facts_missing"] for r in rows) / n, 3),
        "errors": sum(bool(r["error"]) for r in rows),
        "avg_latency_s": round(sum(r["latency_s"] for r in rows) / n, 2),
    }
    print("\nSUMMARY", json.dumps(summary, indent=2))
    (Path(__file__).parent / "results.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))


if __name__ == "__main__":
    d = float(sys.argv[sys.argv.index("--delay") + 1]) if "--delay" in sys.argv else 1.0
    asyncio.run(main(d))
