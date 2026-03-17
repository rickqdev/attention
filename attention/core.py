"""Core API: v2 pipeline-based implementation.

Provides the public API functions:
- analyze_image_intent(request) -> response
- generate_attention_copy(request) -> response
- run_attention_pipeline(photos_dir, ...) -> response
- render_markdown(result) -> str
- write_outputs(result, output_dir) -> (json_path, md_path)
"""

from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import tempfile
from pathlib import Path

from .config import TODAY, load_config
from .format import get_formatter
from .pipeline import Pipeline, PipelineState
from .providers.base import ProviderChain
from .providers.gemini import GeminiProvider
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
from .steps import AnalyzeStep, ArrangeStep, GenerateStep, IngestStep, ResearchStep


def _build_chain(provider: str = "auto", api_key: str = "") -> ProviderChain:
    """Build a provider chain from config."""
    cfg = load_config()
    providers = []

    # Gemini is always first (primary, supports vision)
    gemini_key = api_key if provider in ("auto", "gemini") else ""
    if not gemini_key:
        gemini_key = cfg.get_api_key("gemini")
    if gemini_key:
        providers.append(GeminiProvider(api_key=gemini_key))

    # Add OpenAI-compatible providers from config if available
    try:
        from .providers.openai_compat import OpenAICompatProvider
        # MiniMax (vision)
        minimax_key = cfg.get_api_key("minimax")
        if minimax_key:
            providers.append(OpenAICompatProvider(
                base_url="https://api.minimax.chat/v1/text",
                api_key=minimax_key,
                model=cfg.minimax_vl_model or "MiniMax-VL-01",
                name="minimax",
                supports_vision=True,
            ))
        # GLM (text only)
        glm_key = cfg.get_api_key("glm")
        if glm_key:
            providers.append(OpenAICompatProvider(
                base_url="https://open.bigmodel.cn/api/paas/v4",
                api_key=glm_key,
                model=cfg.glm_model or "glm-4-flash",
                name="glm",
            ))
        # Ollama (local, text only)
        ollama_url = cfg.qwen_ollama_url or "http://localhost:11434"
        providers.append(OpenAICompatProvider(
            base_url=f"{ollama_url}/v1",
            model=cfg.qwen_model or "qwen2.5:0.5b",
            name="ollama",
        ))
    except ImportError:
        pass

    return ProviderChain(providers)


def _build_pipeline(chain: ProviderChain) -> Pipeline:
    """Build the standard 5-step pipeline."""
    return Pipeline([
        IngestStep(),
        AnalyzeStep(chain),
        ArrangeStep(),
        ResearchStep(chain),
        GenerateStep(chain),
    ])


# --- Error helpers ---

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


def _safe_token(value) -> str:
    token = str(value or "").strip()
    if not token or token.startswith("YOUR_"):
        return ""
    return token


# --- Image helpers ---

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


# --- Rendering ---

def render_markdown(result) -> str:
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
    ]

    # Grid arrangement section
    grid = getattr(result, "_grid", None)
    # Try to get grid from meta or direct attribute
    if grid is None and hasattr(result, "meta") and hasattr(result.meta, "grid"):
        grid = result.meta.grid

    if grid and grid.slots:
        lines.extend(["## 九宫格编排", ""])
        if grid.grid_narrative:
            lines.append(f"**叙事线**：{grid.grid_narrative}")
            lines.append("")
        lines.append("| 位置 | 文件 | 角色 | 综合分 |")
        lines.append("|------|------|------|--------|")
        for slot in grid.slots:
            lines.append(f"| {slot.position} | {slot.filename} | {slot.role} | {slot.composite_score:.1f} |")
        if grid.cover_alternatives:
            lines.append("")
            alt_names = ", ".join(a.filename for a in grid.cover_alternatives)
            lines.append(f"**封面备选**：{alt_names}")
        if grid.excluded:
            lines.append("")
            lines.append(f"**淘汰**：{len(grid.excluded)} 张")
        lines.append("")

    lines.append("## 最佳文案")
    if best_copy:
        lines.extend([
            f"- 标题 A：{best_copy.title_a}",
            f"- 标题 B：{best_copy.title_b}",
            f"- 标签：{best_copy.tags}",
        ])
        if best_copy.flip_guide:
            lines.append(f"- 翻页引导：{best_copy.flip_guide}")
        lines.extend(["", best_copy.content.strip()])
    else:
        lines.append("- 未生成到可用文案")

    lines.extend(["", "## 候选文案"])
    if not candidates:
        lines.append("- 无候选文案")
        return "\n".join(lines) + "\n"

    for index, note in enumerate(candidates, start=1):
        lines.extend([
            f"### 文案 {index}",
            f"- 标题 A：{note.title_a}",
            f"- 标题 B：{note.title_b}",
            f"- 标签：{note.tags}",
        ])
        if note.flip_guide:
            lines.append(f"- 翻页引导：{note.flip_guide}")
        lines.extend(["", note.content.strip(), ""])
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


# --- Public API functions ---

def analyze_image_intent(request: AnalyzeImageIntentRequest) -> AnalyzeImageIntentResponse:
    """Analyze a single image to extract visual intent."""
    provider = str(request.provider or "auto").strip().lower()
    chain = _build_chain(provider=provider, api_key=request.api_key)

    if not chain.available_providers(need_vision=True):
        return _error_response(
            AnalyzeImageIntentResponse, provider,
            "missing_api_key",
            "没有可用的视觉模型 key。",
            ["传入 api_key。", "或在 config.json 中配置 gemini_api_key。"],
        )

    try:
        with tempfile.TemporaryDirectory(prefix="attention_intent_") as tmpdir:
            image_path = _materialize_image(request.image, tmpdir)
            state = PipelineState(images=[str(image_path)], provider=provider)
            pipeline = Pipeline([AnalyzeStep(chain)])
            state = asyncio.run(pipeline.run(state))
    except FileNotFoundError as exc:
        return _error_response(
            AnalyzeImageIntentResponse, provider,
            "image_not_found", str(exc),
            ["检查 image.path 是否正确。"],
        )
    except ValueError as exc:
        return _error_response(
            AnalyzeImageIntentResponse, provider,
            "invalid_image_input", str(exc),
            ["改用本地 path。", "或重新传入合法的 Base64 数据。"],
        )
    except Exception as exc:
        return _error_response(
            AnalyzeImageIntentResponse, provider,
            "vision_analysis_failed",
            f"视觉分析失败：{str(exc)[:160]}",
            ["确认 provider 与 api_key 可用。", "更换一张更清晰的图片再试。"],
        )

    if not state.intent:
        return _error_response(
            AnalyzeImageIntentResponse, provider,
            "vision_analysis_failed",
            "视觉分析失败，未获得有效图片意图。",
            ["确认 provider 与 api_key 可用。", "更换一张更清晰的图片再试。"],
        )

    return AnalyzeImageIntentResponse(
        status="ok",
        intent=state.intent,
        meta=ResponseMeta(
            provider_requested=provider,
            provider_used=state.provider_used or provider,
            warnings=state.warnings,
        ),
    )


def generate_attention_copy(request: GenerateAttentionCopyRequest) -> GenerateAttentionCopyResponse:
    """Generate copy from an existing intent (no image analysis)."""
    provider = str(request.provider or "auto").strip().lower()
    chain = _build_chain(provider=provider, api_key=request.api_key)

    if not chain.available_providers():
        return _error_response(
            GenerateAttentionCopyResponse, provider,
            "missing_api_key",
            "没有可用的 LLM key。",
            ["传入 api_key。", "或在 config.json 中配置 gemini_api_key。"],
        )

    # Build state from request
    context_prompt = _context_to_prompt(request.context)
    state = PipelineState(
        intent=request.intent,
        analyzed_images=[request.intent.model_dump()],
        extra_context=context_prompt,
        include_viral_research=request.include_viral_research,
        provider=provider,
    )

    # Run research + generate only (skip ingest + analyze)
    steps = []
    if request.include_viral_research:
        steps.append(ResearchStep(chain))
    steps.append(GenerateStep(chain))
    pipeline = Pipeline(steps)

    try:
        state = asyncio.run(pipeline.run(state))
    except Exception as exc:
        return _error_response(
            GenerateAttentionCopyResponse, provider,
            "copy_generation_failed",
            f"文案生成失败：{str(exc)[:160]}",
            ["确认 provider 与 api_key 可用。", "确认 intent 来自真实视觉分析。"],
        )

    if not state.copy_candidates:
        return _error_response(
            GenerateAttentionCopyResponse, provider,
            "copy_generation_failed",
            "文案生成失败，未获得可用结果。",
            ["更换图片意图后重试。", "确认 provider 与 api_key 可用。"],
        )

    response = GenerateAttentionCopyResponse(
        status="ok",
        intent=request.intent,
        copy_candidates=state.copy_candidates,
        best_copy=state.best_copy,
        why_it_works=state.why_it_works,
        meta=ResponseMeta(
            provider_requested=provider,
            provider_used=state.provider_used or provider,
            warnings=state.warnings,
            used_viral_research=request.include_viral_research and state.research is not None,
        ),
    )
    response.markdown = render_markdown(response)
    return response


def run_attention_pipeline(
    photos_dir,
    provider="auto",
    api_key="",
    include_viral_research=True,
    extra_context="",
) -> GenerateAttentionCopyResponse:
    """Run the full pipeline: ingest -> analyze -> research -> generate."""
    provider = str(provider or "auto").strip().lower()
    chain = _build_chain(provider=provider, api_key=api_key)

    if not chain.available_providers(need_vision=True):
        return _error_response(
            GenerateAttentionCopyResponse, provider,
            "missing_api_key",
            "没有可用的视觉模型 key。",
            ["传入 api_key。", "或在 config.json 中配置 gemini_api_key。"],
        )

    state = PipelineState(
        photos_dir=str(photos_dir),
        extra_context=str(extra_context or "").strip(),
        include_viral_research=include_viral_research,
        provider=provider,
    )

    pipeline = _build_pipeline(chain)

    try:
        state = asyncio.run(pipeline.run(state))
    except Exception as exc:
        return _error_response(
            GenerateAttentionCopyResponse, provider,
            "pipeline_failed",
            f"Pipeline 执行失败：{str(exc)[:160]}",
            ["确认 provider 与 api_key 可用。", "确认 photos/ 目录中有可读图片。"],
        )

    if not state.copy_candidates:
        return _error_response(
            GenerateAttentionCopyResponse, provider,
            "copy_generation_failed",
            "文案生成失败，未获得可用结果。",
            ["更换图片后重试。", "确认 provider 与 api_key 可用。"],
        )

    response = GenerateAttentionCopyResponse(
        status="ok",
        intent=state.intent,
        grid=state.grid,
        copy_candidates=state.copy_candidates,
        best_copy=state.best_copy,
        why_it_works=state.why_it_works,
        meta=ResponseMeta(
            provider_requested=provider,
            provider_used=state.provider_used or provider,
            warnings=state.warnings,
            used_viral_research=include_viral_research and state.research is not None,
            source_images=[Path(p).name for p in state.images],
            photos_analyzed=len(state.analyzed_images),
        ),
    )
    response.markdown = render_markdown(response)
    return response


def _context_to_prompt(context: CopyContext) -> str:
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
