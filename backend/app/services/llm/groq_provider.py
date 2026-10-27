import json
from collections.abc import AsyncIterator

import groq

from app.services.llm.base import (
    Done, LLMProvider, Message, ProviderUnavailableError, RateLimitError, TextDelta, ToolCall, ToolSpec,
)


def to_groq_tools(tools: list[ToolSpec]) -> list[dict]:
    return [
        {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
        for t in tools
    ]


def to_groq_messages(messages: list[Message]) -> list[dict]:
    out = []
    for m in messages:
        if m.role == "tool":
            out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
        elif m.role == "assistant" and m.tool_calls:
            out.append({
                "role": "assistant", "content": m.content or None,
                "tool_calls": [
                    {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": json.dumps(c.args)}}
                    for c in m.tool_calls
                ],
            })
        else:
            out.append({"role": m.role, "content": m.content})
    return out


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, timeout: float = 30.0):
        self.model = model
        self.client = groq.AsyncGroq(api_key=api_key, timeout=timeout, max_retries=0)  # we own retries

    async def _stream(self, messages: list[Message], tools: list[ToolSpec]) -> AsyncIterator:
        kwargs = {"tools": to_groq_tools(tools), "tool_choice": "auto"} if tools else {}
        calls: dict[int, dict] = {}  # streamed tool-call deltas arrive in pieces, keyed by index
        reason = "stop"
        try:
            stream = await self.client.chat.completions.create(
                model=self.model, messages=to_groq_messages(messages), stream=True, **kwargs
            )
            async for chunk in stream:
                ch = chunk.choices[0]
                if ch.delta.content:
                    yield TextDelta(ch.delta.content)
                for tc in ch.delta.tool_calls or []:
                    c = calls.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                    c["id"] = tc.id or c["id"]
                    if tc.function:
                        c["name"] = tc.function.name or c["name"]
                        c["args"] += tc.function.arguments or ""
                reason = ch.finish_reason or reason
        except groq.RateLimitError as e:
            ra = e.response.headers.get("retry-after")
            raise RateLimitError(str(e), float(ra) if ra and ra.replace(".", "").isdigit() else None) from e
        except (groq.APIConnectionError, groq.APITimeoutError) as e:
            raise ProviderUnavailableError(str(e)) from e
        except groq.APIStatusError as e:
            if e.status_code >= 500:
                raise ProviderUnavailableError(str(e)) from e
            raise
        for i in sorted(calls):
            c = calls[i]
            yield ToolCall(c["id"] or f"call_{i}", c["name"], json.loads(c["args"] or "{}"))
        yield Done(reason)
