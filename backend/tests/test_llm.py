import json

import pytest

from app.core.config import settings
from app.services.llm import (
    Done, Message, ProviderUnavailableError, RateLimitError, TextDelta, ToolCall, ToolSpec, get_provider,
)
from app.services.llm import base
from app.services.llm.gemini_provider import to_gemini_contents, to_gemini_tools
from app.services.llm.groq_provider import to_groq_messages, to_groq_tools
from app.services.llm.mock_provider import MockProvider
from app.services.llm.ollama_provider import to_ollama_messages, to_ollama_tools

TOOL = ToolSpec("get_account_details", "Account profile", {
    "type": "object", "properties": {"account_id": {"type": "string"}}, "required": ["account_id"]})
HISTORY = [
    Message("system", "sys"), Message("user", "why risky ACC_1?"),
    Message("assistant", "", [ToolCall("c1", "get_account_details", {"account_id": "ACC_1"})]),
    Message("tool", '{"risk":91}', tool_call_id="c1", name="get_account_details"),
]


async def collect(p, **kw):
    return [e async for e in p.generate(HISTORY, [TOOL], **kw)]


async def test_mock_tool_then_text():
    p = MockProvider([[ToolCall("c1", "get_account_details", {"account_id": "ACC_1"})], "Risk is high"])
    first, second = await collect(p), await collect(p)
    assert isinstance(first[0], ToolCall) and first[0].args == {"account_id": "ACC_1"}
    assert "".join(e.text for e in second if isinstance(e, TextDelta)).strip() == "Risk is high"


async def test_non_streaming_coalesces():
    evs = await collect(MockProvider(["a b c"]), stream=False)
    assert [type(e) for e in evs] == [TextDelta, Done] and evs[0].text == "a b c "


def test_schema_conversion():
    g = to_groq_messages(HISTORY)
    assert to_groq_tools([TOOL])[0]["function"]["parameters"] == TOOL.parameters
    assert json.loads(g[2]["tool_calls"][0]["function"]["arguments"]) == {"account_id": "ACC_1"}
    assert g[3]["tool_call_id"] == "c1"
    assert to_ollama_tools([TOOL])[0]["function"]["name"] == "get_account_details"
    assert to_ollama_messages(HISTORY)[2]["tool_calls"][0]["function"]["arguments"] == {"account_id": "ACC_1"}
    system, contents = to_gemini_contents(HISTORY)
    assert system == "sys" and [c.role for c in contents] == ["user", "model", "user"]
    assert to_gemini_tools([TOOL])[0].function_declarations[0].name == "get_account_details"


class Flaky(MockProvider):
    def __init__(self, fails, exc):
        super().__init__(["ok"])
        self.fails, self.exc = fails, exc

    async def _stream(self, messages, tools):
        if self.fails:
            self.fails -= 1
            raise self.exc("boom")
        async for e in super()._stream(messages, tools):
            yield e


async def test_retry(monkeypatch):
    async def no_sleep(_): pass
    monkeypatch.setattr(base.asyncio, "sleep", no_sleep)
    assert any(isinstance(e, TextDelta) for e in await collect(Flaky(2, RateLimitError)))  # 2 retries ok
    with pytest.raises(ProviderUnavailableError):
        await collect(Flaky(3, ProviderUnavailableError))  # gives up on 3rd failure


@pytest.mark.skipif(not settings.groq_api_key, reason="no GROQ_API_KEY")
async def test_groq_live_tool_call():
    msgs = [Message("user", "Use the tool to look up account ACC_1023.")]
    evs = [e async for e in get_provider("groq").generate(msgs, [TOOL])]
    calls = [e for e in evs if isinstance(e, ToolCall)]
    assert calls and calls[0].name == "get_account_details" and "ACC_1023" in calls[0].args["account_id"]


async def test_retry_honours_retry_after(monkeypatch):
    waits = []

    async def rec(s): waits.append(s)
    monkeypatch.setattr(base.asyncio, "sleep", rec)
    p = Flaky(1, lambda m: RateLimitError(m, retry_after=12))
    await collect(p)
    assert waits == [12]
    waits.clear()
    await collect(Flaky(1, lambda m: RateLimitError(m, retry_after=999)))
    assert waits == [base.MAX_RETRY_WAIT]  # capped
