"""Lightweight XHS (Xiaohongshu) public page scraper.

Fetches real note data from XHS explore page SSR (server-side rendered state).
The explore page embeds ~20 trending notes with titles and engagement data
in window.__INITIAL_STATE__ without requiring authentication.

Single request per call. No individual note page fetching needed.
"""

from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("attention.scraper.xhs")

_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]

_TIMEOUT = 15

# Cache: avoid re-fetching explore page within same pipeline run
_explore_cache: list["XhsNote"] | None = None


@dataclass
class XhsNote:
    """Parsed XHS note data."""
    note_id: str = ""
    title: str = ""
    content: str = ""
    liked_count: int = 0
    collected_count: int = 0
    comment_count: int = 0
    url: str = ""
    author: str = ""
    tags: list[str] = field(default_factory=list)
    note_type: str = ""

    @property
    def engagement_score(self) -> int:
        return self.liked_count + self.collected_count * 2 + self.comment_count * 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "note_id": self.note_id,
            "title": self.title,
            "content": self.content[:300],
            "liked_count": self.liked_count,
            "collected_count": self.collected_count,
            "comment_count": self.comment_count,
            "engagement_score": self.engagement_score,
            "url": self.url,
            "author": self.author,
            "tags": self.tags,
        }


def _parse_count(text: str) -> int:
    """Parse engagement count like '1.2万' -> 12000, '10万+' -> 100000, '3456' -> 3456."""
    text = str(text or "").strip().lower().rstrip("+")
    if not text or text == "-":
        return 0
    m = re.match(r"([\d.]+)\s*[wW万]", text)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.match(r"([\d.]+)\s*[kK千]", text)
    if m:
        return int(float(m.group(1)) * 1000)
    m = re.match(r"(\d+)", text.replace(",", ""))
    if m:
        return int(m.group(1))
    return 0


def _fetch_explore_notes() -> list[XhsNote]:
    """Fetch trending notes from XHS explore page SSR data."""
    headers = {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = client.get("https://www.xiaohongshu.com/explore", headers=headers)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("XHS explore fetch failed: %s", str(exc)[:120])
        return []

    # Extract SSR state
    state_match = re.search(
        r"window\.__INITIAL_STATE__\s*=\s*({.+?})\s*(?:</script>|;\s*\n)",
        resp.text,
        re.DOTALL,
    )
    if not state_match:
        logger.warning("XHS explore: no __INITIAL_STATE__ found")
        return []

    try:
        raw = state_match.group(1).replace("undefined", "null")
        state = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("XHS explore: JSON parse failed: %s", exc)
        return []

    feeds = state.get("feed", {}).get("feeds", [])
    if not feeds:
        logger.warning("XHS explore: empty feeds")
        return []

    notes: list[XhsNote] = []
    for feed in feeds:
        note_card = feed.get("noteCard", {})
        if not note_card:
            continue

        note_id = feed.get("id", "")
        title = note_card.get("displayTitle", "")
        interact = note_card.get("interactInfo", {})
        user = note_card.get("user", {})

        note = XhsNote(
            note_id=note_id,
            title=title,
            content=title,  # explore page only has title, use as content too
            liked_count=_parse_count(str(interact.get("likedCount", "0"))),
            url=f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else "",
            author=user.get("nickname", ""),
            note_type=note_card.get("type", ""),
        )

        if note.title:
            notes.append(note)

    logger.info("XHS explore: fetched %d trending notes", len(notes))
    return notes


def _keyword_relevance(note: XhsNote, keywords: list[str]) -> float:
    """Score how relevant a note is to the given keywords (0.0 - 1.0)."""
    if not keywords:
        return 0.5  # neutral if no keywords
    text = (note.title + " " + note.content).lower()
    hits = sum(1 for kw in keywords if kw.lower() in text)
    return min(hits / max(len(keywords), 1), 1.0)


def search_xhs_notes(
    query: str,
    max_notes: int = 5,
    _request_count: list[int] | None = None,
) -> list[XhsNote]:
    """Get XHS notes relevant to a query.

    Fetches trending notes from the explore page (cached per pipeline run)
    and filters by keyword relevance to the query.

    Args:
        query: Search query keywords (e.g., "美甲教程")
        max_notes: Maximum notes to return
        _request_count: Mutable counter (for API compatibility, only 1 request used)

    Returns:
        List of XhsNote objects sorted by engagement, filtered by relevance
    """
    global _explore_cache

    if _request_count is None:
        _request_count = [0]

    # Use cache if available (avoid re-fetching within same run)
    if _explore_cache is None:
        _request_count[0] += 1
        _explore_cache = _fetch_explore_notes()

    if not _explore_cache:
        return []

    # Split query into keywords for filtering
    keywords = [k.strip() for k in query.split() if k.strip()]

    # Score and filter notes by relevance
    scored = []
    for note in _explore_cache:
        relevance = _keyword_relevance(note, keywords)
        scored.append((note, relevance))

    # Sort: relevant first, then by engagement
    scored.sort(key=lambda x: (x[1] > 0, x[0].engagement_score), reverse=True)

    # If no keyword matches, return top by engagement (still useful as trending data)
    results = [note for note, _ in scored[:max_notes]]

    matched = sum(1 for _, r in scored if r > 0)
    logger.info(
        "XHS search '%s': %d keyword matches out of %d notes, returning %d",
        query, matched, len(_explore_cache), len(results),
    )
    return results


def clear_cache():
    """Clear the explore page cache (call between pipeline runs)."""
    global _explore_cache
    _explore_cache = None


def fetch_xhs_note(
    note_id: str,
    client: httpx.Client | None = None,
    _request_count: list[int] | None = None,
) -> XhsNote | None:
    """Fetch a single XHS note. Currently returns from cache if available."""
    if _explore_cache:
        for note in _explore_cache:
            if note.note_id == note_id:
                return note
    return None
