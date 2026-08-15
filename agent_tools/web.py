"""Web tools: search the internet and read the content of a web page."""
from __future__ import annotations

import re
import requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def web_search(context: dict, query: str, max_results: int = 5) -> str:
    """Run a DuckDuckGo web search and return the top results as text."""
    try:
        # Package was renamed duckduckgo_search -> ddgs; support both.
        try:
            from ddgs import DDGS  # type: ignore
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore

        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=max_results))
    except Exception as exc:  # noqa: BLE001
        return f"web_search error: {exc}"

    if not hits:
        return "No results found."

    lines = []
    for i, h in enumerate(hits, 1):
        title = h.get("title", "")
        href = h.get("href") or h.get("url", "")
        body = h.get("body", "")
        lines.append(f"{i}. {title}\n   {href}\n   {body}")
    return "\n".join(lines)


def visit_webpage(context: dict, url: str, max_chars: int = 8000) -> str:
    """Download a web page and return its main text content as Markdown."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=25)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return f"visit_webpage error: {exc}"

    try:
        from markdownify import markdownify

        text = markdownify(resp.text)
    except Exception:  # noqa: BLE001
        from bs4 import BeautifulSoup

        text = BeautifulSoup(resp.text, "html.parser").get_text("\n")

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n...[truncated]"
    return text


SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web with DuckDuckGo. Returns a list of titles, URLs and snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."},
                    "max_results": {"type": "integer", "description": "How many results (default 5)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "visit_webpage",
            "description": "Fetch a URL and return its readable text content as Markdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The full URL to visit."},
                },
                "required": ["url"],
            },
        },
    },
]

FUNCTIONS = {"web_search": web_search, "visit_webpage": visit_webpage}
