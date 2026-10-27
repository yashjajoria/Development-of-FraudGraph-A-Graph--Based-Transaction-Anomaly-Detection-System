from collections.abc import AsyncIterator

from google import genai
from google.genai import errors, types

from app.services.llm.base import (
    Done, LLMProvider, Message, ProviderUnavailableError, RateLimitError, TextDelta, ToolCall, ToolSpec,
)


def to_gemini_tools(tools: list[ToolSpec]) -> list[types.Tool]:
    return [types.Tool(function_declarations=[
        types.FunctionDeclaration(name=t.name, description=t.description, parameters_json_schema=t.parameters)
        for t in tools
    ])] if tools else []


def to_gemini_contents(messages: list[Message]) -> tuple[str | None, list[types.Content]]:
    system, contents = None, []
    for m in messages:
        if m.role == "system":
            system = m.content
        elif m.role == "tool":
            part = types.Part.from_function_response(name=m.name or "", response={"result": m.content})
            contents.append(types.Content(role="user", parts=[part]))
        elif m.role == "assistant":
            parts = [types.Part.from_text(text=m.content)] if m.content else []
            parts += [types.Part.from_function_call(name=c.name, args=c.args) for c in m.tool_calls]
            contents.append(types.Content(role="model", parts=parts))
        else:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=m.content)]))
    return system, contents


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, timeout: float = 30.0):
        self.model = model
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout * 1000)))

    async def _stream(self, messages: list[Message], tools: list[ToolSpec]) -> AsyncIterator:
        system, contents = to_gemini_contents(messages)
        cfg = types.GenerateContentConfig(
            system_instruction=system, tools=to_gemini_tools(tools),
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        n = 0
        try:
            async for chunk in await self.client.aio.models.generate_content_stream(
                model=self.model, contents=contents, config=cfg
            ):
                for cand in chunk.candidates or []:
                    for p in (cand.content.parts if cand.content else None) or []:
                        if p.text:
                            yield TextDelta(p.text)
                        elif p.function_call:
                            n += 1
                            fc = p.function_call
                            yield ToolCall(fc.id or f"call_{n}", fc.name, dict(fc.args or {}))
        except errors.APIError as e:
            if e.code == 429:
                raise RateLimitError(str(e)) from e
            if e.code >= 500:
                raise ProviderUnavailableError(str(e)) from e
            raise
        except TimeoutError as e:
            raise ProviderUnavailableError(str(e)) from e
        yield Done()
