"""File tools: download the file attached to a GAIA task and read its content."""
from __future__ import annotations

import io
import os
import tempfile

import requests

_HEADERS = {"User-Agent": "gaia-agent/1.0"}


def _download(context: dict) -> tuple[bytes, str]:
    """Download the file attached to the current task. Returns (bytes, suggested_name)."""
    task_id = context.get("task_id")
    api_url = context.get("api_url", "").rstrip("/")
    if not task_id:
        raise ValueError("No task_id in context; this task has no attached file.")
    url = f"{api_url}/files/{task_id}"
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    name = context.get("file_name") or task_id
    return resp.content, name


def read_file(context: dict, max_chars: int = 8000) -> str:
    """Read the file attached to the current task (text/CSV/Excel/JSON/code)."""
    try:
        data, name = _download(context)
    except Exception as exc:  # noqa: BLE001
        return f"read_file error: {exc}"

    ext = os.path.splitext(name)[1].lower()

    try:
        if ext in {".xlsx", ".xls"}:
            import pandas as pd

            frames = pd.read_excel(io.BytesIO(data), sheet_name=None)
            out = []
            for sheet, df in frames.items():
                out.append(f"# Sheet: {sheet}\n{df.to_string(index=False)}")
            text = "\n\n".join(out)
        elif ext == ".csv":
            import pandas as pd

            df = pd.read_csv(io.BytesIO(data))
            text = df.to_string(index=False)
        else:
            text = data.decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return f"read_file parse error ({ext}): {exc}"

    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n...[truncated]"
    return f"[file: {name}]\n{text}"


def save_task_file(context: dict) -> str:
    """Download the attached file to a temp path (for audio/image tools). Returns the path."""
    data, name = _download(context)
    path = os.path.join(tempfile.gettempdir(), f"gaia_{context.get('task_id')}_{name}")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the file attached to this task. Handles plain text, code, JSON, "
                "CSV and Excel spreadsheets. Use this whenever the question mentions an "
                "attached/provided file that is not audio or an image."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

FUNCTIONS = {"read_file": read_file}
