#!/usr/bin/env python3
import json
import shutil
import tempfile
from pathlib import Path

import gradio as gr

from main import build_attention_result, ensure_config, render_markdown, write_outputs
from modules import context_loader, copywriter, photo_tagger
from modules.base import BASE_DIR, set_runtime_options

EXAMPLE_JSON_PATH = BASE_DIR / "examples" / "attention_sample.json"

DEMO_CSS = """
.attention-shell {
  max-width: 1120px;
  margin: 0 auto;
}
.attention-hero {
  padding: 28px;
  border-radius: 22px;
  background:
    radial-gradient(circle at top right, rgba(121, 80, 242, 0.18), transparent 36%),
    linear-gradient(140deg, #fff8ef 0%, #ffffff 45%, #f6f2ff 100%);
  border: 1px solid rgba(137, 106, 255, 0.18);
  box-shadow: 0 22px 44px rgba(113, 83, 191, 0.08);
  margin-bottom: 18px;
}
.attention-kicker {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(137, 106, 255, 0.16);
}
.attention-hero h1 {
  font-size: 40px;
  line-height: 1.15;
  margin: 14px 0 12px;
}
.attention-hero p {
  font-size: 16px;
  line-height: 1.7;
  margin: 0;
  max-width: 760px;
}
.attention-badges {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 16px;
}
.attention-badges span {
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(76, 47, 160, 0.08);
  color: #4c2fa0;
  font-size: 13px;
  font-weight: 600;
}
.attention-section-title {
  margin: 14px 0 6px;
  font-size: 24px;
}
.attention-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin: 16px 0 8px;
}
.attention-card {
  padding: 18px;
  border-radius: 18px;
  border: 1px solid rgba(20, 20, 20, 0.08);
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 10px 24px rgba(20, 20, 20, 0.04);
}
.attention-card h3 {
  margin: 0 0 8px;
  font-size: 18px;
}
.attention-card p {
  margin: 0;
  line-height: 1.65;
  font-size: 14px;
}
.attention-note {
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid rgba(20, 20, 20, 0.08);
  background: linear-gradient(180deg, #ffffff 0%, #fffaf2 100%);
  margin: 12px 0;
}
.attention-note p {
  margin: 0;
  line-height: 1.7;
}
@media (max-width: 900px) {
  .attention-grid {
    grid-template-columns: 1fr;
  }
  .attention-hero h1 {
    font-size: 30px;
  }
}
"""

HERO_HTML = """
<div class="attention-shell">
  <div class="attention-hero">
    <div class="attention-kicker">attention / 注意力</div>
    <h1>先找出图里最值得展开的意图，再把它整理成清晰的图文草案</h1>
    <p>上传一张图，识别视觉主角和用户最想追问的那一句话，再生成标题、正文和标签建议。不是堆文案技巧，而是先把真正会让人停下来的那个点找准、写清楚。</p>
    <div class="attention-badges">
      <span>视觉切入</span>
      <span>问题提炼</span>
      <span>文案草案</span>
    </div>
  </div>
</div>
"""

VALUE_HTML = """
<div class="attention-shell">
  <h2 class="attention-section-title">为什么它不像普通文案工具</h2>
  <div class="attention-grid">
    <div class="attention-card">
      <h3>先解决“写什么”</h3>
      <p>不是每张图都该从整体开始写，真正值得展开的，常常是一个细节、反差或追问点。</p>
    </div>
    <div class="attention-card">
      <h3>再解决“怎么写”</h3>
      <p>把这个点转成更清晰的标题、正文和标签草案，而不是堆模板句式。</p>
    </div>
    <div class="attention-card">
      <h3>尽量避免乱编</h3>
      <p>你可以补充真实信息，工具只负责放大亮点，不负责凭空补价格、品牌或教程细节。</p>
    </div>
  </div>
</div>
"""

FEATURE_HTML = """
<div class="attention-shell">
  <h2 class="attention-section-title">它具体会帮你做什么</h2>
  <div class="attention-grid">
    <div class="attention-card">
      <h3>识别最该写的点</h3>
      <p>从图片里找出最先抓住注意力的视觉主角，而不是泛泛描述“这张图很好看”。</p>
    </div>
    <div class="attention-card">
      <h3>预测用户最想问什么</h3>
      <p>把“看到这张图的人第一句会问什么”先找出来，文案开头就更容易抓住人。</p>
    </div>
    <div class="attention-card">
      <h3>生成可继续修改的表达</h3>
      <p>输出标题、正文和标签建议，让你更快得到一个结构清晰的图文初稿，而不是模板化营销稿。</p>
    </div>
  </div>
</div>
"""

TRUST_HTML = """
<div class="attention-shell">
  <div class="attention-note">
    <p><strong>适合场景：</strong>个人账号、日常发图、穿搭、美甲、饰品、探店、局部细节这类需要“先抓注意力再展开”的内容。</p>
  </div>
  <div class="attention-note">
    <p><strong>边界说明：</strong>它不是自动发布工具，也不承诺爆款；它的价值是帮你先找到那个真正值得展开的切入点。</p>
  </div>
</div>
"""


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


def _load_public_example():
    with open(EXAMPLE_JSON_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def load_public_example():
    example_result = _load_public_example()
    return (
        render_markdown(example_result),
        example_result,
        "已加载公开示例：先由细节建立切入点，再展开成完整图文。",
    )


def run_attention(
    image_path,
    provider,
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
        )
        if photo_result.get("total_photos", 0) == 0:
            return "未检测到可分析图片。", None, "执行失败。"
        if photo_result.get("error"):
            return photo_result["error"], None, "视觉分析失败。"

        notes_result = copywriter.run(
            photo_data=photo_result,
            context_info=context_prompt,
            provider=provider,
        )
        if notes_result.get("error"):
            return notes_result["error"], None, "文案生成失败。"
        if notes_result.get("total", 0) == 0:
            return "文案生成失败，请更换图片或模型参数。", None, "执行失败。"

    run_result = build_attention_result(
        photo_result=photo_result,
        notes_result=notes_result,
        context_loaded=context_data,
        provider=provider,
    )
    _, md_path = write_outputs(run_result, BASE_DIR / "output")
    markdown = render_markdown(run_result)
    status = f"已生成并写入：{md_path}"
    return markdown, run_result, status


def build_demo():
    example_result = _load_public_example()
    example_story = """
### 公开示例拆解
1. 原图：局部细节穿搭照，第一眼会先停在无名指上的蜘蛛装饰。
2. 视觉主角：蜘蛛装饰美甲
3. 用户最想问：这个蜘蛛装饰美甲是怎么做出来的？
4. 为什么这个角度成立：它不是泛泛写整套穿搭，而是先用一个反差细节把人停住。
5. 生成文案：把“先被细节吸走，再顺着气氛看完整张图”的过程写出来，形成更自然的图文展开。
"""

    faq_markdown = """
### FAQ
**它和普通 AI 文案工具有什么区别？**  
普通工具通常从空白开始写，`attention / 注意力` 会先从图片里找到最值得展开的那个点，再把它整理成更清晰的图文草案。

**会不会乱编品牌、价格或教程细节？**  
不会。你可以补充真实上下文，但如果没有明确提供，它会尽量只放大图中能支撑的亮点。

**适合什么内容？**  
尤其适合穿搭、美甲、饰品、探店、局部细节、日常发图这类需要“先抓眼再展开”的内容。
"""

    with gr.Blocks(title="attention / 注意力") as demo:
        gr.HTML(HERO_HTML)
        gr.HTML(VALUE_HTML)
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 上传图片")
                image_input = gr.Image(type="filepath", label="上传原图")
                provider = gr.Dropdown(
                    choices=["gemini", "minimax", "auto"],
                    value="gemini",
                    label="Provider",
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
                with gr.Row():
                    run_btn = gr.Button("上传图片，生成图文草案", variant="primary")
                    example_btn = gr.Button("查看示例结果")
            with gr.Column(scale=1):
                gr.Markdown("## 结果预览")
                status = gr.Textbox(
                    label="结果状态",
                    interactive=False,
                    value="上传图片后，我们会先告诉你什么最值得展开，再给出一份清晰的图文草案。",
                )
                md_output = gr.Markdown(value="### 等你上传一张图\n先看视觉主角，再看用户最想问的那一句。")
                json_output = gr.JSON(label="结构化结果", value=example_result)

        gr.HTML(FEATURE_HTML)
        gr.HTML(TRUST_HTML)

        with gr.Accordion("查看示例结果拆解", open=False):
            gr.Markdown(example_story)

        with gr.Accordion("FAQ", open=False):
            gr.Markdown(faq_markdown)

        run_btn.click(
            fn=run_attention,
            inputs=[
                image_input,
                provider,
                api_key,
                tavily_key,
                skip_viral,
                extra_context,
            ],
            outputs=[md_output, json_output, status],
        )
        example_btn.click(
            fn=load_public_example,
            inputs=[],
            outputs=[md_output, json_output, status],
        )
    return demo


if __name__ == "__main__":
    build_demo().launch(css=DEMO_CSS)
