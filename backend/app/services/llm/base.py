"""Provider-independent LLM types. The rest of the app only sees these."""
import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


class LLMError(Exception):
    pass


class RateLimitError(LLMError):
    def __init__(self, msg: str = "", retry_after: float | None = None):
        super().__init__(msg)
        self.retry_after = retry_after  # seconds the provider asked us to wait


class ProviderUnavailableError(LLMError):
    pass


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema object


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class Message:
    role: str  # system | user | assistant | tool
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)  # on assistant turns
    tool_call_id: str | None = None  # on tool turns
    name: str | None = None  # tool name on tool turns


@dataclass
class TextDelta:
    text: str


@dataclass
class Done:
    finish_reason: str = "stop"


LLMEvent = TextDelta | ToolCall | Done

RETRIES = 2
MAX_RETRY_WAIT = 30.0


class LLMProvider(ABC):
    @abstractmethod
    def _stream(self, messages: list[Message], tools: list[ToolSpec]) -> AsyncIterator[LLMEvent]:
        """Adapter hook: yield events, raise RateLimitError/ProviderUnavailableError."""

    async def generate(
        self, messages: list[Message], tools: list[ToolSpec] | None = None, stream: bool = True
    ) -> AsyncIterator[LLMEvent]:
        """Unified stream of TextDelta / ToolCall / Done. Retries (2x, exponential
        backoff) only before the first event, so callers never see duplicated text."""
        tools = tools or []
        text: list[str] = []
        for attempt in range(RETRIES + 1):
            started = False
            try:
                async for ev in self._stream(messages, tools):
                    started = True
                    if not stream and isinstance(ev, TextDelta):
                        text.append(ev.text)  # coalesce for non-streaming callers
                        continue
                    if not stream and isinstance(ev, Done) and text:
                        yield TextDelta("".join(text))
                    yield ev
                return
            except (RateLimitError, ProviderUnavailableError) as e:
                if started or attempt == RETRIES:
                    raise
                wait = 0.5 * 2**attempt
                if isinstance(e, RateLimitError) and e.retry_after:
                    wait = max(wait, min(e.retry_after, MAX_RETRY_WAIT))  # honour the hint, but never hang the UI
                await asyncio.sleep(wait)
