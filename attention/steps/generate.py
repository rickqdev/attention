"""Stage 4: Generate -- AI copy generation from image intent.

Produces multi-variant A/B titles, content, and tags.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from attention.config import load_config
from attention.providers.base import ProviderChain
from attention.schemas import CopyCandidate
from .base import Step

logger = logging.getLogger("attention.steps.generate")


def _normalize_tag(tag: str, max_length: int = 16) -> str:
    candidate = "#" + re.sub(r"\s+", "", str(tag or "").strip().lstrip("#"))
    if candidate == "#" or len(candidate) > max_length:
        return ""
    return candidate


def _clean_tags(raw_tags: str, viral_keywords: list[str] | None = None) -> str:
    tags = re.findall(r"#[^#\s]+", raw_tags or "")
    if not tags:
        tags = ["#" + s.strip().lstrip("#") for s in re.split(r"[\s,，]+", raw_tags or "") if s.strip()]

    if len(tags) < 6 and viral_keywords:
        for kw in viral_keywords:
            candidate = "#" + kw.strip().lstrip("#")
            if candidate not in tags:
                tags.append(candidate)
            if len(tags) >= 8:
                break

    cleaned = []
    seen: set[str] = set()
    for tag in tags:
        normalized = _normalize_tag(tag)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
        if len(cleaned) >= 10:
            break
    return " ".join(cleaned)


def build_prompt(
    photo_data: dict, viral_insights: dict | None = None, context_info: str = "",
) -> str:
    """Build the copy generation prompt from image intent + context."""
    cfg = load_config()
    persona = cfg.persona
    forbidden = cfg.forbidden_words

    intent = photo_data.get("intent", {})
    if isinstance(intent, dict):
        hero_element = intent.get("hero_element", "主角")
        hero_reason = intent.get("hero_reason", "")
        supporting = ", ".join(intent.get("supporting_elements", [])) or "无"
        all_elements = ", ".join(intent.get("all_elements", [])[:10]) or "见图片"
        mood = intent.get("mood", "")
        viewer_question = intent.get("viewer_question", "")
        social_query = intent.get("social_search_query", "")
        info_needed = intent.get("info_needed", [])
        attention_angle = photo_data.get("primary_attention_angle", intent.get("attention_angle", ""))
    else:
        hero_element = str(getattr(intent, "hero_element", "主角"))
        hero_reason = str(getattr(intent, "hero_reason", ""))
        supporting = "无"
        all_elements = "见图片"
        mood = str(getattr(intent, "mood", ""))
        viewer_question = str(getattr(intent, "viewer_question", ""))
        social_query = str(getattr(intent, "social_search_query", ""))
        info_needed = list(getattr(intent, "info_needed", []))
        attention_angle = str(getattr(intent, "attention_angle", ""))

    if viral_insights is None:
        viral_insights = photo_data.get("viral_insights", {})

    top_keywords = viral_insights.get("top_keywords", [])
    title_patterns = viral_insights.get("viral_title_patterns", [])
    emotional_hooks = viral_insights.get("emotional_hooks", [])
    tone_style = viral_insights.get("tone_style", "")
    core_narrative = viral_insights.get("core_narrative", "")
    avoid_cliches = viral_insights.get("avoid_cliches", [])
    raw_posts = viral_insights.get("raw_posts", [])

    reference_posts = []
    for idx, post in enumerate(raw_posts[:3], 1):
        reference_posts.append(
            f"【参考 {idx}】标题：{post.get('title', '')}\n正文：{post.get('text', '')[:160]}"
        )

    missing_info_text = "、".join(info_needed) if info_needed else "无"
    keyword_text = "、".join(top_keywords[:8]) if top_keywords else "无"
    pattern_text = " | ".join(title_patterns[:3]) if title_patterns else "无"
    hook_text = " | ".join(emotional_hooks[:3]) if emotional_hooks else "无"
    reference_text = "\n".join(reference_posts) if reference_posts else "无"
    cliche_text = "、".join(avoid_cliches[:6]) if avoid_cliches else "无"

    return f"""你是 attention / 注意力 的中文文案引擎。任务是基于图片意图和可选的爆款线索，生成一条更容易让人停下来阅读的中文社交平台文案。

【图片意图】
视觉主角：{hero_element}
主角理由：{hero_reason}
配角元素：{supporting}
图中元素：{all_elements}
氛围：{mood}
用户最想问：{viewer_question}
搜索同类热门内容的关键词：{social_query}
最强注意力切入点：{attention_angle}
缺失但不能编造的信息：{missing_info_text}

【作者设定】
名字：{persona.name}
背景：{persona.background}
专长：{persona.specialty}
语气要求：{persona.tone}
禁止风格：{persona.avoid}

【上下文信息】
{context_info or "今天没有额外上下文，请只写图中能支撑的内容。"}

【可选爆款线索】
高频关键词：{keyword_text}
标题结构：{pattern_text}
互动钩子：{hook_text}
叙事逻辑：{core_narrative or "无"}
语气特征：{tone_style or "无"}
已经俗套的表达：{cliche_text}
真实参考片段：
{reference_text}

【生成规则】
1. 输出 1 条文案。
2. 标题 A：直接点名主角，再制造一个反差、悬念或判断，18 字以内。
3. 标题 B：换一个角度，用问题或对比句式，18 字以内。
4. 正文 120-220 字，第一句必须直接回应"用户最想问"的问题，不能铺垫太久。
5. 正文要像真人在发内容，不要写成营销稿，不要写万能鸡汤句。
6. 如果上下文没有提供价格、店名、品牌、教程细节，就不要编造。
7. 标签 6-10 个，优先使用爆款高频词和图片核心元素。
8. 禁止出现这些违禁词：{", ".join(forbidden)}
9. 不要出现 Markdown 代码块。

【输出格式】
===笔记1===
【推荐照片】：
【标题A】：
【标题B】：
【正文】：
【标签】：
【违禁词检查】：通过
"""


def parse_notes(raw_text: str, viral_keywords: list[str] | None = None) -> list[dict]:
    """Parse generated copy text into structured notes."""
    if not raw_text:
        return []

    sections = re.split(r"={2,}\s*笔记\s*\d+\s*={2,}", raw_text)
    notes = []
    for section in sections:
        section = section.strip()
        if len(section) < 20:
            continue

        def extract(pattern, default=""):
            match = re.search(pattern, section, re.DOTALL)
            return match.group(1).strip() if match else default

        raw_tags = extract(r"【标签】[：:]\s*(.*?)(?=【违禁词|$)")
        note = {
            "photo": extract(r"【推荐照片】[：:]\s*(.*?)(?=【|$)"),
            "title_a": extract(r"【标题A】[：:]\s*(.*?)(?=【|$)"),
            "title_b": extract(r"【标题B】[：:]\s*(.*?)(?=【|$)"),
            "content": extract(r"【正文】[：:]\s*(.*?)(?=【标签】|【违禁词|$)"),
            "tags": _clean_tags(raw_tags, viral_keywords=viral_keywords),
        }

        for key in ("title_a", "title_b", "content"):
            value = note.get(key, "")
            value = re.sub(r"```[\s\S]*?```", "", value)
            value = re.sub(r"`[^`]+`", "", value)
            value = re.sub(r"\n{3,}", "\n\n", value)
            note[key] = value.strip()

        if note["title_a"] or note["content"]:
            notes.append(note)
    return notes


def _fallback_note(intent_data: dict) -> dict:
    hero = intent_data.get("hero_element") or "图片主角"
    question = intent_data.get("viewer_question") or f"{hero}到底是什么？"
    angle = intent_data.get("attention_angle") or "从一个细节切入"
    query = intent_data.get("social_search_query", "")
    keyword_seed = [s for s in query.split() if s][:4]
    base_tags = [f"#{hero}", "#注意力文案", "#图文创作"]
    base_tags.extend(f"#{s}" for s in keyword_seed if s)
    tags = _clean_tags(" ".join(base_tags[:8]))

    return {
        "title_a": f"{hero}|第一眼就会被问到",
        "title_b": f"不是堆信息，是把 {hero} 讲清楚",
        "content": (
            f"这张图最容易让人停下来的点是「{hero}」。"
            f"多数人第一反应会问：{question}"
            f"如果把内容展开，关键不是把所有信息都塞满，而是先把这个追问讲清楚，"
            f"再补一到两个能支撑判断的细节。"
            f"这条文案的核心策略是：{angle}。"
        ),
        "tags": tags,
        "_fallback": True,
    }


class GenerateStep(Step):
    name = "generate"

    def __init__(self, chain: ProviderChain):
        self.chain = chain

    def should_skip(self, state) -> bool:
        return state.intent is None

    async def run(self, state):
        intent = state.intent
        if not intent or not intent.hero_element or not intent.viewer_question:
            state.warnings.append("No valid intent for copy generation")
            return state

        photo_data = {
            "intent": intent.model_dump(),
            "primary_attention_angle": intent.attention_angle or intent.hero_element,
            "viral_insights": state.research.viral_insights if state.research else {},
        }

        viral_insights = photo_data["viral_insights"]
        prompt = build_prompt(photo_data, viral_insights=viral_insights, context_info=state.extra_context)

        try:
            raw = await self.chain.generate(prompt, temperature=0.8)
        except Exception as exc:
            logger.warning("Copy generation failed: %s", exc)
            note = _fallback_note(intent.model_dump())
            state.copy_candidates = [CopyCandidate(
                title_a=note["title_a"],
                title_b=note["title_b"],
                content=note["content"],
                tags=note["tags"],
            )]
            state.best_copy = state.copy_candidates[0]
            state.warnings.append("Used fallback copy generation")
            return state

        notes = parse_notes(raw, viral_keywords=viral_insights.get("top_keywords", []))

        cfg = load_config()
        for note in notes:
            full_text = note.get("title_a", "") + note.get("title_b", "") + note.get("content", "")
            hits = [w for w in cfg.forbidden_words if w in full_text]
            note["forbidden_hits"] = hits
            note["pass_check"] = not hits

        candidates = [
            CopyCandidate(
                title_a=n.get("title_a", ""),
                title_b=n.get("title_b", ""),
                content=n.get("content", ""),
                tags=n.get("tags", ""),
            )
            for n in notes
        ]

        state.copy_candidates = candidates
        state.best_copy = candidates[0] if candidates else None
        state.why_it_works = (
            intent.attention_angle
            or "基于视觉主角和用户追问点，形成了明确的注意力切入。"
        )
        state.provider_used = self.chain.last_used

        passed = sum(1 for n in notes if n.get("pass_check"))
        logger.info("Generated %d copies, %d passed forbidden check", len(notes), passed)
        return state
