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
    # Package was renamed duckduckgo_search -> ddgs; support both.
    try:
        try:
            from ddgs import DDGS  # type: ignore
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return f"web_search unavailable: {exc}"

    hits = []
    for attempt in range(3):
        try:
            with DDGS() as ddgs:
                hits = list(ddgs.text(query, max_results=max_results))
            if hits:
                break
        except Exception:  # noqa: BLE001 - shared-IP rate limits, retry
            pass

    if not hits:
        return (
            "No web results (search may be rate-limited from this host). "
            "Try wikipedia_search / read_wikipedia for factual lookups instead."
        )

    lines = []
    for i, h in enumerate(hits, 1):
        title = h.get("title", "")
        href = h.get("href") or h.get("url", "")
        body = h.get("body", "")
        lines.append(f"{i}. {title}\n   {href}\n   {body}")
    return "\n".join(lines)


# Wikimedia's robot policy requires a descriptive User-Agent (browser UAs get 403).
_WIKI_HEADERS = {
    "User-Agent": "gaia-agents-course/1.0 (HF Agents course student project)",
    "Accept": "application/json",
}


def _wiki_api(params: dict) -> dict:
    params = {"format": "json", **params}
    resp = requests.get(
        "https://en.wikipedia.org/w/api.php", params=params, headers=_WIKI_HEADERS, timeout=25
    )
    resp.raise_for_status()
    return resp.json()


def wikipedia_search(context: dict, query: str, max_results: int = 5) -> str:
    """Search English Wikipedia and return matching page titles with snippets."""
    try:
        data = _wiki_api(
            {"action": "query", "list": "search", "srsearch": query, "srlimit": max_results}
        )
    except Exception as exc:  # noqa: BLE001
        return f"wikipedia_search error: {exc}"

    results = data.get("query", {}).get("search", [])
    if not results:
        return "No Wikipedia pages found."
    lines = []
    for i, r in enumerate(results, 1):
        snippet = re.sub(r"<[^>]+>", "", r.get("snippet", ""))
        lines.append(f"{i}. {r.get('title')} — {snippet}")
    return "\n".join(lines)


def read_wikipedia(context: dict, title: str, max_chars: int = 8000) -> str:
    """Return the plain-text content of an English Wikipedia article by title."""
    try:
        data = _wiki_api(
            {
                "action": "query",
                "prop": "extracts",
                "explaintext": 1,
                "redirects": 1,
                "titles": title,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return f"read_wikipedia error: {exc}"

    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    text = page.get("extract")
    if not text:
        return f"No Wikipedia article titled '{title}'. Try wikipedia_search first."
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n...[truncated]"
    return f"[Wikipedia: {page.get('title', title)}]\n{text}"


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
    {
        "type": "function",
        "function": {
            "name": "wikipedia_search",
            "description": (
                "Search English Wikipedia for page titles. Prefer this over web_search "
                "for encyclopedic facts (people, places, events, works, species) — it is "
                "reliable and not rate-limited."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for."},
                    "max_results": {"type": "integer", "description": "How many titles (default 5)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_wikipedia",
            "description": "Read the full plain-text of an English Wikipedia article by its exact title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Exact article title."},
                },
                "required": ["title"],
            },
        },
    },
]

FUNCTIONS = {
    "web_search": web_search,
    "visit_webpage": visit_webpage,
    "wikipedia_search": wikipedia_search,
    "read_wikipedia": read_wikipedia,
}
