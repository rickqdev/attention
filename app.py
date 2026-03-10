#!/usr/bin/env python3
import shutil
import tempfile
from pathlib import Path

import gradio as gr

from main import build_attention_result, ensure_config, render_markdown, write_outputs
from modules import context_loader, copywriter, photo_tagger
from modules.base import BASE_DIR, set_runtime_options


def _merge_context_prompt(extra_context):
    context_loader.create_template()
    ctx_data = context_loader.load()
    prompt = context_loader.to_prompt_block(ctx_data)
    extra = (extra_context or "").strip()
    if not extra:
        return ctx_data, prompt

    if prompt:
        merged = f"{prompt}\n- 临时补充：{extra}"
    else:
        merged = f"以下是临时补充上下文，请仅在有依据时使用：\n- {extra}"
    return ctx_data, merged


def run_attention(
    image_path,
    provider,
    model_id,
    api_key,
    tavily_api_key,
    skip_viral_research,
    extra_context,
):
    if not image_path:
        return "请先上传一张图片。", None, "未执行。"

    runtime_keys = {}
    key = (api_key or "").strip()
    if key:
        runtime_keys[provider if provider in ("gemini", "minimax") else "gemini"] = key
    tavily = (tavily_api_key or "").strip()
    if tavily:
        runtime_keys["tavily"] = tavily

    set_runtime_options(
        provider=provider,
        model_id=(model_id or "").strip(),
        api_keys=runtime_keys,
    )
    try:
        ensure_config(
            provider=provider,
            api_key=key,
            tavily_api_key=tavily,
            skip_viral_research=skip_viral_research,
        )
    except SystemExit:
        return "配置不足，请检查 provider 与 API key。", None, "执行失败。"

    context_data, context_prompt = _merge_context_prompt(extra_context)

    with tempfile.TemporaryDirectory(prefix="attention_upload_") as tmpdir:
        src_path = Path(image_path)
        tmp_photo = Path(tmpdir) / src_path.name
        shutil.copy2(src_path, tmp_photo)

        photo_result = photo_tagger.run(
            photos_dir=Path(tmpdir),
            enable_viral_research=not skip_viral_research,
            provider=provider,
            model_id=(model_id or "").strip(),
        )
        if photo_result.get("total_photos", 0) == 0:
            return "未检测到可分析图片。", None, "执行失败。"

        notes_result = copywriter.run(
            photo_data=photo_result,
            context_info=context_prompt,
            provider=provider,
            model_id=(model_id or "").strip(),
        )
        if notes_result.get("total", 0) == 0:
            return "文案生成失败，请更换图片或模型参数。", None, "执行失败。"

    run_result = build_attention_result(
        photo_result=photo_result,
        notes_result=notes_result,
        context_loaded=context_data,
        provider=provider,
        model_id=(model_id or "").strip(),
    )
    _, md_path = write_outputs(run_result, BASE_DIR / "output")
    markdown = render_markdown(run_result)
    status = f"已生成并写入：{md_path}"
    return markdown, run_result, status


def build_demo():
    with gr.Blocks(title="attention / 注意力") as demo:
        gr.Markdown(
            """
# attention / 注意力
Image → Attention Copy  
上传图片后，分析“最能抓住注意力的意图”，输出候选文案与最佳文案。

API Key 只在本次运行内存中使用，不会写入磁盘。
"""
        )
        with gr.Row():
            with gr.Column(scale=1):
                image_input = gr.Image(type="filepath", label="上传图片")
                provider = gr.Dropdown(
                    choices=["gemini", "minimax", "auto"],
                    value="gemini",
                    label="Provider",
                )
                model_id = gr.Textbox(
                    value="",
                    label="Model ID（可选）",
                    placeholder="留空使用默认模型",
                )
                api_key = gr.Textbox(
                    value="",
                    label="Provider API Key",
                    type="password",
                    placeholder="运行时输入，不会落盘",
                )
                tavily_key = gr.Textbox(
                    value="",
                    label="Tavily API Key（可选）",
                    type="password",
                )
                skip_viral = gr.Checkbox(
                    value=True,
                    label="跳过爆款线索抓取（更快）",
                )
                extra_context = gr.Textbox(
                    value="",
                    label="临时上下文（可选）",
                    lines=4,
                    placeholder="例如：主体是手工饰品，预算 99，地点上海。",
                )
                run_btn = gr.Button("生成注意力文案", variant="primary")
            with gr.Column(scale=1):
                status = gr.Textbox(label="状态", interactive=False)
                md_output = gr.Markdown(label="Markdown 预览")
                json_output = gr.JSON(label="JSON 输出")

        run_btn.click(
            fn=run_attention,
            inputs=[
                image_input,
                provider,
                model_id,
                api_key,
                tavily_key,
                skip_viral,
                extra_context,
            ],
            outputs=[md_output, json_output, status],
        )
    return demo


if __name__ == "__main__":
    build_demo().launch()
