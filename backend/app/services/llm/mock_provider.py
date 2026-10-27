from collections.abc import AsyncIterator

from app.services.llm.base import Done, LLMProvider, Message, TextDelta, ToolCall, ToolSpec


class MockProvider(LLMProvider):
    """Scripted turns: each generate() call consumes one step.
    A step is a str (streamed as words) or a list[ToolCall]."""

    def __init__(self, script: list[str | list[ToolCall]]):
        self.script = list(script)
        self.calls: list[list[Message]] = []  # recorded for test assertions

    async def _stream(self, messages: list[Message], tools: list[ToolSpec]) -> AsyncIterator:
        self.calls.append(messages)
        step = self.script.pop(0) if self.script else "(mock script exhausted)"
        if isinstance(step, str):
            for w in step.split(" "):
                yield TextDelta(w + " ")
            yield Done("stop")
        else:
            for c in step:
                yield c
            yield Done("tool_calls")
