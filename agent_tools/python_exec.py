"""A sandboxed-ish Python execution tool for calculations and data crunching."""
from __future__ import annotations

import contextlib
import io


def run_python(context: dict, code: str) -> str:
    """Execute Python code and return whatever is printed. Use for math and logic."""
    allowed = {
        "__builtins__": {
            k: getattr(__builtins__, k, None) if not isinstance(__builtins__, dict)
            else __builtins__.get(k)
            for k in (
                "print", "len", "range", "sum", "min", "max", "abs", "round",
                "sorted", "enumerate", "zip", "map", "filter", "list", "dict",
                "set", "tuple", "str", "int", "float", "bool", "all", "any",
                "reversed", "divmod", "pow",
            )
        }
    }
    for mod in ("math", "statistics", "re", "itertools", "collections", "datetime", "json"):
        try:
            allowed[mod] = __import__(mod)
        except Exception:  # noqa: BLE001
            pass

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(code, allowed)  # noqa: S102
    except Exception as exc:  # noqa: BLE001
        return f"run_python error: {exc}\n--- output so far ---\n{buf.getvalue()}"

    out = buf.getvalue().strip()
    return out or "[no output — remember to print() your result]"


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": (
                "Execute Python code for calculations, string/list processing or logic. "
                "You MUST print() the result. math, statistics, re, itertools, collections, "
                "datetime and json are available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to run."}
                },
                "required": ["code"],
            },
        },
    },
]

FUNCTIONS = {"run_python": run_python}
