#!/usr/bin/env python3
import argparse
import html
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
  padding: 30px 30px 28px;
  border-radius: 22px;
  background:
    radial-gradient(circle at top right, rgba(121, 80, 242, 0.18), transparent 36%),
    linear-gradient(140deg, #fff8ef 0%, #ffffff 45%, #f6f2ff 100%);
  border: 1px solid rgba(137, 106, 255, 0.18);
  box-shadow: 0 22px 44px rgba(113, 83, 191, 0.08);
  margin-bottom: 28px;
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
  font-size: 42px;
  line-height: 1.12;
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
.attention-stepper {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 30px;
}
.attention-step {
  border-radius: 18px;
  border: 1px solid rgba(20, 20, 20, 0.08);
  background: rgba(255, 255, 255, 0.92);
  padding: 16px;
  box-shadow: 0 10px 24px rgba(20, 20, 20, 0.04);
}
.attention-step.is-active {
  border-color: rgba(247, 106, 0, 0.28);
  box-shadow: 0 14px 30px rgba(247, 106, 0, 0.08);
  background: linear-gradient(180deg, #fffaf4 0%, #ffffff 100%);
}
.attention-step.is-done {
  border-color: rgba(76, 47, 160, 0.16);
  background: linear-gradient(180deg, #faf7ff 0%, #ffffff 100%);
}
.attention-step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  background: rgba(20, 20, 20, 0.06);
  color: #1f1f1f;
  margin-bottom: 12px;
}
.attention-step.is-active .attention-step-index {
  background: #f76a00;
  color: #ffffff;
}
.attention-step.is-done .attention-step-index {
  background: #4c2fa0;
  color: #ffffff;
}
.attention-step-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 6px;
}
.attention-step-copy {
  font-size: 14px;
  line-height: 1.65;
  color: #4d4d4d;
}
.attention-section-title {
  margin: 0 0 8px;
  font-size: 28px;
}
.attention-subtitle {
  margin: 0 0 18px;
  font-size: 15px;
  line-height: 1.7;
  color: #555;
}
.attention-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 20px;
  align-items: start;
  margin-bottom: 28px;
}
.attention-panel {
  padding: 22px;
  border-radius: 22px;
  border: 1px solid rgba(20, 20, 20, 0.08);
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 16px 36px rgba(20, 20, 20, 0.05);
}
.attention-panel h3 {
  margin: 0 0 8px;
  font-size: 22px;
}
.attention-panel p {
  margin: 0;
  line-height: 1.65;
  font-size: 14px;
}
.attention-step-block {
  margin-top: 18px;
}
.attention-step-block:first-of-type {
  margin-top: 0;
}
.attention-step-label {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #6f6f6f;
  margin: 0 0 10px;
}
.attention-flow-note {
  margin: 0 0 14px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #fff7ee;
  border: 1px solid rgba(247, 106, 0, 0.14);
  color: #6b4a21;
  line-height: 1.7;
}
.attention-result-shell {
  margin-bottom: 24px;
}
.attention-result-card {
  padding: 24px;
  border-radius: 22px;
  border: 1px solid rgba(20, 20, 20, 0.08);
  background: linear-gradient(180deg, #ffffff 0%, #fffdf8 100%);
  box-shadow: 0 16px 36px rgba(20, 20, 20, 0.05);
}
.attention-result-card h3 {
  margin: 0 0 8px;
  font-size: 30px;
  line-height: 1.2;
}
.attention-result-card p {
  margin: 0;
  line-height: 1.75;
  color: #2f2f2f;
}
.attention-result-kicker {
  display: inline-block;
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7a5b1d;
  background: #fff5df;
  border-radius: 999px;
  padding: 7px 10px;
}
.attention-result-subhead {
  font-size: 14px;
  font-weight: 700;
  color: #6a6a6a;
  margin: 18px 0 8px;
}
.attention-result-list {
  margin: 0;
  padding-left: 18px;
  line-height: 1.75;
}
.attention-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}
.attention-tags span {
  border-radius: 999px;
  padding: 7px 10px;
  background: rgba(76, 47, 160, 0.08);
  color: #4c2fa0;
  font-size: 13px;
  font-weight: 600;
}
.attention-empty {
  padding: 20px;
  border-radius: 18px;
  background: #fafafa;
  border: 1px dashed rgba(20, 20, 20, 0.12);
  color: #616161;
  line-height: 1.7;
}
.attention-note {
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid rgba(20, 20, 20, 0.08);
  background: linear-gradient(180deg, #ffffff 0%, #fffaf2 100%);
  margin: 10px 0;
}
.attention-note p {
  margin: 0;
  line-height: 1.7;
}
.attention-example-panel {
  padding: 18px 20px;
  border-radius: 18px;
  border: 1px dashed rgba(20, 20, 20, 0.12);
  background: #fffdf8;
  margin: 22px 0 10px;
}
.attention-example-panel h3 {
  margin: 0 0 8px;
  font-size: 20px;
}
.attention-example-panel p {
  margin: 0 0 12px;
  line-height: 1.7;
  color: #4c4c4c;
}
@media (max-width: 900px) {
  .attention-stepper,
  .attention-workbench {
    grid-template-columns: 1fr;
  }
  .attention-hero h1 {
    font-size: 32px;
  }
  .attention-panel {
    padding: 18px;
  }
  .attention-result-card h3 {
    font-size: 24px;
  }
}
/* Force light theme globally */
.gradio-container, .gradio-container .contain, body,
.dark .gradio-container, .dark body {
  background: #fafafa !important;
  color: #1f1f1f !important;
}
.dark h1, .dark h2, .dark h3, .dark h4, .dark p, .dark span, .dark li, .dark label, .dark td, .dark th,
.gradio-container h1, .gradio-container h2, .gradio-container h3, .gradio-container h4,
.gradio-container p, .gradio-container span, .gradio-container li, .gradio-container label,
.gradio-container td, .gradio-container th,
.dark .prose *, .prose * {
  color: #1f1f1f !important;
}
.dark input, .dark textarea, .dark select,
input, textarea, select {
  background: #ffffff !important;
  color: #1f1f1f !important;
  border-color: rgba(20, 20, 20, 0.15) !important;
}
.dark .block, .block {
  background: #ffffff !important;
  border-color: rgba(20, 20, 20, 0.1) !important;
}
.dark button.primary, button.primary {
  color: #ffffff !important;
}
.dark .accordion, .accordion {
  background: #ffffff !important;
  color: #1f1f1f !important;
}
"""

HERO_HTML = """
<div class="attention-shell">
  <div class="attention-hero">
    <div class="attention-kicker">attention / 注意力</div>
    <h1>先看图里最抓人的点，再给你一版文案草稿</h1>
    <p>这不是从空白开始写文案，而是先帮你看图、找重点，再把结果整理成一版可以直接继续改的草稿。</p>
    <div class="attention-badges">
      <span>视觉切入</span>
      <span>问题提炼</span>
      <span>文案草案</span>
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

EXAMPLE_PANEL_HTML = """
<div class="attention-shell">
  <div class="attention-example-panel">
    <h3>想先看看结果长什么样？</h3>
    <p>你可以先载入一份公开示例，再决定是否上传自己的图片。示例只用于理解结果结构，不会覆盖你之后的真实生成。</p>
  </div>
</div>
"""


def render_stepper(current_step):
    steps = [
        ("1", "上传图片", "先选一张你想写的图。"),
        ("2", "填写 API Key", "上传完成后再填写。"),
        ("3", "开始生成", "准备好后点击主按钮。"),
        ("4", "查看最佳文案", "先看最推荐的一版。"),
    ]
    cards = []
    for index, title, copy in steps:
        step_number = int(index)
        state_class = ""
        if step_number < current_step:
            state_class = " is-done"
        elif step_number == current_step:
            state_class = " is-active"
        cards.append(
            f"""
            <div class="attention-step{state_class}">
              <div class="attention-step-index">{html.escape(index)}</div>
              <div class="attention-step-title">{html.escape(title)}</div>
              <div class="attention-step-copy">{html.escape(copy)}</div>
            </div>
            """
        )
    return f'<div class="attention-shell"><div class="attention-stepper">{"".join(cards)}</div></div>'


def _format_tags(tag_text):
    tags = [item.strip() for item in str(tag_text or "").split() if item.strip()]
    if not tags:
        return ""
    return "".join(f"<span>{html.escape(tag)}</span>" for tag in tags)


def render_best_copy_html(payload):
    best_copy = (payload or {}).get("best_copy") or {}
    title_a = str(best_copy.get("title_a", "")).strip()
    title_b = str(best_copy.get("title_b", "")).strip()
    content = str(best_copy.get("content", "")).strip()
    tags_html = _format_tags(best_copy.get("tags", ""))

    if not (title_a or title_b or content):
        return """
        <div class="attention-result-card">
          <div class="attention-result-kicker">步骤 4</div>
          <h3>最佳文案</h3>
          <div class="attention-empty">生成完成后，这里会先出现一版最值得直接修改的文案。</div>
        </div>
        """

    title_items = []
    if title_a:
        title_items.append(f"<li>{html.escape(title_a)}</li>")
    if title_b:
        title_items.append(f"<li>{html.escape(title_b)}</li>")
    titles_html = "".join(title_items) or "<li>暂无标题建议</li>"
    content_html = html.escape(content).replace("\n", "<br>")

    return f"""
    <div class="attention-result-card">
      <div class="attention-result-kicker">步骤 4</div>
      <h3>最佳文案</h3>
      <div class="attention-result-subhead">标题建议</div>
      <ul class="attention-result-list">{titles_html}</ul>
      <div class="attention-result-subhead">正文草稿</div>
      <p>{content_html}</p>
      <div class="attention-result-subhead">标签建议</div>
      <div class="attention-tags">{tags_html or "<span>暂无标签</span>"}</div>
    </div>
    """


def render_insight_markdown(payload):
    intent = (payload or {}).get("intent") or {}
    why_it_works = str((payload or {}).get("why_it_works", "")).strip()
    if not intent:
        return "暂无切入点分析。"

    lines = [
        "### 这张图的切入点",
        f"- 图里最抓人的点：{intent.get('hero_element', '未识别')}",
        f"- 别人最想问的话：{intent.get('viewer_question', '未识别')}",
    ]
    if why_it_works:
        lines.append(f"- 为什么这样写：{why_it_works}")
    mood = str(intent.get("mood", "")).strip()
    if mood:
        lines.append(f"- 画面感觉：{mood}")
    return "\n".join(lines)


def render_candidates_markdown(payload):
    candidates = list((payload or {}).get("copy_candidates") or [])
    if not candidates:
        return "暂无候选文案。"
    if len(candidates) == 1:
        return "当前只有 1 版结果，你可以直接从上面的最佳文案继续改。"

    lines = ["### 其他候选文案"]
    for index, candidate in enumerate(candidates[1:], start=2):
        lines.extend(
            [
                f"#### 文案 {index}",
                f"- 标题 A：{candidate.get('title_a', '') or '暂无'}",
                f"- 标题 B：{candidate.get('title_b', '') or '暂无'}",
                f"- 标签：{candidate.get('tags', '') or '暂无'}",
                "",
                candidate.get("content", "").strip() or "暂无正文",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _current_step(image_path=None, api_key="", has_result=False):
    if has_result:
        return 4
    if image_path and str(api_key or "").strip():
        return 3
    if image_path:
        return 2
    return 1


def _flow_hint(image_path=None, api_key=""):
    if not image_path:
        return "先上传一张图片，我们会按步骤带你走完。"
    if not str(api_key or "").strip():
        return "图片已准备好，下一步填写你的 API Key。"
    return "现在可以点击开始生成。"


def _empty_result_outputs():
    return (
        gr.update(visible=False),
        "",
        render_best_copy_html({}),
        "",
        "",
        None,
    )


def update_flow(image_path, api_key):
    image_ready = bool(image_path)
    key_ready = bool(str(api_key or "").strip())
    return (
        render_stepper(_current_step(image_path=image_path, api_key=api_key)),
        gr.update(visible=image_ready),
        _flow_hint(image_path=image_path, api_key=api_key),
        gr.update(interactive=image_ready and key_ready),
        *_empty_result_outputs(),
    )


def _result_outputs_from_payload(payload, notice):
    return (
        gr.update(visible=True),
        notice,
        render_best_copy_html(payload),
        render_insight_markdown(payload),
        render_candidates_markdown(payload),
        payload,
    )


def _load_public_example():
    with open(EXAMPLE_JSON_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def load_public_example(image_path, api_key):
    example_result = _load_public_example()
    return (
        render_stepper(_current_step(image_path=image_path, api_key=api_key)),
        *_result_outputs_from_payload(
            example_result,
            "已加载公开示例结果。当前展示的是示例，不是你刚上传的图片。",
        ),
    )


def run_attention(
    image_path,
    provider,
    api_key,
    extra_context,
):
    if not image_path:
        return (
            render_stepper(_current_step(image_path=image_path, api_key=api_key)),
            gr.update(visible=True),
            "请先上传一张图片。",
            render_best_copy_html({}),
            "",
            "",
            None,
        )

    with tempfile.TemporaryDirectory(prefix="attention_upload_") as tmpdir:
        src_path = Path(image_path)
        tmp_photo = Path(tmpdir) / src_path.name
        tmp_photo.write_bytes(src_path.read_bytes())

        result = run_attention_pipeline(
            photos_dir=Path(tmpdir),
            provider=provider,
            api_key=api_key,
            include_viral_research=True,
            extra_context=extra_context,
        )
    if result.status != "ok":
        if result.error:
            return (
                render_stepper(_current_step(image_path=image_path, api_key=api_key)),
                gr.update(visible=True),
                f"生成失败：{result.error.message}",
                render_best_copy_html({}),
                "",
                "",
                result.model_dump(exclude_none=True),
            )
        return (
            render_stepper(_current_step(image_path=image_path, api_key=api_key)),
            gr.update(visible=True),
            "生成失败，请稍后重试。",
            render_best_copy_html({}),
            "",
            "",
            result.model_dump(exclude_none=True),
        )

    payload = result.model_dump(exclude_none=True)
    return (
        render_stepper(_current_step(image_path=image_path, api_key=api_key, has_result=True)),
        *_result_outputs_from_payload(
            payload,
            "已完成生成。先看上面的最佳文案，如果方向对，再展开下面的说明继续修改。",
        ),
    )


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

    with gr.Blocks(title="attention / 注意力", theme=gr.themes.Default(), css=DEMO_CSS) as demo:
        gr.HTML(HERO_HTML)
        stepper = gr.HTML(render_stepper(1))
        with gr.Row(elem_classes="attention-workbench"):
            with gr.Column(scale=7, elem_classes="attention-panel"):
                gr.Markdown("## 步骤 1：上传你的图片")
                gr.Markdown(
                    "先上传一张你想写的图片。上传后，我们再带你填写 key 并生成结果。",
                    elem_classes="attention-subtitle",
                )
                image_input = gr.Image(type="filepath", label="图片")
            with gr.Column(scale=5, visible=False, elem_classes="attention-panel") as setup_panel:
                gr.Markdown("## 步骤 2：填写你的 API Key")
                flow_hint = gr.Markdown(
                    _flow_hint(),
                    elem_classes="attention-flow-note",
                )
                provider = gr.Dropdown(
                    choices=["gemini", "minimax", "auto"],
                    value="gemini",
                    label="模型",
                )
                api_key = gr.Textbox(
                    value="",
                    label="你的 API Key",
                    type="password",
                    placeholder="只在这次使用，不会保存",
                )
                with gr.Accordion("补充说明（可选）", open=False):
                    extra_context = gr.Textbox(
                        value="",
                        label="补充说明",
                        lines=4,
                        placeholder="例如：这是手工饰品，预算 99，拍摄地点在上海。",
                    )
                gr.Markdown("## 步骤 3：开始生成", elem_classes="attention-step-block")
                run_btn = gr.Button("开始生成", variant="primary", interactive=False)

        with gr.Column(visible=False, elem_classes="attention-result-shell") as result_section:
            gr.Markdown("## 步骤 4：查看最佳文案")
            result_notice = gr.Markdown("", elem_classes="attention-flow-note")
            best_copy_output = gr.HTML(render_best_copy_html({}))
            with gr.Accordion("这张图的切入点", open=False):
                insight_output = gr.Markdown("")
            with gr.Accordion("候选文案", open=False):
                candidates_output = gr.Markdown("")
            with gr.Accordion("开发者查看：详细数据", open=False):
                json_output = gr.JSON(label="调试数据 JSON", value=None)

        gr.HTML(TRUST_HTML)

        gr.HTML(EXAMPLE_PANEL_HTML)
        example_btn = gr.Button("查看公开示例")

        with gr.Accordion("查看示例结果拆解", open=False):
            gr.Markdown(example_story)

        with gr.Accordion("FAQ", open=False):
            gr.Markdown(faq_markdown)

        image_input.change(
            fn=update_flow,
            inputs=[image_input, api_key],
            outputs=[
                stepper,
                setup_panel,
                flow_hint,
                run_btn,
                result_section,
                result_notice,
                best_copy_output,
                insight_output,
                candidates_output,
                json_output,
            ],
        )
        api_key.change(
            fn=update_flow,
            inputs=[image_input, api_key],
            outputs=[
                stepper,
                setup_panel,
                flow_hint,
                run_btn,
                result_section,
                result_notice,
                best_copy_output,
                insight_output,
                candidates_output,
                json_output,
            ],
        )
        run_btn.click(
            fn=run_attention,
            inputs=[
                image_input,
                provider,
                api_key,
                extra_context,
            ],
            outputs=[
                stepper,
                result_section,
                result_notice,
                best_copy_output,
                insight_output,
                candidates_output,
                json_output,
            ],
        )
        example_btn.click(
            fn=load_public_example,
            inputs=[image_input, api_key],
            outputs=[
                stepper,
                result_section,
                result_notice,
                best_copy_output,
                insight_output,
                candidates_output,
                json_output,
            ],
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
    )


if __name__ == "__main__":
    main()
