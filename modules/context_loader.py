import json
from pathlib import Path

from .base import BASE_DIR, TODAY, log

CONTEXT_DIR = BASE_DIR / "context"
EXAMPLE_PATH = CONTEXT_DIR / "context.example.json"


def _today_context_path():
    return CONTEXT_DIR / f"context_{TODAY}.json"


def _default_template():
    return {
        "_说明": "每次运行前按需填写，attention 会优先使用这些真实信息，不会主动编造。",
        "主体信息": {
            "名称": "",
            "来源": "",
            "价格": "",
            "补充说明": ""
        },
        "配角信息": [],
        "场景": {
            "地点": "",
            "时间": "",
            "感受": ""
        },
        "自由补充": ""
    }


def create_template():
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    target_path = _today_context_path()
    if target_path.exists():
        return target_path

    if EXAMPLE_PATH.exists():
        content = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    else:
        content = _default_template()
    target_path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"[context] 已生成今日上下文模板：{target_path.name}", "WARN")
    return target_path


def load():
    path = _today_context_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"[context] 上下文加载失败：{str(exc)[:120]}", "WARN")
        return {}


def to_prompt_block(ctx):
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
    subject_parts = [part for part in subject_parts if part]
    if subject_parts:
        known.append("主体信息：" + "，".join(subject_parts))

    supporting = [str(item).strip() for item in ctx.get("配角信息", []) if str(item).strip()]
    if supporting:
        known.append("配角信息：" + "、".join(supporting))

    scene = ctx.get("场景", {})
    scene_parts = [
        scene.get("地点", "").strip(),
        scene.get("时间", "").strip(),
        scene.get("感受", "").strip(),
    ]
    scene_parts = [part for part in scene_parts if part]
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
