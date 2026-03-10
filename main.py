#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from modules import context_loader, copywriter, photo_tagger
from modules.base import BASE_DIR, TODAY, load_config, log, set_runtime_options

SUPPORTED_PROVIDERS = ("auto", "gemini", "minimax")


def build_parser():
    parser = argparse.ArgumentParser(
        description="attention / 注意力: 基于图片意图生成更能抓住注意力的中文文案。"
    )
    parser.add_argument(
        "--photos-dir",
        default=str(BASE_DIR / "photos"),
        help="输入图片目录，默认使用仓库下的 photos/",
    )
    parser.add_argument(
        "--output-dir",
        default=str(BASE_DIR / "output"),
        help="输出目录，默认使用仓库下的 output/",
    )
    parser.add_argument(
        "--skip-viral-research",
        action="store_true",
        help="跳过可选的爆款线索抓取，仅根据图片和上下文生成文案。",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="在终端额外打印完整 JSON 结果。",
    )
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default="auto",
        help="模型提供方。auto 会优先 Gemini，失败后回退 MiniMax。",
    )
    parser.add_argument(
        "--model-id",
        default="",
        help="可选模型 ID（按 provider 解释）。为空时使用默认模型。",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="运行时 API Key，不会写入磁盘。provider=auto 时按 Gemini key 处理。",
    )
    parser.add_argument(
        "--tavily-api-key",
        default="",
        help="可选运行时 Tavily key，仅用于爆款线索抓取。",
    )
    return parser


def _has_config_key(cfg, key_name):
    value = str(cfg.get(key_name, "")).strip()
    return bool(value and not value.startswith("YOUR_"))


def ensure_config(provider, api_key="", tavily_api_key="", skip_viral_research=False):
    try:
        cfg = load_config()
    except FileNotFoundError:
        print("❌ 未找到配置文件。")
        print(f"   请把 {BASE_DIR / 'config.example.json'} 放在仓库内，或自行创建 config.json。")
        print("   你也可以直接通过命令行/界面填写 provider 与 API key。")
        raise SystemExit(1)

    has_gemini_key = bool(api_key.strip()) if provider in ("auto", "gemini") else False
    has_minimax_key = bool(api_key.strip()) if provider == "minimax" else False
    has_gemini_key = has_gemini_key or _has_config_key(cfg, "gemini_api_key")
    has_minimax_key = has_minimax_key or _has_config_key(cfg, "minimax_api_key")

    if provider == "gemini" and not has_gemini_key:
        print("❌ 当前 provider=gemini，但未检测到可用 key。")
        print("   请在命令里传 --api-key，或在 config.json 填写 gemini_api_key。")
        raise SystemExit(1)
    if provider == "minimax" and not has_minimax_key:
        print("❌ 当前 provider=minimax，但未检测到可用 key。")
        print("   请在命令里传 --api-key，或在 config.json 填写 minimax_api_key。")
        raise SystemExit(1)
    if provider == "auto" and not (has_gemini_key or has_minimax_key):
        print("❌ provider=auto 需要至少一个可用视觉模型 key（Gemini 或 MiniMax）。")
        print("   你可以传 --api-key（默认按 Gemini key 处理），或在 config.json 配置 key。")
        raise SystemExit(1)

    optional_missing = []
    for key_name, label in (
        ("glm_api_key", "GLM 文字兜底"),
        ("minimax_api_key", "MiniMax 可选兜底"),
    ):
        if not _has_config_key(cfg, key_name):
            optional_missing.append(label)

    has_tavily = bool(tavily_api_key.strip()) or _has_config_key(cfg, "tavily_api_key")
    if not skip_viral_research and not has_tavily:
        optional_missing.append("Tavily 爆款研究（可通过 --skip-viral-research 跳过）")

    if optional_missing:
        log(f"未配置可选能力：{', '.join(optional_missing)}", "WARN")

    return cfg


def build_attention_result(photo_result, notes_result, context_loaded, provider, model_id):
    intent_data = photo_result.get("intent", {})
    notes = notes_result.get("notes", [])
    copy_candidates = []

    for note in notes:
        copy_candidates.append(
            {
                "title_a": note.get("title_a", ""),
                "title_b": note.get("title_b", ""),
                "content": note.get("content", ""),
                "tags": note.get("tags", ""),
            }
        )

    best_copy = copy_candidates[0] if copy_candidates else {}
    why_it_works = (
        photo_result.get("primary_attention_angle")
        or intent_data.get("attention_angle", "")
        or "基于视觉主角和用户追问点，形成了明确的注意力切入。"
    )

    return {
        "product": "attention",
        "date": TODAY,
        "context_loaded": bool(context_loaded),
        "intent": intent_data.get("hero_element", ""),
        "user_question": intent_data.get("viewer_question", ""),
        "copy_candidates": copy_candidates,
        "best_copy": best_copy,
        "why_it_works": why_it_works,
        "meta": {
            "provider": provider,
            "model_id": model_id or "",
            "photos_analyzed": photo_result.get("analyzed", 0),
            "source_images": photo_result.get("photo_filenames", []),
        },
    }


def render_markdown(run_result):
    best_copy = run_result.get("best_copy", {})
    candidates = run_result.get("copy_candidates", [])

    lines = [
        f"# attention 结果 · {run_result.get('date', TODAY)}",
        "",
        "## 核心洞察",
        f"- 视觉主角：{run_result.get('intent', '未识别') or '未识别'}",
        f"- 用户最想问：{run_result.get('user_question', '未识别') or '未识别'}",
        f"- 为什么有效：{run_result.get('why_it_works', '未生成') or '未生成'}",
        "",
        "## 最佳文案",
    ]

    if best_copy:
        lines.extend(
            [
                f"- 标题 A：{best_copy.get('title_a', '')}",
                f"- 标题 B：{best_copy.get('title_b', '')}",
                f"- 标签：{best_copy.get('tags', '')}",
                "",
                best_copy.get("content", "").strip(),
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
                f"- 标题 A：{note.get('title_a', '')}",
                f"- 标题 B：{note.get('title_b', '')}",
                f"- 标签：{note.get('tags', '')}",
                "",
                note.get("content", "").strip(),
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def write_outputs(run_result, output_dir):
    output_path = Path(output_dir).expanduser()
    output_path.mkdir(parents=True, exist_ok=True)

    json_path = output_path / f"attention_{TODAY}.json"
    md_path = output_path / f"attention_{TODAY}.md"

    json_path.write_text(
        json.dumps(run_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(run_result), encoding="utf-8")
    return json_path, md_path


def main():
    parser = build_parser()
    args = parser.parse_args()
    runtime_provider = args.provider
    runtime_model_id = args.model_id.strip()
    runtime_key = args.api_key.strip()
    runtime_tavily_key = args.tavily_api_key.strip()

    runtime_keys = {}
    if runtime_key:
        if runtime_provider in ("gemini", "minimax"):
            runtime_keys[runtime_provider] = runtime_key
        else:
            runtime_keys["gemini"] = runtime_key
    if runtime_tavily_key:
        runtime_keys["tavily"] = runtime_tavily_key

    set_runtime_options(
        provider=runtime_provider,
        model_id=runtime_model_id,
        api_keys=runtime_keys,
    )
    ensure_config(
        provider=runtime_provider,
        api_key=runtime_key,
        tavily_api_key=runtime_tavily_key,
        skip_viral_research=args.skip_viral_research,
    )

    context_loader.create_template()
    context_data = context_loader.load()
    context_prompt = context_loader.to_prompt_block(context_data)

    photo_result = photo_tagger.run(
        photos_dir=Path(args.photos_dir),
        enable_viral_research=not args.skip_viral_research,
        provider=runtime_provider,
        model_id=runtime_model_id,
    )
    if photo_result.get("total_photos", 0) == 0:
        log("未发现可分析图片，请把图片放进 photos/ 后再运行。", "ERR")
        return 1

    notes_result = copywriter.run(
        photo_data=photo_result,
        context_info=context_prompt,
        provider=runtime_provider,
        model_id=runtime_model_id,
    )
    if notes_result.get("total", 0) == 0:
        log("文案生成失败，未输出可用结果。", "ERR")
        return 1

    run_result = build_attention_result(
        photo_result=photo_result,
        notes_result=notes_result,
        context_loaded=context_data,
        provider=runtime_provider,
        model_id=runtime_model_id,
    )

    json_path, md_path = write_outputs(run_result, args.output_dir)
    log(f"结果已写入 {json_path}", "OK")
    log(f"摘要已写入 {md_path}", "OK")

    if args.print_json:
        print(json.dumps(run_result, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
