"""ToolRegistry: name -> function + JSON schema + description + requires_confirmation.
Every call is schema-validated; results are always {"data", "referenced_nodes", "summary"}."""
from dataclasses import dataclass
from typing import Any, Callable

import jsonschema

from app.services.llm.base import ToolSpec

MAX_ROWS = 20


class ToolError(Exception):
    """Expected failure (not found, bad range). Returned to the LLM as a result, never raised past run()."""


class ConfirmationRequired(Exception):
    def __init__(self, tool: str, args: dict):
        super().__init__(f"{tool} requires user confirmation")
        self.tool, self.args = tool, args


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    fn: Callable[..., dict]
    requires_confirmation: bool = False


def obj(props: dict, required: tuple = ()) -> dict:
    return {"type": "object", "properties": props, "required": list(required), "additionalProperties": False}


def inr(x: float) -> str:
    """Indian digit grouping: 1234567 -> ₹12,34,567."""
    s = str(int(round(x)))
    head, tail, parts = s[:-3], s[-3:], []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    return "₹" + ",".join(([head] if head else []) + parts + [tail]) if len(s) > 3 else "₹" + s


def out(rows: list, nodes: list, summary: str) -> dict:
    """Cap rows to MAX_ROWS and say so in the summary, so the LLM never claims it saw everything."""
    extra = len(rows) - MAX_ROWS
    if extra > 0:
        summary += f" (showing {MAX_ROWS} of {len(rows)}; {extra} more not shown)"
    return {"data": rows[:MAX_ROWS], "referenced_nodes": list(dict.fromkeys(nodes))[:MAX_ROWS], "summary": summary}


def _fail(msg: str) -> dict:
    return {"data": None, "referenced_nodes": [], "summary": msg}


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, description: str, parameters: dict, requires_confirmation: bool = False):
        def deco(fn):
            self.tools[fn.__name__] = Tool(fn.__name__, description, parameters, fn, requires_confirmation)
            return fn
        return deco

    def specs(self) -> list[ToolSpec]:
        return [ToolSpec(t.name, t.description, t.parameters) for t in self.tools.values()]

    def run(self, name: str, args: dict[str, Any], confirmed: bool = False) -> dict:
        tool = self.tools.get(name)
        if not tool:
            return _fail(f"Unknown tool '{name}'")
        try:
            jsonschema.validate(args, tool.parameters)
        except jsonschema.ValidationError as e:
            return _fail(f"Invalid input: {e.message}")
        if tool.requires_confirmation and not confirmed:  # enforced here, so no caller can skip it
            raise ConfirmationRequired(name, args)
        try:
            return tool.fn(**args)
        except ToolError as e:
            return _fail(str(e))


registry = ToolRegistry()
