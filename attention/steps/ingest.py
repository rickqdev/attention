"""Stage 1: Ingest -- Input normalization and context loading."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from attention.config import BASE_DIR, TODAY, load_config
from .base import Step

logger = logging.getLogger("attention.steps.ingest")

CONTEXT_DIR = BASE_DIR / "context"
SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _default_template() -> dict:
    return {
        "_说明": "每次运行前按需填写，attention 会优先使用这些真实信息，不会主动编造。",
        "主体信息": {"名称": "", "来源": "", "价格": "", "补充说明": ""},
        "配角信息": [],
        "场景": {"地点": "", "时间": "", "感受": ""},
        "自由补充": "",
    }


def load_context() -> dict:
    """Load today's context file if it exists."""
    path = CONTEXT_DIR / f"context_{TODAY}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Context load failed: %s", exc)
        return {}


def create_context_template() -> Path:
    """Create today's context template if it doesn't exist."""
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    path = CONTEXT_DIR / f"context_{TODAY}.json"
    if path.exists():
        return path

    example = CONTEXT_DIR / "context.example.json"
    if example.exists():
        content = json.loads(example.read_text(encoding="utf-8"))
    else:
        content = _default_template()
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def context_to_prompt(ctx: dict) -> str:
    """Convert context dict to prompt text."""
    if not ctx:
        return ""

    known = []
    subject = ctx.get("主体信息", {})
    subject_parts = [
        subject.get("名称", "").strip(),
        subject.get("来源", "").strip(),
        subject.get("价格", "").strip(),
        subject.get("补充说明", "").strip(),
    ]
    subject_parts = [p for p in subject_parts if p]
    if subject_parts:
        known.append("主体信息：" + "，".join(subject_parts))

    supporting = [str(s).strip() for s in ctx.get("配角信息", []) if str(s).strip()]
    if supporting:
        known.append("配角信息：" + "、".join(supporting))

    scene = ctx.get("场景", {})
    scene_parts = [
        scene.get("地点", "").strip(),
        scene.get("时间", "").strip(),
        scene.get("感受", "").strip(),
    ]
    scene_parts = [p for p in scene_parts if p]
    if scene_parts:
        known.append("场景：" + "，".join(scene_parts))

    extra = str(ctx.get("自由补充", "")).strip()
    if extra:
        known.append("补充：" + extra)

    if not known:
        return "今天没有补充上下文，正文只能使用图片中可以直接支撑的信息。"

    lines = ["以下是真实上下文，文案只能使用这些信息，不要扩写成不存在的事实："]
    lines.extend(f"- {item}" for item in known)
    return "\n".join(lines)


def discover_images(photos_dir: str | Path) -> list[Path]:
    """Find all supported images in a directory."""
    target = Path(photos_dir).expanduser()
    if not target.exists():
        return []
    return sorted(
        f for f in target.iterdir()
        if f.suffix.lower() in SUPPORTED_EXT and not f.name.startswith(".")
    )


class IngestStep(Step):
    name = "ingest"

    async def run(self, state):
        if state.photos_dir:
            images = discover_images(state.photos_dir)
            state.images = [str(p) for p in images]
            logger.info("Found %d images in %s", len(images), state.photos_dir)

        create_context_template()
        ctx = load_context()
        context_prompt = context_to_prompt(ctx)
        if state.extra_context:
            if context_prompt:
                context_prompt = f"{context_prompt}\n- 临时补充：{state.extra_context}"
            else:
                context_prompt = f"以下是临时补充上下文：\n- {state.extra_context}"
        state.extra_context = context_prompt

        return state
