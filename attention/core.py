from __future__ import annotations

import base64
import json
import mimetypes
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

from modules import context_loader, copywriter, photo_tagger
from modules.base import (
    BASE_DIR,
    TODAY,
    clear_provider_trace,
    clear_runtime_options,
    get_provider_trace,
    load_config,
    set_runtime_options,
)

from .schemas import (
    AnalyzeImageIntentRequest,
    AnalyzeImageIntentResponse,
    AttentionError,
    CopyCandidate,
    CopyContext,
    GenerateAttentionCopyRequest,
    GenerateAttentionCopyResponse,
    IntentPayload,
    ResponseMeta,
)

_RUNTIME_LOCK = threading.Lock()
_SUPPORTED_PROVIDERS = {"auto", "gemini", "minimax"}


def _safe_token(value):
    token = str(value or "").strip()
    if not token or token.startswith("YOUR_"):
        return ""
    return token


def _config_has_key(config, key_name):
    return bool(_safe_token(config.get(key_name, "")))


def _resolve_requested_key(provider, api_key):
    key = _safe_token(api_key)
    if not key:
        return {}
    if provider in ("gemini", "minimax"):
        return {provider: key}
    return {"gemini": key}


def _normalize_provider(provider):
    selected = str(provider or "auto").strip().lower()
    if selected not in _SUPPORTED_PROVIDERS:
        return "auto"
    return selected


def _error_response(response_cls, provider, code, message, suggestions, warnings=None):
    meta = ResponseMeta(
        provider_requested=provider,
        provider_used="",
        warnings=warnings or [],
    )
    return response_cls(
        status="error",
        meta=meta,
        error=AttentionError(
            code=code,
            message=message,
            suggestions=suggestions,
        ),
    )


def _validate_provider_access(provider, api_key="", tavily_api_key="", include_viral_research=False):
    provider = _normalize_provider(provider)
    config = load_config()
    has_gemini = bool(_safe_token(api_key)) if provider in ("auto", "gemini") else False
    has_minimax = bool(_safe_token(api_key)) if provider == "minimax" else False
    has_gemini = has_gemini or _config_has_key(config, "gemini_api_key")
    has_minimax = has_minimax or _config_has_key(config, "minimax_api_key")

    if provider == "gemini" and not has_gemini:
        return _error_response(
            AnalyzeImageIntentResponse,
            provider,
            "missing_api_key",
            "当前 provider=gemini，但没有可用 API key。",
            ["通过运行时传入 api_key。", "或在本地 config.json 中填写 gemini_api_key。"],
        )
    if provider == "minimax" and not has_minimax:
        return _error_response(
            AnalyzeImageIntentResponse,
            provider,
            "missing_api_key",
            "当前 provider=minimax，但没有可用 API key。",
            ["通过运行时传入 api_key。", "或在本地 config.json 中填写 minimax_api_key。"],
        )
    if provider == "auto" and not (has_gemini or has_minimax):
        return _error_response(
            AnalyzeImageIntentResponse,
            provider,
            "missing_api_key",
            "provider=auto 需要至少一个可用视觉模型 key（Gemini 或 MiniMax）。",
            ["传入 api_key。", "或在本地 config.json 中配置 gemini_api_key / minimax_api_key。"],
        )

    warnings = []
    tavily_available = bool(_safe_token(tavily_api_key)) or _config_has_key(config, "tavily_api_key")
    if include_viral_research and not tavily_available:
        warnings.append("未提供 Tavily key，已跳过爆款线索抓取。")
    return warnings


@contextmanager
def _runtime_session(provider, api_key="", tavily_api_key=""):
    runtime_keys = _resolve_requested_key(provider, api_key)
    tavily = _safe_token(tavily_api_key)
    if tavily:
        runtime_keys["tavily"] = tavily

    with _RUNTIME_LOCK:
        set_runtime_options(provider=provider, api_keys=runtime_keys)
        clear_provider_trace()
        try:
            yield
        finally:
            clear_runtime_options()
            clear_provider_trace()


def _image_suffix(image_input):
    if image_input.path:
        return Path(image_input.path).suffix.lower() or ".jpg"
    guessed = mimetypes.guess_extension(image_input.mime_type or "")
    return guessed or ".jpg"


def _materialize_image(image_input, target_dir):
    if image_input.path:
        path = Path(image_input.path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"图片路径不存在：{path}")
        return path

    try:
        raw = base64.b64decode(image_input.base64.encode("utf-8"), validate=True)
    except Exception as exc:
        raise ValueError("image.base64 不是合法的 Base64 数据。") from exc

    suffix = _image_suffix(image_input)
    path = Path(target_dir) / f"upload{suffix}"
    path.write_bytes(raw)
    return path


def _intent_from_raw(data):
    return IntentPayload(
        hero_element=str(data.get("hero_element", "")).strip(),
        hero_reason=str(data.get("hero_reason", "")).strip(),
        supporting_elements=[str(item).strip() for item in data.get("supporting_elements", []) if str(item).strip()],
        mood=str(data.get("mood", "")).strip(),
        viewer_question=str(data.get("viewer_question", "")).strip(),
        attention_angle=str(data.get("attention_angle", "")).strip(),
        social_search_query=str(data.get("social_search_query", "")).strip(),
        info_needed=[str(item).strip() for item in data.get("info_needed", []) if str(item).strip()],
        relevance_score=data.get("relevance_score"),
    )


def _context_to_prompt(context: CopyContext):
    known = []
    subject_parts = [
        context.subject.name.strip(),
        context.subject.source.strip(),
        context.subject.price.strip(),
        context.subject.notes.strip(),
    ]
    subject_parts = [item for item in subject_parts if item]
    if subject_parts:
        known.append("主体信息：" + "，".join(subject_parts))

    supporting = [str(item).strip() for item in context.supporting if str(item).strip()]
    if supporting:
        known.append("配角信息：" + "、".join(supporting))

    scene_parts = [
        context.scene.location.strip(),
        context.scene.time.strip(),
        context.scene.feeling.strip(),
    ]
    scene_parts = [item for item in scene_parts if item]
    if scene_parts:
        known.append("场景：" + "，".join(scene_parts))

    extra = context.extra.strip()
    if extra:
        known.append("补充：" + extra)

    if not known:
        return "今天没有补充上下文，正文只能使用图片中可以直接支撑的信息。"

    lines = ["以下是真实上下文，文案只能使用这些信息，不要扩写成不存在的事实："]
    lines.extend(f"- {item}" for item in known)
    return "\n".join(lines)


def _copy_candidates(notes):
    candidates = []
    for note in notes or []:
        candidates.append(
            CopyCandidate(
                title_a=note.get("title_a", ""),
                title_b=note.get("title_b", ""),
                content=note.get("content", ""),
                tags=note.get("tags", ""),
            )
        )
    return candidates


def render_markdown(result):
    best_copy = result.best_copy
    candidates = result.copy_candidates
    lines = [
        f"# attention 结果 · {TODAY}",
        "",
        "## 核心洞察",
        f"- 视觉主角：{result.intent.hero_element if result.intent else '未识别'}",
        f"- 用户最想问：{result.intent.viewer_question if result.intent else '未识别'}",
        f"- 为什么有效：{result.why_it_works or '未生成'}",
        "",
        "## 最佳文案",
    ]
    if best_copy:
        lines.extend(
            [
                f"- 标题 A：{best_copy.title_a}",
                f"- 标题 B：{best_copy.title_b}",
                f"- 标签：{best_copy.tags}",
                "",
                best_copy.content.strip(),
            ]
        )
    else:
        lines.append("- 未生成到可用文案")

    lines.extend(["", "## 候选文案"])
    if not candidates:
        lines.append("- 无候选文案")
        return "\n".join(lines) + "\n"

    for index, note in enumerate(candidates, start=1):
        lines.extend(
            [
                f"### 文案 {index}",
                f"- 标题 A：{note.title_a}",
                f"- 标题 B：{note.title_b}",
                f"- 标签：{note.tags}",
                "",
                note.content.strip(),
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def write_outputs(result, output_dir):
    output_path = Path(output_dir).expanduser()
    output_path.mkdir(parents=True, exist_ok=True)

    json_path = output_path / f"attention_{TODAY}.json"
    md_path = output_path / f"attention_{TODAY}.md"

    payload = result.model_dump(exclude_none=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    return json_path, md_path


def analyze_image_intent(request: AnalyzeImageIntentRequest) -> AnalyzeImageIntentResponse:
    provider = _normalize_provider(request.provider)
    validation = _validate_provider_access(provider=provider, api_key=request.api_key)
    if isinstance(validation, AnalyzeImageIntentResponse):
        return validation

    try:
        with tempfile.TemporaryDirectory(prefix="attention_intent_") as tmpdir:
            image_path = _materialize_image(request.image, tmpdir)
            with _runtime_session(provider=provider, api_key=request.api_key):
                raw_intent = photo_tagger.analyze_image_intent(image_path, provider=provider)
                provider_used = get_provider_trace().get("vision", "")
    except FileNotFoundError as exc:
        return _error_response(
            AnalyzeImageIntentResponse,
            provider,
            "image_not_found",
            str(exc),
            ["检查 image.path 是否正确。"],
        )
    except ValueError as exc:
        return _error_response(
            AnalyzeImageIntentResponse,
            provider,
            "invalid_image_input",
            str(exc),
            ["改用本地 path。", "或重新传入合法的 Base64 数据。"],
        )
    except Exception as exc:
        return _error_response(
            AnalyzeImageIntentResponse,
            provider,
            "vision_analysis_failed",
            f"视觉分析失败：{str(exc)[:160]}",
            ["确认 provider 与 api_key 可用。", "更换一张更清晰的图片再试。"],
        )

    if not raw_intent:
        return _error_response(
            AnalyzeImageIntentResponse,
            provider,
            "vision_analysis_failed",
            "视觉分析失败，未获得有效图片意图。",
            ["确认 provider 与 api_key 可用。", "更换一张更清晰的图片再试。"],
        )

    return AnalyzeImageIntentResponse(
        status="ok",
        intent=_intent_from_raw(raw_intent),
        meta=ResponseMeta(
            provider_requested=provider,
            provider_used=provider_used or provider,
            warnings=list(validation),
        ),
    )


def _build_photo_data(intent: IntentPayload, viral_insights=None):
    return {
        "intent": intent.model_dump(),
        "primary_attention_angle": intent.attention_angle or intent.hero_element,
        "viral_insights": viral_insights or {},
    }


def _build_viral_insights(intent: IntentPayload, provider, include_viral_research):
    warnings = []
    if not include_viral_research:
        return {}, warnings, False

    queries = photo_tagger._candidate_queries(intent.model_dump())
    if not queries:
        warnings.append("图片意图中没有可用搜索词，已跳过爆款线索抓取。")
        return {}, warnings, False

    insights_map = {}
    for query in queries:
        posts = photo_tagger.search_viral_posts(query)
        if not posts:
            continue
        insights_map[query] = photo_tagger.extract_viral_insights(posts, provider=provider)

    if not insights_map:
        warnings.append("未抓取到可用爆款线索，已按图片意图继续生成。")
        return {}, warnings, False

    return photo_tagger._aggregate_insights(insights_map), warnings, True


def generate_attention_copy(request: GenerateAttentionCopyRequest) -> GenerateAttentionCopyResponse:
    provider = _normalize_provider(request.provider)
    validation = _validate_provider_access(
        provider=provider,
        api_key=request.api_key,
        tavily_api_key=request.tavily_api_key,
        include_viral_research=request.include_viral_research,
    )
    if isinstance(validation, AnalyzeImageIntentResponse):
        return _error_response(
            GenerateAttentionCopyResponse,
            provider,
            validation.error.code if validation.error else "missing_api_key",
            validation.error.message if validation.error else "未提供可用 API key。",
            validation.error.suggestions if validation.error else ["通过运行时传入 api_key。"],
        )

    prompt = _context_to_prompt(request.context)
    with _runtime_session(provider=provider, api_key=request.api_key, tavily_api_key=request.tavily_api_key):
        viral_insights, warnings, used_viral_research = _build_viral_insights(
            request.intent,
            provider=provider,
            include_viral_research=request.include_viral_research,
        )
        warnings = list(validation) + warnings
        photo_data = _build_photo_data(request.intent, viral_insights=viral_insights)
        notes_result = copywriter.run(
            photo_data=photo_data,
            context_info=prompt,
            provider=provider,
        )
        provider_used = get_provider_trace().get("text", "")

    if notes_result.get("error"):
        return _error_response(
            GenerateAttentionCopyResponse,
            provider,
            "copy_generation_failed",
            notes_result["error"],
            ["确认 provider 与 api_key 可用。", "确认 intent 来自真实视觉分析。"],
            warnings=warnings,
        )
    if notes_result.get("total", 0) == 0:
        return _error_response(
            GenerateAttentionCopyResponse,
            provider,
            "copy_generation_failed",
            "文案生成失败，未获得可用结果。",
            ["更换图片意图后重试。", "确认 provider 与 api_key 可用。"],
            warnings=warnings,
        )

    candidates = _copy_candidates(notes_result.get("notes", []))
    best_copy = candidates[0] if candidates else None
    response = GenerateAttentionCopyResponse(
        status="ok",
        intent=request.intent,
        copy_candidates=candidates,
        best_copy=best_copy,
        why_it_works=request.intent.attention_angle or "基于视觉主角和用户追问点，形成了明确的注意力切入。",
        meta=ResponseMeta(
            provider_requested=provider,
            provider_used=provider_used or provider,
            warnings=warnings,
            used_viral_research=used_viral_research,
        ),
    )
    response.markdown = render_markdown(response)
    return response


def _legacy_context_prompt():
    context_loader.create_template()
    context_data = context_loader.load()
    return context_data, context_loader.to_prompt_block(context_data)


def run_attention_pipeline(
    photos_dir,
    provider="auto",
    api_key="",
    tavily_api_key="",
    include_viral_research=True,
    extra_context="",
):
    provider = _normalize_provider(provider)
    validation = _validate_provider_access(
        provider=provider,
        api_key=api_key,
        tavily_api_key=tavily_api_key,
        include_viral_research=include_viral_research,
    )
    if isinstance(validation, AnalyzeImageIntentResponse):
        return _error_response(
            GenerateAttentionCopyResponse,
            provider,
            validation.error.code if validation.error else "missing_api_key",
            validation.error.message if validation.error else "未提供可用 API key。",
            validation.error.suggestions if validation.error else ["通过运行时传入 api_key。"],
        )

    context_data, context_prompt = _legacy_context_prompt()
    extra = str(extra_context or "").strip()
    if extra:
        if context_prompt:
            context_prompt = f"{context_prompt}\n- 临时补充：{extra}"
        else:
            context_prompt = f"以下是临时补充上下文，请仅在有依据时使用：\n- {extra}"

    with _runtime_session(provider=provider, api_key=api_key, tavily_api_key=tavily_api_key):
        photo_result = photo_tagger.run(
            photos_dir=Path(photos_dir),
            enable_viral_research=include_viral_research,
            provider=provider,
        )
        vision_provider_used = get_provider_trace().get("vision", "")
        if photo_result.get("error"):
            return _error_response(
                GenerateAttentionCopyResponse,
                provider,
                "vision_analysis_failed",
                photo_result["error"],
                ["确认 provider 与 api_key 可用。", "确认 photos/ 目录中有可读图片。"],
                warnings=list(validation),
            )
        notes_result = copywriter.run(
            photo_data=photo_result,
            context_info=context_prompt,
            provider=provider,
        )
        text_provider_used = get_provider_trace().get("text", "")

    if notes_result.get("error"):
        return _error_response(
            GenerateAttentionCopyResponse,
            provider,
            "copy_generation_failed",
            notes_result["error"],
            ["确认 provider 与 api_key 可用。", "确认图片视觉分析成功。"],
            warnings=list(validation),
        )
    if notes_result.get("total", 0) == 0:
        return _error_response(
            GenerateAttentionCopyResponse,
            provider,
            "copy_generation_failed",
            "文案生成失败，未获得可用结果。",
            ["更换图片后重试。", "确认 provider 与 api_key 可用。"],
            warnings=list(validation),
        )

    intent = _intent_from_raw(photo_result.get("intent", {}))
    candidates = _copy_candidates(notes_result.get("notes", []))
    best_copy = candidates[0] if candidates else None
    response = GenerateAttentionCopyResponse(
        status="ok",
        intent=intent,
        copy_candidates=candidates,
        best_copy=best_copy,
        why_it_works=photo_result.get("primary_attention_angle")
        or intent.attention_angle
        or "基于视觉主角和用户追问点，形成了明确的注意力切入。",
        meta=ResponseMeta(
            provider_requested=provider,
            provider_used=text_provider_used or vision_provider_used or provider,
            warnings=list(validation),
            used_viral_research=include_viral_research and bool(photo_result.get("viral_insights")),
            source_images=photo_result.get("photo_filenames", []),
            failed_images=photo_result.get("failed_images", []),
            photos_analyzed=photo_result.get("analyzed", 0),
        ),
    )
    response.markdown = render_markdown(response)
    return response
