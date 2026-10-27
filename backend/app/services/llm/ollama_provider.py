import json
from collections.abc import AsyncIterator

import httpx

from app.services.llm.base import (
    Done, LLMProvider, Message, ProviderUnavailableError, RateLimitError, TextDelta, ToolCall, ToolSpec,
)


def to_ollama_tools(tools: list[ToolSpec]) -> list[dict]:
    return [
        {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
        for t in tools
    ]


def to_ollama_messages(messages: list[Message]) -> list[dict]:
    out = []
    for m in messages:
        d = {"role": m.role, "content": m.content}
        if m.role == "tool":
            d["tool_name"] = m.name
        if m.tool_calls:
            d["tool_calls"] = [{"function": {"name": c.name, "arguments": c.args}} for c in m.tool_calls]
        out.append(d)
    return out


class OllamaProvider(LLMProvider):
    def __init__(self, url: str, model: str, timeout: float = 30.0):
        self.model = model
        self.client = httpx.AsyncClient(base_url=url, timeout=timeout)

    async def _stream(self, messages: list[Message], tools: list[ToolSpec]) -> AsyncIterator:
        body = {"model": self.model, "messages": to_ollama_messages(messages), "stream": True}
        if tools:
            body["tools"] = to_ollama_tools(tools)
        n = 0
        try:
            async with self.client.stream("POST", "/api/chat", json=body) as r:
                if r.status_code == 429:
                    raise RateLimitError("ollama busy")
                if r.status_code >= 500:
                    raise ProviderUnavailableError(f"ollama {r.status_code}")
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    msg = json.loads(line).get("message", {})
                    if msg.get("content"):
                        yield TextDelta(msg["content"])
                    for tc in msg.get("tool_calls") or []:
                        n += 1
                        yield ToolCall(f"call_{n}", tc["function"]["name"], tc["function"].get("arguments") or {})
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise ProviderUnavailableError(str(e)) from e
        yield Done()
