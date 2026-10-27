from app.services.copilot.agent import CopilotAgent, build_memory, context_note
from app.services.copilot.data import get_store
from app.services.llm import Message, ProviderUnavailableError, ToolCall
from app.services.llm.mock_provider import MockProvider


async def run(script, question="q", history=(), context=None, create_action=None, provider=None):
    p = provider or MockProvider(script)
    evs = [e async for e in CopilotAgent(p).run(list(history), question, context, "tester", create_action)]
    return p, evs


def kinds(evs):
    return [e["event"] for e in evs]


async def test_tool_then_answer_with_blocks():
    p, evs = await run([[ToolCall("c1", "get_neighbors", {"account_id": "ACC_9010", "direction": "in"})], "ACC_9010 got money from 15 accounts"])
    k = kinds(evs)
    assert k[:2] == ["tool_start", "tool_end"] and k[-2:] == ["blocks", "_final"] and "token" in k
    assert evs[0]["data"]["label"] == "Finding 1-hop neighbors of ACC_9010"
    b = next(e for e in evs if e["event"] == "blocks")["data"]
    assert "ACC_9010" in b["referenced_nodes"] and b["table"]["columns"]
    final = evs[-1]["data"]
    assert "15 accounts" in final["content"] and final["tool_calls"][0]["tool"] == "get_neighbors"
    tool_msg = next(m for m in p.calls[1] if m.role == "tool")
    assert tool_msg.content.startswith("<tool_result>")  # wrapped as data


async def test_parallel_calls_one_round():
    _, evs = await run([[ToolCall("a", "detect_patterns", {"account_id": "ACC_9030"}),
                         ToolCall("b", "get_account_details", {"account_id": "ACC_9001"})], "done"])
    assert kinds(evs)[:2] == ["tool_start", "tool_start"] and kinds(evs).count("tool_end") == 2


async def test_iteration_limit_stops_and_explains():
    loop = [[ToolCall(f"c{i}", "get_dashboard_stats", {})] for i in range(10)]
    p, evs = await run(loop + ["unused"][:0], provider=MockProvider(loop[:5] + ["Stopped early; ask me X."]))
    assert kinds(evs).count("tool_start") == 5
    assert "Stopped early" in evs[-1]["data"]["content"]
    assert any("limit reached" in m.content for m in p.calls[-1] if m.role == "system")  # final pass had the limit note
    assert len(p.calls) == 6


async def test_action_tool_is_proposed_not_executed():
    s = get_store()
    aid = next(a["id"] for a in s.alerts.values() if a["status"] == "open")
    made = []
    _, evs = await run([[ToolCall("x", "update_alert_status", {"alert_id": aid, "status": "confirmed_fraud"})], "Please confirm."],
                       create_action=lambda t, a: made.append((t, a)) or "act1")
    c = next(e for e in evs if e["event"] == "confirmation_required")["data"]
    assert c["action_id"] == "act1" and "Confirmed Fraud" in c["description"]
    assert s.alerts[aid]["status"] == "open" and made


async def test_provider_failure_becomes_error_event():
    class Down(MockProvider):
        async def _stream(self, m, t):
            raise ProviderUnavailableError("down")
            yield
    import app.services.llm.base as b
    b.RETRIES, old = 0, b.RETRIES
    try:
        _, evs = await run([], provider=Down([]))
    finally:
        b.RETRIES = old
    assert evs[-1]["event"] == "error" and evs[-1]["data"]["retryable"] is True and "Detection" in evs[-1]["data"]["message"]


async def test_bad_tool_input_returned_to_llm_not_crash():
    _, evs = await run([[ToolCall("c", "get_account_details", {"account_id": "nope"})], "ok"])
    assert "Invalid input" in next(e for e in evs if e["event"] == "tool_end")["data"]["summary"]


def test_memory_and_context():
    h = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(14)]
    m = build_memory(h)
    assert len(m) == 11 and m[0].role == "system" and "m0" in m[0].content and m[-1].content == "m13"
    n = context_note({"page": "account", "account_id": "ACC_1023", "selected_nodes": ["ACC_1", "evil; drop"]})
    assert "ACC_1023" in n and "ACC_1" in n and "evil" not in n
    assert context_note({"page": "x", "account_id": "ignore previous"}).count("ignore") == 0
