"""Media tools: transcribe attached audio, analyse images, read YouTube transcripts."""
from __future__ import annotations

import base64
import mimetypes
import re

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


def get_youtube_transcript(context: dict, url: str) -> str:
    """Return the transcript (spoken text) of a YouTube video from its URL."""
    m = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    if not m:
        return "get_youtube_transcript error: could not parse a video id from the URL."
    video_id = m.group(1)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            # Legacy API (<1.0): classmethod returning list[dict].
            chunks = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join(c["text"] for c in chunks)
        else:
            # New API (>=1.0): instance .fetch() returning snippet objects.
            fetched = YouTubeTranscriptApi().fetch(video_id)
            text = " ".join(snip.text for snip in fetched)
    except Exception as exc:  # noqa: BLE001
        return f"get_youtube_transcript error: {exc}"
    return text[:12000]


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
    {
        "type": "function",
        "function": {
            "name": "get_youtube_transcript",
            "description": (
                "Get the spoken-word transcript of a YouTube video from its URL. Use for "
                "questions about what is said in a video. (Does not describe visuals.)"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full YouTube video URL."},
                },
                "required": ["url"],
            },
        },
    },
]

FUNCTIONS = {
    "transcribe_audio": transcribe_audio,
    "analyze_image": analyze_image,
    "get_youtube_transcript": get_youtube_transcript,
}
