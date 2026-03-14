"""Stage 3: Research -- Hotspot trending and competitor analysis.

Fetches viral content from XHS (direct scraping), Weibo, Baidu and extracts patterns.
Tavily kept as fallback only.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from typing import Any

from attention.config import load_config
from attention.providers.base import ProviderChain
from attention.scraper.xhs import search_xhs_notes
from .analyze import candidate_queries
from .base import Step

logger = logging.getLogger("attention.steps.research")

VIRAL_PROMPT = """分析以下真实小红书爆款笔记，提取容易抓住注意力的写法。返回 JSON，不要 Markdown 代码块，所有说明字段必须使用简体中文，所有字段都要存在。

帖子数据（含真实互动数据）：
{posts_text}

返回字段：
- top_keywords: 高频词 5-8 个
- viral_title_patterns: 可复用标题结构 3 个
- emotional_hooks: 具体的互动钩子句式 3 个
- core_narrative: 这类内容最常见的叙事逻辑，用一句完整的话说明
- tone_style: 语气风格，描述句式特点
- avoid_cliches: 已经很滥的表达 3-5 个
- raw_posts: 原始帖子片段列表，格式为数组，元素字段为 title 和 text

只输出 JSON。
"""


def _clean_json(text: str) -> str:
    return re.sub(r"```json\s*|\s*```", "", text or "").strip()


def _xhs_notes_to_posts(notes) -> list[dict]:
    """Convert XhsNote objects to the post dict format used by extract_viral_insights."""
    return [
        {
            "title": n.title,
            "content": n.content[:300],
            "url": n.url,
            "liked_count": n.liked_count,
            "collected_count": n.collected_count,
            "comment_count": n.comment_count,
        }
        for n in notes
    ]


def fetch_weibo_hot() -> list[str]:
    """Fetch trending topics from Weibo."""
    import httpx
    try:
        resp = httpx.get(
            "https://weibo.com/ajax/side/hotSearch",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        data = resp.json()
        items = data.get("data", {}).get("realtime", [])
        return [item.get("word", "") for item in items[:15] if item.get("word")]
    except Exception as exc:
        logger.warning("Weibo hot fetch failed: %s", exc)
        return []


def fetch_baidu_hot() -> list[str]:
    """Fetch trending topics from Baidu."""
    import httpx
    try:
        resp = httpx.get(
            "https://top.baidu.com/api/board?platform=wise&tab=realtime",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        data = resp.json()
        cards = data.get("data", {}).get("cards", [])
        topics = []
        for card in cards:
            for item in card.get("content", []):
                word = item.get("word", "")
                if word:
                    topics.append(word)
        return topics[:15]
    except Exception as exc:
        logger.warning("Baidu hot fetch failed: %s", exc)
        return []


async def extract_viral_insights(
    posts: list[dict], chain: ProviderChain,
) -> dict[str, Any]:
    """Extract viral patterns from post data using LLM."""
    if not posts:
        return {}

    posts_text = "\n".join(
        f"标题：{p.get('title', '')}\n摘要：{p.get('content', '')[:150]}"
        f"\n互动：{p.get('liked_count', 0)} 赞 / {p.get('collected_count', 0)} 收藏 / {p.get('comment_count', 0)} 评论"
        for p in posts[:8]
    )
    fallback = {
        "top_keywords": [],
        "viral_title_patterns": [],
        "emotional_hooks": [],
        "core_narrative": "",
        "tone_style": "",
        "avoid_cliches": [],
        "raw_posts": [
            {"title": p.get("title", ""), "text": p.get("content", "")[:200]}
            for p in posts[:3]
        ],
    }

    try:
        result = await chain.generate(
            VIRAL_PROMPT.format(posts_text=posts_text), temperature=0.3,
        )
        if result:
            parsed = json.loads(_clean_json(result))
            parsed.setdefault("raw_posts", fallback["raw_posts"])
            return parsed
    except Exception as exc:
        logger.warning("Viral insight extraction failed: %s", str(exc)[:120])

    return fallback


def aggregate_insights(insights_map: dict[str, dict]) -> dict[str, Any]:
    """Merge insights from multiple queries."""
    if not insights_map:
        return {
            "top_keywords": [], "viral_title_patterns": [], "emotional_hooks": [],
            "core_narrative": "", "tone_style": "", "avoid_cliches": [],
            "raw_posts": [], "per_query": {},
        }

    keywords, patterns, hooks, avoid_words = [], [], [], []
    narratives, tones, raw_posts = [], [], []

    for insight in insights_map.values():
        keywords.extend(insight.get("top_keywords", []))
        patterns.extend(insight.get("viral_title_patterns", []))
        hooks.extend(insight.get("emotional_hooks", []))
        avoid_words.extend(insight.get("avoid_cliches", []))
        if insight.get("core_narrative"):
            narratives.append(insight["core_narrative"])
        if insight.get("tone_style"):
            tones.append(insight["tone_style"])
        raw_posts.extend(insight.get("raw_posts", []))

    return {
        "top_keywords": [i for i, _ in Counter(keywords).most_common(10)],
        "viral_title_patterns": list(dict.fromkeys(patterns))[:3],
        "emotional_hooks": [i for i, _ in Counter(hooks).most_common(5)],
        "core_narrative": max(narratives, key=len, default=""),
        "tone_style": max(tones, key=len, default=""),
        "avoid_cliches": list(dict.fromkeys(avoid_words))[:8],
        "raw_posts": raw_posts[:5],
        "per_query": insights_map,
    }


class ResearchStep(Step):
    name = "research"

    def __init__(self, chain: ProviderChain):
        self.chain = chain

    def should_skip(self, state) -> bool:
        return not state.include_viral_research

    async def run(self, state):
        from attention.pipeline import ResearchPayload

        weibo_topics = fetch_weibo_hot()
        baidu_topics = fetch_baidu_hot()

        insights_map: dict[str, dict] = {}
        seen: set[str] = set()
        request_count: list[int] = [0]  # shared counter for rate limiting

        if state.analyzed_images:
            for intent in state.analyzed_images:
                for query in candidate_queries(intent):
                    if query in seen or len(seen) >= 5:
                        continue
                    seen.add(query)
                    notes = search_xhs_notes(
                        query, max_notes=5, _request_count=request_count,
                    )
                    posts = _xhs_notes_to_posts(notes)
                    if posts:
                        insight = await extract_viral_insights(posts, self.chain)
                        if insight:
                            insights_map[query] = insight

        cfg = load_config()
        for keyword in cfg.seed_keywords:
            if keyword in seen or len(seen) >= 5:
                continue
            seen.add(keyword)
            notes = search_xhs_notes(
                keyword, max_notes=5, _request_count=request_count,
            )
            posts = _xhs_notes_to_posts(notes)
            if posts:
                insight = await extract_viral_insights(posts, self.chain)
                if insight:
                    insights_map[keyword] = insight

        combined = aggregate_insights(insights_map)
        all_topics = list(dict.fromkeys(weibo_topics + baidu_topics))[:20]

        state.research = ResearchPayload(
            topics=all_topics,
            sources={
                "weibo": len(weibo_topics),
                "baidu": len(baidu_topics),
                "xhs": len(insights_map),
            },
            viral_insights=combined,
        )

        logger.info(
            "Research: %d topics, %d XHS viral queries analyzed",
            len(all_topics), len(insights_map),
        )
        return state
