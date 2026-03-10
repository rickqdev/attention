import json
from collections import Counter, defaultdict
from pathlib import Path

from .base import BASE_DIR, TODAY, clean_json, gemini_request, load_config, log, tavily_search, vision_request

PHOTOS_DIR = BASE_DIR / "photos"
SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

INTENT_PROMPT = """分析这张图片，找出最值得写成社交平台文案的内容方向。返回 JSON，不要 Markdown 代码块。所有文本字段必须使用简体中文，禁止输出英文句子或英文搜索词。

【第一步：完整描述图中所有元素】
不分类，不贴标签，只描述你看到的：人/物/场景/颜色/材质/氛围/细节。

【第二步：找视觉主角】
问自己三个问题：
1. 用户眼睛第一秒落在哪里？
2. 哪个元素最稀缺、最容易让人停下来？
3. 哪个元素最可能让人追问“这是什么 / 在哪买 / 怎么做 / 为什么会这样”？
选出唯一主角，不限制类型。

【第三步：推断用户最想知道什么】
看到这张图的人，最想问的那一句话是什么？必须具体，不要泛化。

【第四步：生成搜索词】
如果你要搜索“和这张图同类的热门内容”，你会搜什么词？
给出 2-4 个具体中文关键词，空格分隔，不要写成一句话。

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
- relevance_score: 0-10，这张图用于社交平台文案的适配度
- exclude_reason: score < 5 时说明原因，否则写 null

只输出 JSON。
"""

VIRAL_PROMPT = """分析以下真实内容标题和摘要，提取容易抓住注意力的写法。返回 JSON，不要 Markdown 代码块，所有说明字段必须使用简体中文，所有字段都要存在。

帖子数据：
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


def analyze_image_intent(img_path, provider=None, model_id=None):
    try:
        result = vision_request(
            INTENT_PROMPT,
            images=[str(img_path)],
            provider=provider,
            model_id=model_id,
        )
        if result:
            data = json.loads(clean_json(result))
            data["filename"] = img_path.name
            if _is_valid_intent(data):
                return data
            log(f"[photo] 图片分析结果缺少关键字段：{img_path.name}", "WARN")
    except Exception as exc:
        log(f"[photo] 图片分析失败 {img_path.name}: {str(exc)[:120]}", "WARN")
    return None


def _is_valid_intent(data):
    if not isinstance(data, dict):
        return False
    if not str(data.get("hero_element", "")).strip():
        return False
    if not str(data.get("viewer_question", "")).strip():
        return False
    return True


def search_viral_posts(query):
    results = tavily_search(f"{query} 小红书", max_results=8)
    return [
        {
            "title": item.get("title", ""),
            "content": item.get("content", "")[:300],
            "url": item.get("url", ""),
        }
        for item in results
    ]


def extract_viral_insights(posts, provider=None, retry=2):
    if not posts:
        return {}

    posts_text = "\n".join(
        f"标题：{post.get('title', '')}\n摘要：{post.get('content', '')[:150]}"
        for post in posts[:8]
    )
    fallback = {
        "top_keywords": [],
        "viral_title_patterns": [],
        "emotional_hooks": [],
        "core_narrative": "",
        "tone_style": "",
        "avoid_cliches": [],
        "raw_posts": [
            {"title": post.get("title", ""), "text": post.get("content", "")[:200]}
            for post in posts[:3]
        ],
    }

    for attempt in range(retry + 1):
        try:
            result = gemini_request(
                VIRAL_PROMPT.format(posts_text=posts_text),
                temperature=0.3,
                provider=provider,
            )
            if not result:
                continue
            parsed = json.loads(clean_json(result))
            parsed.setdefault("raw_posts", fallback["raw_posts"])
            return parsed
        except Exception as exc:
            log(f"[photo] 爆款线索提取失败（第 {attempt + 1} 次）: {str(exc)[:120]}", "WARN")

    return fallback


def cluster_and_filter(analyzed):
    relevant = [item for item in analyzed if item.get("relevance_score", 0) >= 5]
    excluded = [item for item in analyzed if item.get("relevance_score", 0) < 5]
    if not relevant:
        relevant = analyzed[:]
        excluded = []

    clusters = defaultdict(list)
    for item in relevant:
        key = item.get("attention_angle") or item.get("hero_element") or "其他"
        clusters[key].append(item)

    top = sorted(relevant, key=lambda item: item.get("relevance_score", 0), reverse=True)[:6]

    keywords = []
    for item in top:
        keywords.extend(item.get("supporting_elements", []))
        keywords.extend(item.get("all_elements", [])[:2])

    primary_angle = max(clusters, key=lambda key: len(clusters[key])) if clusters else "通用"
    return {
        "best_photos": top,
        "excluded_photos": excluded,
        "primary_attention_angle": primary_angle,
        "clusters": {key: len(items) for key, items in clusters.items()},
        "keyword_frequency": dict(Counter(keywords).most_common(10)),
    }


def _candidate_queries(intent):
    raw_query = str(intent.get("social_search_query", "")).strip()
    hero = str(intent.get("hero_element", "")).strip()
    queries = []

    if raw_query:
        parts = [part for part in raw_query.split() if len(part) <= 8]
        if parts:
            queries.append(" ".join(parts[:2]))
    if hero and len(hero) <= 12:
        queries.append(hero)

    cleaned = []
    seen = set()
    for query in queries:
        query = query.strip()
        if not query or query in seen:
            continue
        seen.add(query)
        cleaned.append(query)
    return cleaned


def _aggregate_insights(insights_map):
    if not insights_map:
        return {
            "top_keywords": [],
            "viral_title_patterns": [],
            "emotional_hooks": [],
            "core_narrative": "",
            "tone_style": "",
            "avoid_cliches": [],
            "raw_posts": [],
            "per_query": {},
        }

    keywords = []
    patterns = []
    hooks = []
    avoid_words = []
    narratives = []
    tones = []
    raw_posts = []

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
        "top_keywords": [item for item, _ in Counter(keywords).most_common(10)],
        "viral_title_patterns": list(dict.fromkeys(patterns))[:3],
        "emotional_hooks": [item for item, _ in Counter(hooks).most_common(5)],
        "core_narrative": max(narratives, key=len, default=""),
        "tone_style": max(tones, key=len, default=""),
        "avoid_cliches": list(dict.fromkeys(avoid_words))[:8],
        "raw_posts": raw_posts[:5],
        "per_query": insights_map,
    }


def _failed(target_dir, image_files, reason, failed_images=None):
    return {
        "date": TODAY,
        "input_dir": str(target_dir),
        "total_photos": len(image_files),
        "analyzed": 0,
        "photo_filenames": [image.name for image in image_files],
        "intent": {},
        "viral_insights": {},
        "best_photos": [],
        "excluded_photos": [],
        "primary_attention_angle": "",
        "clusters": {},
        "keyword_frequency": {},
        "error": reason,
        "failed_images": failed_images or [],
    }


def run(photos_dir=None, enable_viral_research=True, provider=None, model_id=None):
    cfg = load_config()
    target_dir = Path(photos_dir).expanduser() if photos_dir else PHOTOS_DIR
    if not target_dir.exists():
        log(f"[photo] 图片目录不存在：{target_dir}", "WARN")
        return _empty(target_dir)

    image_files = sorted(
        file for file in target_dir.iterdir()
        if file.suffix.lower() in SUPPORTED_EXT and not file.name.startswith(".")
    )
    if not image_files:
        log("[photo] photos/ 目录为空。", "WARN")
        return _empty(target_dir)

    log(f"[photo] 发现 {len(image_files)} 张图片，开始分析。", "START")
    analyzed = []
    failed_images = []
    for image in image_files:
        log(f"[photo] 分析 {image.name}", "INFO")
        intent = analyze_image_intent(image, provider=provider, model_id=model_id)
        if intent:
            analyzed.append(intent)
        else:
            failed_images.append(image.name)

    if not analyzed:
        reason = "视觉分析失败。请检查 provider、API key、网络状态或更换图片。"
        log(f"[photo] {reason}", "ERR")
        return _failed(target_dir, image_files, reason, failed_images=failed_images)

    insights_map = {}
    if enable_viral_research:
        seen = set()
        for intent in analyzed:
            for query in _candidate_queries(intent):
                if query in seen or len(seen) >= 5:
                    continue
                seen.add(query)
                posts = search_viral_posts(query)
                if not posts:
                    continue
                insight = extract_viral_insights(posts, provider=provider)
                if insight:
                    insights_map[query] = insight

        for keyword in cfg.get("seed_keywords", []):
            if keyword in seen or len(seen) >= 5:
                continue
            seen.add(keyword)
            posts = search_viral_posts(keyword)
            if not posts:
                continue
            insight = extract_viral_insights(posts, provider=provider)
            if insight:
                insights_map[keyword] = insight
    else:
        log("[photo] 已跳过爆款线索抓取。", "WARN")

    cluster = cluster_and_filter(analyzed)
    combined_insights = _aggregate_insights(insights_map)

    for photo in cluster["best_photos"]:
        query_text = photo.get("social_search_query", "")
        photo["viral_insights"] = next(
            (
                insight
                for key, insight in insights_map.items()
                if key and key in query_text
            ),
            {},
        )

    result = {
        "date": TODAY,
        "input_dir": str(target_dir),
        "total_photos": len(image_files),
        "analyzed": len(analyzed),
        "photo_filenames": [image.name for image in image_files],
        "intent": analyzed[0] if analyzed else {},
        "viral_insights": combined_insights,
        "failed_images": failed_images,
        **cluster,
    }
    log(f"[photo] 完成分析，主切入点：{result['primary_attention_angle']}", "OK")
    return result


def _empty(target_dir):
    return {
        "date": TODAY,
        "input_dir": str(target_dir),
        "total_photos": 0,
        "analyzed": 0,
        "photo_filenames": [],
        "intent": {},
        "viral_insights": {},
        "best_photos": [],
        "excluded_photos": [],
        "primary_attention_angle": "",
        "clusters": {},
        "keyword_frequency": {},
    }
