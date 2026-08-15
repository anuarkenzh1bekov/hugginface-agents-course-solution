"""Media tools: transcribe attached audio and analyse attached images via OpenAI."""
from __future__ import annotations

import base64
import mimetypes

from .files import save_task_file


def transcribe_audio(context: dict) -> str:
    """Transcribe the audio file attached to the current task using OpenAI Whisper."""
    client = context["client"]
    try:
        path = save_task_file(context)
        with open(path, "rb") as fh:
            resp = client.audio.transcriptions.create(
                model=context.get("stt_model", "whisper-1"),
                file=fh,
            )
        return resp.text
    except Exception as exc:  # noqa: BLE001
        return f"transcribe_audio error: {exc}"


def analyze_image(context: dict, question: str) -> str:
    """Answer a question about the image file attached to the current task (vision)."""
    client = context["client"]
    try:
        path = save_task_file(context)
        mime = mimetypes.guess_type(path)[0] or "image/png"
        with open(path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        resp = client.chat.completions.create(
            model=context.get("vision_model", context.get("model", "gpt-4o")),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                    ],
                }
            ],
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        return f"analyze_image error: {exc}"


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "transcribe_audio",
            "description": "Transcribe the audio file (mp3/wav/...) attached to this task to text.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_image",
            "description": "Ask a question about the image attached to this task and get an answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "What to look for / ask about the image.",
                    }
                },
                "required": ["question"],
            },
        },
    },
]

FUNCTIONS = {"transcribe_audio": transcribe_audio, "analyze_image": analyze_image}
