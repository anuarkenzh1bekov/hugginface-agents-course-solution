"""Tool registry for the GAIA agent.

Every module exposes two objects:
  * SCHEMAS   -> list of OpenAI tool/function schemas
  * FUNCTIONS -> {name: callable(context, **kwargs)}

They are merged here so the agent can advertise the schemas to the model and
dispatch tool calls by name.
"""
from __future__ import annotations

from . import files, media, python_exec, web

_MODULES = (web, files, media, python_exec)

TOOL_SCHEMAS: list[dict] = []
TOOL_FUNCTIONS: dict = {}

for _m in _MODULES:
    TOOL_SCHEMAS.extend(_m.SCHEMAS)
    TOOL_FUNCTIONS.update(_m.FUNCTIONS)


def dispatch(name: str, context: dict, arguments: dict) -> str:
    """Run a tool by name, injecting the shared context."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"Unknown tool: {name}"
    try:
        return str(func(context, **arguments))
    except TypeError as exc:
        return f"Tool '{name}' called with bad arguments {arguments}: {exc}"
