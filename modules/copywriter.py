import json
import re

from .base import TODAY, check_forbidden, gemini_request, load_config, log


def _clean_tags(raw_tags, viral_keywords=None):
    tags = re.findall(r"#[^#\s]+", raw_tags or "")
    if not tags:
        tags = ["#" + item.strip().lstrip("#") for item in re.split(r"[\s,，]+", raw_tags or "") if item.strip()]

    if len(tags) < 6 and viral_keywords:
        for keyword in viral_keywords:
            candidate = "#" + keyword.strip().lstrip("#")
            if candidate not in tags:
                tags.append(candidate)
            if len(tags) >= 8:
                break
    return " ".join(tags[:10])


def build_prompt(photo_data, viral_insights=None, context_info=""):
    cfg = load_config()
    persona = cfg.get("persona", {})
    forbidden = cfg.get("forbidden_words", [])

    intent = photo_data.get("intent", {})
    hero_element = intent.get("hero_element", "主角")
    hero_reason = intent.get("hero_reason", "")
    supporting = ", ".join(intent.get("supporting_elements", [])) or "无"
    all_elements = ", ".join(intent.get("all_elements", [])[:10]) or "见图片"
    mood = intent.get("mood", "")
    viewer_question = intent.get("viewer_question", "")
    social_query = intent.get("social_search_query", "")
    info_needed = intent.get("info_needed", [])
    attention_angle = photo_data.get("primary_attention_angle", intent.get("attention_angle", ""))

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
    for index, post in enumerate(raw_posts[:3], start=1):
        reference_posts.append(
            f"【参考 {index}】标题：{post.get('title', '')}\n正文：{post.get('text', '')[:160]}"
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
名字：{persona.get("name", "")}
背景：{persona.get("background", "")}
专长：{persona.get("specialty", "")}
语气要求：{persona.get("tone", "")}
禁止风格：{persona.get("avoid", "")}

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
4. 正文 120-220 字，第一句必须直接回应“用户最想问”的问题，不能铺垫太久。
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


def parse_notes(raw_text, viral_keywords=None):
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
            "raw": section,
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


def _fallback_note(photo_data):
    intent = photo_data.get("intent", {})
    hero = intent.get("hero_element") or "图片主角"
    question = intent.get("viewer_question") or f"{hero}到底是什么？"
    angle = photo_data.get("primary_attention_angle") or intent.get("attention_angle") or "从一个细节切入"
    query = intent.get("social_search_query", "")
    keyword_seed = [item for item in query.split() if item][:4]
    base_tags = [f"#{hero}", "#注意力文案", "#图文创作"]
    base_tags.extend(f"#{item}" for item in keyword_seed if item)
    tags = " ".join(base_tags[:8])

    return {
        "photo": intent.get("filename", ""),
        "title_a": f"{hero}｜第一眼就会被问到",
        "title_b": f"不是堆信息，是把 {hero} 讲清楚",
        "content": (
            f"这张图最容易让人停下来的点是「{hero}」。"
            f"多数人第一反应会问：{question}"
            f"如果把内容展开，关键不是把所有信息都塞满，而是先把这个追问讲清楚，"
            f"再补一到两个能支撑判断的细节。"
            f"这条文案的核心策略是：{angle}。"
        ),
        "tags": tags,
        "raw": "",
        "auto_forbidden_check": [],
        "pass_check": True,
        "_fallback": True,
    }


def run(photo_data, cfg=None, context_info="", provider=None, model_id=None):
    del cfg
    viral_insights = photo_data.get("viral_insights", {})
    prompt = build_prompt(photo_data, viral_insights=viral_insights, context_info=context_info)
    raw = gemini_request(prompt, temperature=0.8, provider=provider, model=model_id)
    if not raw:
        log("所有文字模型均失败，已使用规则兜底生成文案。", "WARN")
        note = _fallback_note(photo_data)
        return {"notes": [note], "total": 1, "passed_check": 1, "raw": "", "fallback": True}

    notes = parse_notes(raw, viral_keywords=viral_insights.get("top_keywords", []))
    for note in notes:
        full_text = note.get("title_a", "") + note.get("title_b", "") + note.get("content", "")
        hits = check_forbidden(full_text)
        note["auto_forbidden_check"] = hits
        note["pass_check"] = not hits

    passed = sum(1 for note in notes if note.get("pass_check"))
    log(f"[copy] 文案生成完成：{len(notes)} 条，{passed} 条通过违禁词检查。", "OK")
    return {
        "date": TODAY,
        "notes": notes,
        "total": len(notes),
        "passed_check": passed,
        "raw": raw,
        "content_angle": photo_data.get("primary_attention_angle", ""),
    }
