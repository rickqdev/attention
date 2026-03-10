#!/usr/bin/env python3
import argparse
import json

from attention.core import run_attention_pipeline, write_outputs
from modules.base import BASE_DIR, log

SUPPORTED_PROVIDERS = ("auto", "gemini", "minimax")


def build_parser():
    parser = argparse.ArgumentParser(
        description="attention / 注意力: 先识别图片里最值得展开的意图，再生成清晰、可继续修改的中文图文草案。"
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
        help="跳过可选的爆款线索抓取，仅根据图片意图和上下文生成图文。",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="在终端额外打印完整 JSON 结果，便于查看意图和文案草案。",
    )
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default="auto",
        help="模型提供方。auto 会优先 Gemini，失败后回退 MiniMax。",
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


def main():
    parser = build_parser()
    args = parser.parse_args()

    result = run_attention_pipeline(
        photos_dir=args.photos_dir,
        provider=args.provider,
        api_key=args.api_key,
        tavily_api_key=args.tavily_api_key,
        include_viral_research=not args.skip_viral_research,
    )

    if result.status != "ok":
        if result.error:
            log(result.error.message, "ERR")
            for suggestion in result.error.suggestions:
                print(f"- {suggestion}")
        return 1

    json_path, md_path = write_outputs(result, args.output_dir)
    log(f"结果已写入 {json_path}", "OK")
    log(f"摘要已写入 {md_path}", "OK")

    if args.print_json:
        print(json.dumps(result.model_dump(exclude_none=True), ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
