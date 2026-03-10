#!/usr/bin/env python3
import argparse
import json
import tempfile
from pathlib import Path

import gradio as gr

from attention import run_attention_pipeline
from modules.base import BASE_DIR

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
    <h1>先看图里最抓人的点，再给你一版文案草稿</h1>
    <p>上传图片后，它会先告诉你这张图最该从哪里写，再生成标题、正文和标签建议。你可以直接拿来改，不用从空白开始。</p>
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
  <h2 class="attention-section-title">它能帮你做什么</h2>
  <div class="attention-grid">
    <div class="attention-card">
      <h3>先解决“写什么”</h3>
      <p>不是每张图都该从整体开始写，很多时候真正该写的是一个小细节。</p>
    </div>
    <div class="attention-card">
      <h3>再解决“怎么写”</h3>
      <p>把这个点直接变成标题、正文和标签草稿，省掉从零开始写的时间。</p>
    </div>
    <div class="attention-card">
      <h3>尽量避免乱编</h3>
      <p>你可以补充真实信息，它不会硬编价格、品牌或教程细节。</p>
    </div>
  </div>
</div>
"""

FEATURE_HTML = """
<div class="attention-shell">
  <h2 class="attention-section-title">输出给你的是什么</h2>
  <div class="attention-grid">
    <div class="attention-card">
      <h3>识别最该写的点</h3>
      <p>先找出这张图里最容易让人停下来的那个点。</p>
    </div>
    <div class="attention-card">
      <h3>预测用户最想问什么</h3>
      <p>先找出“别人看到这张图最可能会问什么”。</p>
    </div>
    <div class="attention-card">
      <h3>生成可继续修改的表达</h3>
      <p>给你一版能直接继续改的标题、正文和标签草稿。</p>
    </div>
  </div>
</div>
"""

TRUST_HTML = """
<div class="attention-shell">
  <div class="attention-note">
    <p><strong>适合场景：</strong>日常发图、穿搭、美甲、饰品、探店、局部细节这类内容。</p>
  </div>
  <div class="attention-note">
    <p><strong>边界说明：</strong>它不会自动发内容，也不保证爆款；它做的是帮你更快找到切入点。</p>
  </div>
</div>
"""
def _load_public_example():
    with open(EXAMPLE_JSON_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def load_public_example():
    example_result = _load_public_example()
    return (
        example_result.get("markdown", ""),
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

    with tempfile.TemporaryDirectory(prefix="attention_upload_") as tmpdir:
        src_path = Path(image_path)
        tmp_photo = Path(tmpdir) / src_path.name
        tmp_photo.write_bytes(src_path.read_bytes())

        result = run_attention_pipeline(
            photos_dir=Path(tmpdir),
            provider=provider,
            api_key=api_key,
            tavily_api_key=tavily_api_key,
            include_viral_research=not skip_viral_research,
            extra_context=extra_context,
        )
    if result.status != "ok":
        if result.error:
            return result.error.message, result.model_dump(exclude_none=True), "执行失败。"
        return "执行失败。", result.model_dump(exclude_none=True), "执行失败。"

    payload = result.model_dump(exclude_none=True)
    status = "已完成图片分析和文案生成。"
    return result.markdown, payload, status


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
普通工具往往上来就开始写，`attention / 注意力` 会先帮你看图，再出文案。

**会不会乱编品牌、价格或教程细节？**  
不会。你没提供的信息，它不会硬写。

**适合什么内容？**  
适合穿搭、美甲、饰品、探店、局部细节、日常发图这类内容。
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
                    label="补充说明（可选）",
                    lines=4,
                    placeholder="例如：这是手工饰品，预算 99，拍摄地点在上海。",
                )
                with gr.Row():
                    run_btn = gr.Button("开始生成", variant="primary")
                    example_btn = gr.Button("查看示例结果")
            with gr.Column(scale=1):
                gr.Markdown("## 结果预览")
                status = gr.Textbox(
                    label="结果状态",
                    interactive=False,
                    value="上传图片后，会先告诉你这张图最该从哪里写，再给你一版文案草稿。",
                )
                md_output = gr.Markdown(value="### 等你上传一张图\n先找亮点，再看文案。")
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


def build_parser():
    parser = argparse.ArgumentParser(
        description="Launch the attention / 注意力 Web demo for desktop or mobile browsers."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="监听地址。局域网手机访问时可使用 0.0.0.0。",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Gradio 端口，默认 7860。",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="启用 Gradio 临时分享链接。",
    )
    parser.add_argument(
        "--inbrowser",
        action="store_true",
        help="启动后自动在默认浏览器中打开。",
    )
    return parser


def main():
    args = build_parser().parse_args()
    build_demo().launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        inbrowser=args.inbrowser,
        show_error=True,
        css=DEMO_CSS,
    )


if __name__ == "__main__":
    main()
