#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from modules import context_loader, copywriter, photo_tagger
from modules.base import BASE_DIR, TODAY, load_config, log


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
    return parser


def ensure_config():
    try:
        cfg = load_config()
    except FileNotFoundError:
        print("❌ 未找到配置文件。")
        print(f"   请先复制 {BASE_DIR / 'config.example.json'} 为 {BASE_DIR / 'config.json'}")
        print("   然后至少填写 gemini_api_key。")
        raise SystemExit(1)

    gemini_key = str(cfg.get("gemini_api_key", "")).strip()
    if not gemini_key or gemini_key.startswith("YOUR_"):
        print("❌ gemini_api_key 未配置。")
        print(f"   请编辑 {BASE_DIR / 'config.json'}，填写真实的 Gemini API Key。")
        print("   如果你还没有配置文件，可以先从 config.example.json 复制一份。")
        raise SystemExit(1)

    optional_missing = []
    for key, label in (
        ("tavily_api_key", "Tavily 爆款研究"),
        ("glm_api_key", "GLM 文字兜底"),
        ("minimax_api_key", "MiniMax 可选兜底"),
    ):
        value = str(cfg.get(key, "")).strip()
        if not value or value.startswith("YOUR_"):
            optional_missing.append(label)

    if optional_missing:
        log(f"未配置可选能力：{', '.join(optional_missing)}", "WARN")

    return cfg


def render_markdown(run_result):
    photo_result = run_result.get("photos", {})
    notes_result = run_result.get("notes", {})
    primary_intent = photo_result.get("intent", {})
    best_photos = photo_result.get("best_photos", [])
    notes = notes_result.get("notes", [])

    lines = [
        f"# attention 结果 · {run_result.get('date', TODAY)}",
        "",
        "## 图片意图",
        f"- 视觉主角：{primary_intent.get('hero_element', '未识别')}",
        f"- 用户最想问：{primary_intent.get('viewer_question', '未识别')}",
        f"- 注意力切入点：{photo_result.get('primary_attention_angle', '未识别')}",
        f"- 推荐搜索词：{primary_intent.get('social_search_query', '未生成')}",
        "",
        "## 推荐图片",
    ]

    if best_photos:
        for photo in best_photos:
            lines.append(
                f"- {photo.get('filename', 'unknown')} | {photo.get('hero_element', '未识别')} | {photo.get('mood', '未识别')}"
            )
    else:
        lines.append("- 没有可用图片")

    lines.extend(["", "## 生成文案"])
    if not notes:
        lines.append("- 未生成到可用文案")
        return "\n".join(lines) + "\n"

    for index, note in enumerate(notes, start=1):
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
    ensure_config()

    context_loader.create_template()
    context_data = context_loader.load()
    context_prompt = context_loader.to_prompt_block(context_data)

    photo_result = photo_tagger.run(
        photos_dir=Path(args.photos_dir),
        enable_viral_research=not args.skip_viral_research,
    )
    if photo_result.get("total_photos", 0) == 0:
        log("未发现可分析图片，请把图片放进 photos/ 后再运行。", "ERR")
        return 1

    notes_result = copywriter.run(
        photo_data=photo_result,
        context_info=context_prompt,
    )
    if notes_result.get("total", 0) == 0:
        log("文案生成失败，未输出可用结果。", "ERR")
        return 1

    run_result = {
        "product": "attention",
        "date": TODAY,
        "context_loaded": bool(context_data),
        "photos": photo_result,
        "notes": notes_result,
    }

    json_path, md_path = write_outputs(run_result, args.output_dir)
    log(f"结果已写入 {json_path}", "OK")
    log(f"摘要已写入 {md_path}", "OK")

    if args.print_json:
        print(json.dumps(run_result, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
