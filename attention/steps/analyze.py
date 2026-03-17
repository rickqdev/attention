"""Stage 2: Analyze -- Vision analysis of images.

Extracts visual intent: hero element, viewer question, mood, attention angle.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from attention.config import load_config
from attention.providers.base import ProviderChain
from .base import Step

logger = logging.getLogger("attention.steps.analyze")

INTENT_PROMPT = """分析这张图片，找出最值得写成社交平台文案的内容方向。返回 JSON，不要 Markdown 代码块。所有文本字段必须使用简体中文，禁止输出英文句子或英文搜索词。

【第一步：完整描述图中所有元素】
不分类，不贴标签，只描述你看到的：人/物/场景/颜色/材质/氛围/细节。

【第二步：找视觉主角】
问自己三个问题：
1. 用户眼睛第一秒落在哪里？
2. 哪个元素最稀缺、最容易让人停下来？
3. 哪个元素最可能让人追问"这是什么 / 在哪买 / 怎么做 / 为什么会这样"？
选出唯一主角，不限制类型。

【第三步：推断用户最想知道什么】
看到这张图的人，最想问的那一句话是什么？必须具体，不要泛化。

【第四步：生成搜索词】
如果你要搜索"和这张图同类的热门内容"，你会搜什么词？
给出 2-4 个具体中文关键词，空格分隔，不要写成一句话。

【第五步：五维评分】
对这张图独立评分（0-10），每个维度必须给出具体分数：
- visual_impact: 视觉冲击力 — 第一眼能不能让人停下来（构图张力、色彩对比、画面清晰度）
- info_density: 信息密度 — 图中有多少可以写进文案的内容（产品细节、文字、价格、地点）
- uniqueness: 独特性 — 有没有不常见的视角、罕见元素、反差感
- emotion_pull: 情绪感染力 — 能不能引发共鸣、好奇、向往、争议
- cover_potential: 封面潜力 — 如果这张图出现在信息流里作为封面，点击欲有多强

返回字段：
- all_elements: 图中所有可见元素列表
- hero_element: 视觉主角（唯一，具体）
- hero_reason: 为什么它最抓眼
- supporting_elements: 配角元素列表
- mood: 整体氛围短语
- viewer_question: 用户最想追问的话
- social_search_query: 搜索同类热门内容时最应该用的 2-4 个关键词，空格分隔
- attention_angle: 最容易抓住注意力的切入点，用一句话说清
- info_needed: 如果要写成高质量文案，还需要补充哪些真实信息（2-3 项列表）
- visual_impact: 0-10
- info_density: 0-10
- uniqueness: 0-10
- emotion_pull: 0-10
- cover_potential: 0-10
- relevance_score: 0-10，这张图用于社交平台文案的适配度
- exclude_reason: score < 5 时说明原因，否则写 null

只输出 JSON。
"""


# Composite score weights
SCORE_WEIGHTS = {
    "visual_impact": 0.30,
    "info_density": 0.20,
    "uniqueness": 0.20,
    "emotion_pull": 0.20,
    "cover_potential": 0.10,
}
SCORE_DIMENSIONS = list(SCORE_WEIGHTS.keys())


def compute_composite_score(data: dict) -> float:
    """Compute weighted composite score from 5 dimensions."""
    total = 0.0
    for dim, weight in SCORE_WEIGHTS.items():
        total += float(data.get(dim, 0)) * weight
    return round(total, 2)


def _clean_json(text: str) -> str:
    return re.sub(r"```json\s*|\s*```", "", text or "").strip()


def _is_valid_intent(data: dict) -> bool:
    if not isinstance(data, dict):
        return False
    return bool(
        str(data.get("hero_element", "")).strip()
        and str(data.get("viewer_question", "")).strip()
    )


async def analyze_single_image(
    image_path: str | Path, chain: ProviderChain,
) -> dict | None:
    """Analyze one image and return intent dict or None."""
    path = Path(image_path)
    try:
        result = await chain.generate(
            INTENT_PROMPT, images=[str(path)], temperature=0.3,
        )
        if result:
            data = json.loads(_clean_json(result))
            data["filename"] = path.name
            data["composite_score"] = compute_composite_score(data)
            if _is_valid_intent(data):
                return data
            logger.warning("Invalid intent for %s", path.name)
    except Exception as exc:
        logger.warning("Analysis failed for %s: %s", path.name, str(exc)[:120])
    return None


def candidate_queries(intent: dict) -> list[str]:
    """Extract search queries from an intent dict."""
    raw_query = str(intent.get("social_search_query", "")).strip()
    hero = str(intent.get("hero_element", "")).strip()
    queries: list[str] = []

    if raw_query:
        parts = [p for p in raw_query.split() if len(p) <= 8]
        if parts:
            queries.append(" ".join(parts[:2]))
    if hero and len(hero) <= 12:
        queries.append(hero)

    seen: set[str] = set()
    cleaned: list[str] = []
    for q in queries:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            cleaned.append(q)
    return cleaned


def cluster_and_filter(analyzed: list[dict]) -> dict[str, Any]:
    """Cluster analyzed images by attention angle, filter by relevance."""
    relevant = [i for i in analyzed if i.get("relevance_score", 0) >= 5]
    excluded = [i for i in analyzed if i.get("relevance_score", 0) < 5]
    if not relevant:
        relevant = analyzed[:]
        excluded = []

    clusters: dict[str, list] = defaultdict(list)
    for item in relevant:
        key = item.get("attention_angle") or item.get("hero_element") or "其他"
        clusters[key].append(item)

    top = sorted(relevant, key=lambda i: i.get("relevance_score", 0), reverse=True)[:6]

    keywords = []
    for item in top:
        keywords.extend(item.get("supporting_elements", []))
        keywords.extend(item.get("all_elements", [])[:2])

    primary_angle = max(clusters, key=lambda k: len(clusters[k])) if clusters else "通用"
    return {
        "best_photos": top,
        "excluded_photos": excluded,
        "primary_attention_angle": primary_angle,
        "clusters": {k: len(v) for k, v in clusters.items()},
        "keyword_frequency": dict(Counter(keywords).most_common(10)),
    }


class AnalyzeStep(Step):
    name = "analyze"

    def __init__(self, chain: ProviderChain):
        self.chain = chain

    async def run(self, state):
        from attention.pipeline import PipelineState
        from attention.schemas import IntentPayload

        if not state.images:
            state.warnings.append("No images to analyze")
            return state

        analyzed = []
        failed = []
        for img_path in state.images:
            intent = await analyze_single_image(img_path, self.chain)
            if intent:
                analyzed.append(intent)
            else:
                failed.append(Path(img_path).name)

        if not analyzed:
            state.warnings.append("All image analyses failed")
            return state

        state.analyzed_images = analyzed

        cluster = cluster_and_filter(analyzed)
        best = cluster["best_photos"][0] if cluster["best_photos"] else analyzed[0]

        state.intent = IntentPayload(
            hero_element=str(best.get("hero_element", "")).strip(),
            hero_reason=str(best.get("hero_reason", "")).strip(),
            supporting_elements=[
                str(s).strip() for s in best.get("supporting_elements", []) if str(s).strip()
            ],
            mood=str(best.get("mood", "")).strip(),
            viewer_question=str(best.get("viewer_question", "")).strip(),
            attention_angle=str(best.get("attention_angle", "")).strip(),
            social_search_query=str(best.get("social_search_query", "")).strip(),
            info_needed=[str(s).strip() for s in best.get("info_needed", []) if str(s).strip()],
            relevance_score=best.get("relevance_score"),
        )
        state.provider_used = self.chain.last_used

        logger.info(
            "Analyzed %d/%d images, primary angle: %s",
            len(analyzed), len(state.images), cluster["primary_attention_angle"],
        )
        return state
