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


def _extract_intent_fields(photo_data: dict) -> dict:
    """Extract intent fields from photo_data, handling both dict and object."""
    intent = photo_data.get("intent", {})
    if isinstance(intent, dict):
        return {
            "hero_element": intent.get("hero_element", "主角"),
            "hero_reason": intent.get("hero_reason", ""),
            "supporting": ", ".join(intent.get("supporting_elements", [])) or "无",
            "all_elements": ", ".join(intent.get("all_elements", [])[:10]) or "见图片",
            "mood": intent.get("mood", ""),
            "viewer_question": intent.get("viewer_question", ""),
            "social_query": intent.get("social_search_query", ""),
            "info_needed": intent.get("info_needed", []),
            "attention_angle": photo_data.get("primary_attention_angle", intent.get("attention_angle", "")),
        }
    return {
        "hero_element": str(getattr(intent, "hero_element", "主角")),
        "hero_reason": str(getattr(intent, "hero_reason", "")),
        "supporting": "无",
        "all_elements": "见图片",
        "mood": str(getattr(intent, "mood", "")),
        "viewer_question": str(getattr(intent, "viewer_question", "")),
        "social_query": str(getattr(intent, "social_search_query", "")),
        "info_needed": list(getattr(intent, "info_needed", [])),
        "attention_angle": str(getattr(intent, "attention_angle", "")),
    }


def _format_viral_section(viral_insights: dict, raw_posts_limit: int = 3) -> dict:
    """Format viral insights into display strings."""
    top_keywords = viral_insights.get("top_keywords", [])
    title_patterns = viral_insights.get("viral_title_patterns", [])
    emotional_hooks = viral_insights.get("emotional_hooks", [])
    raw_posts = viral_insights.get("raw_posts", [])

    reference_posts = []
    for idx, post in enumerate(raw_posts[:raw_posts_limit], 1):
        reference_posts.append(
            f"【参考 {idx}】标题：{post.get('title', '')}\n正文：{post.get('text', '')[:160]}"
        )

    return {
        "keyword_text": "、".join(top_keywords[:8]) if top_keywords else "无",
        "pattern_text": " | ".join(title_patterns[:3]) if title_patterns else "无",
        "hook_text": " | ".join(emotional_hooks[:3]) if emotional_hooks else "无",
        "core_narrative": viral_insights.get("core_narrative", "") or "无",
        "tone_style": viral_insights.get("tone_style", "") or "无",
        "cliche_text": "、".join(viral_insights.get("avoid_cliches", [])[:6]) or "无",
        "reference_text": "\n".join(reference_posts) if reference_posts else "无",
    }


def build_grid_prompt(
    grid_slots: list[dict],
    analyzed_images: list[dict],
    viral_insights: dict | None = None,
    context_info: str = "",
) -> str:
    """Build copy generation prompt for a full 9-grid arrangement."""
    cfg = load_config()
    persona = cfg.persona
    forbidden = cfg.forbidden_words

    # Build grid overview
    grid_lines = []
    cover_hero = ""
    for slot in grid_slots:
        fname = slot.get("filename", "?")
        role = slot.get("role", "")
        pos = slot.get("position", 0)
        # Find matching analyzed image
        matched = next((img for img in analyzed_images if img.get("filename") == fname), {})
        hero = matched.get("hero_element", "")
        mood = matched.get("mood", "")
        if pos == 1:
            cover_hero = hero
        grid_lines.append(f"  位置{pos}（{role}）：{fname} — 主角「{hero}」氛围「{mood}」")

    grid_overview = "\n".join(grid_lines)

    # Collect all unique elements across grid
    all_heroes = []
    all_questions = []
    all_elements_flat = []
    for img in analyzed_images:
        hero = img.get("hero_element", "")
        if hero and hero not in all_heroes:
            all_heroes.append(hero)
        q = img.get("viewer_question", "")
        if q and q not in all_questions:
            all_questions.append(q)
        all_elements_flat.extend(img.get("all_elements", [])[:3])

    heroes_text = "、".join(all_heroes[:6])
    questions_text = "\n".join(f"  - {q}" for q in all_questions[:4])
    elements_text = "、".join(list(dict.fromkeys(all_elements_flat))[:12])

    # Cover image details
    cover_img = next((img for img in analyzed_images if img.get("hero_element") == cover_hero), analyzed_images[0] if analyzed_images else {})
    cover_question = cover_img.get("viewer_question", "")
    cover_angle = cover_img.get("attention_angle", "")

    missing_info = []
    for img in analyzed_images:
        missing_info.extend(img.get("info_needed", []))
    missing_info = list(dict.fromkeys(missing_info))[:5]
    missing_info_text = "、".join(missing_info) if missing_info else "无"

    # Viral section
    viral = _format_viral_section(viral_insights or {})

    return f"""你是 attention / 注意力 的中文文案引擎。任务是为一组已经编排好的九宫格图片生成整组叙事文案。

【九宫格编排】
共 {len(grid_slots)} 张图，封面是「{cover_hero}」：
{grid_overview}

【整组内容概览】
核心元素：{heroes_text}
图中可见元素：{elements_text}
用户看到这组图最可能追问的：
{questions_text}
封面切入点：{cover_angle}
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
高频关键词：{viral["keyword_text"]}
标题结构：{viral["pattern_text"]}
互动钩子：{viral["hook_text"]}
叙事逻辑：{viral["core_narrative"]}
语气特征：{viral["tone_style"]}
已经俗套的表达：{viral["cliche_text"]}
真实参考片段：
{viral["reference_text"]}

【生成规则】
1. 输出 1 条整组文案，不是每张图单独写。
2. 标题 A：基于封面图「{cover_hero}」制造钩子，18 字以内。
3. 标题 B：换角度，用整组内容的主题切入，18 字以内。
4. 正文 150-280 字：
   - 第一句直接回应封面图最可能引发的追问：{cover_question}
   - 自然涵盖 3-4 张关键图的信息节拍（不需要每张都写）
   - 像真人在发内容，不要营销稿
5. 翻页引导：一句话引导用户翻看特定位置，如"划到第X张看xxx"。
6. 标签 6-10 个，综合全部图片的核心元素。
7. 禁止出现这些违禁词：{", ".join(forbidden)}
8. 不要出现 Markdown 代码块。
9. 如果上下文没有提供价格、店名、品牌，不要编造。

【输出格式】
===笔记1===
【封面图】：{cover_img.get("filename", "")}
【标题A】：
【标题B】：
【正文】：
【翻页引导】：
【标签】：
【违禁词检查】：通过
"""


def build_prompt(
    photo_data: dict, viral_insights: dict | None = None, context_info: str = "",
) -> str:
    """Build the copy generation prompt from single image intent + context (legacy)."""
    cfg = load_config()
    persona = cfg.persona
    forbidden = cfg.forbidden_words

    fields = _extract_intent_fields(photo_data)
    if viral_insights is None:
        viral_insights = photo_data.get("viral_insights", {})

    viral = _format_viral_section(viral_insights)
    missing_info_text = "、".join(fields["info_needed"]) if fields["info_needed"] else "无"

    return f"""你是 attention / 注意力 的中文文案引擎。任务是基于图片意图和可选的爆款线索，生成一条更容易让人停下来阅读的中文社交平台文案。

【图片意图】
视觉主角：{fields["hero_element"]}
主角理由：{fields["hero_reason"]}
配角元素：{fields["supporting"]}
图中元素：{fields["all_elements"]}
氛围：{fields["mood"]}
用户最想问：{fields["viewer_question"]}
搜索同类热门内容的关键词：{fields["social_query"]}
最强注意力切入点：{fields["attention_angle"]}
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
高频关键词：{viral["keyword_text"]}
标题结构：{viral["pattern_text"]}
互动钩子：{viral["hook_text"]}
叙事逻辑：{viral["core_narrative"]}
语气特征：{viral["tone_style"]}
已经俗套的表达：{viral["cliche_text"]}
真实参考片段：
{viral["reference_text"]}

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
            "photo": extract(r"【(?:推荐照片|封面图)】[：:]\s*(.*?)(?=【|$)"),
            "title_a": extract(r"【标题A】[：:]\s*(.*?)(?=【|$)"),
            "title_b": extract(r"【标题B】[：:]\s*(.*?)(?=【|$)"),
            "content": extract(r"【正文】[：:]\s*(.*?)(?=【(?:翻页引导|标签)】|【违禁词|$)"),
            "flip_guide": extract(r"【翻页引导】[：:]\s*(.*?)(?=【|$)"),
            "tags": _clean_tags(raw_tags, viral_keywords=viral_keywords),
        }

        for key in ("title_a", "title_b", "content", "flip_guide"):
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

        viral_insights = state.research.viral_insights if state.research else {}

        # Use grid-aware prompt when grid arrangement exists
        if state.grid and state.grid.slots:
            grid_slot_dicts = [s.model_dump() for s in state.grid.slots]
            prompt = build_grid_prompt(
                grid_slots=grid_slot_dicts,
                analyzed_images=state.analyzed_images,
                viral_insights=viral_insights,
                context_info=state.extra_context,
            )
        else:
            photo_data = {
                "intent": intent.model_dump(),
                "primary_attention_angle": intent.attention_angle or intent.hero_element,
                "viral_insights": viral_insights,
            }
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
                flip_guide=n.get("flip_guide", ""),
            )
            for n in notes
        ]

        state.copy_candidates = candidates
        state.best_copy = candidates[0] if candidates else None
        state.why_it_works = (
            state.grid.grid_narrative if state.grid and state.grid.grid_narrative
            else intent.attention_angle
            or "基于视觉主角和用户追问点，形成了明确的注意力切入。"
        )
        state.provider_used = self.chain.last_used

        passed = sum(1 for n in notes if n.get("pass_check"))
        logger.info("Generated %d copies, %d passed forbidden check", len(notes), passed)
        return state
