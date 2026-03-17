#!/usr/bin/env python3
"""attention / 注意力 — 九宫格选图引擎 Web UI"""

import argparse
import html
import json
import logging
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger("attention.app")

import gradio as gr

from attention import run_attention_pipeline
from attention.grid_render import render_grid_png
from modules.base import BASE_DIR

EXAMPLE_JSON_PATH = BASE_DIR / "examples" / "attention_sample.json"

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

DEMO_CSS = """
.attention-shell { max-width: 1120px; margin: 0 auto; }

/* Hero */
.attention-hero {
  padding: 30px 30px 28px; border-radius: 22px;
  background: radial-gradient(circle at top right, rgba(121,80,242,0.18), transparent 36%),
    linear-gradient(140deg, #fff8ef 0%, #ffffff 45%, #f6f2ff 100%);
  border: 1px solid rgba(137,106,255,0.18);
  box-shadow: 0 22px 44px rgba(113,83,191,0.08);
  margin-bottom: 28px;
}
.attention-kicker {
  display: inline-block; font-size: 12px; letter-spacing: 0.08em;
  text-transform: uppercase; padding: 6px 10px; border-radius: 999px;
  background: rgba(255,255,255,0.9); border: 1px solid rgba(137,106,255,0.16);
}
.attention-hero h1 { font-size: 38px; line-height: 1.15; margin: 14px 0 12px; }
.attention-hero p { font-size: 16px; line-height: 1.7; margin: 0; max-width: 760px; }
.attention-badges { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }
.attention-badges span {
  padding: 7px 12px; border-radius: 999px;
  background: rgba(76,47,160,0.08); color: #4c2fa0;
  font-size: 13px; font-weight: 600;
}

/* Panels */
.attention-panel {
  padding: 22px; border-radius: 22px;
  border: 1px solid rgba(20,20,20,0.08);
  background: rgba(255,255,255,0.95);
  box-shadow: 0 16px 36px rgba(20,20,20,0.05);
}
.attention-panel h3 { margin: 0 0 8px; font-size: 22px; }
.attention-panel p { margin: 0; line-height: 1.65; font-size: 14px; }
.attention-subtitle { margin: 0 0 18px; font-size: 15px; line-height: 1.7; color: #555; }
.attention-flow-note {
  margin: 0 0 14px; padding: 12px 14px; border-radius: 14px;
  background: #fff7ee; border: 1px solid rgba(247,106,0,0.14);
  color: #6b4a21; line-height: 1.7;
}

/* 9-Grid Visual */
.attention-grid-preview {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  margin: 16px 0;
  max-width: 480px;
}
.attention-grid-cell {
  aspect-ratio: 3/4;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
  background: #f0f0f0;
  border: 2px solid transparent;
}
.attention-grid-cell.is-cover {
  border-color: #f76a00;
  box-shadow: 0 0 0 2px rgba(247,106,0,0.3);
}
.attention-grid-cell img {
  width: 100%; height: 100%; object-fit: cover;
}
.attention-grid-badge {
  position: absolute; top: 4px; left: 4px;
  padding: 2px 6px; border-radius: 4px;
  font-size: 11px; font-weight: 700; color: #fff;
  background: rgba(0,0,0,0.55);
}
.attention-grid-cell.is-cover .attention-grid-badge {
  background: #f76a00;
}
.attention-grid-role {
  position: absolute; bottom: 0; left: 0; right: 0;
  padding: 3px 6px; font-size: 10px; color: #fff;
  background: linear-gradient(transparent, rgba(0,0,0,0.6));
  text-align: center;
}
.attention-grid-score {
  position: absolute; top: 4px; right: 4px;
  padding: 2px 5px; border-radius: 4px;
  font-size: 10px; font-weight: 600; color: #fff;
  background: rgba(76,47,160,0.7);
}

/* Result card */
.attention-result-card {
  padding: 24px; border-radius: 22px;
  border: 1px solid rgba(20,20,20,0.08);
  background: linear-gradient(180deg, #ffffff 0%, #fffdf8 100%);
  box-shadow: 0 16px 36px rgba(20,20,20,0.05);
}
.attention-result-card h3 { margin: 0 0 8px; font-size: 28px; line-height: 1.2; }
.attention-result-card p { margin: 0; line-height: 1.75; color: #2f2f2f; }
.attention-result-kicker {
  display: inline-block; margin-bottom: 12px; font-size: 12px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase; color: #7a5b1d;
  background: #fff5df; border-radius: 999px; padding: 7px 10px;
}
.attention-result-subhead { font-size: 14px; font-weight: 700; color: #6a6a6a; margin: 18px 0 8px; }
.attention-result-list { margin: 0; padding-left: 18px; line-height: 1.75; }
.attention-tags { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.attention-tags span {
  border-radius: 999px; padding: 7px 10px;
  background: rgba(76,47,160,0.08); color: #4c2fa0;
  font-size: 13px; font-weight: 600;
}

/* Excluded table */
.attention-excluded-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
.attention-excluded-table th { text-align: left; padding: 6px 8px; border-bottom: 2px solid #e0e0e0; color: #666; }
.attention-excluded-table td { padding: 6px 8px; border-bottom: 1px solid #f0f0f0; }

/* Narrative bar */
.attention-narrative {
  padding: 14px 18px; border-radius: 14px; margin: 12px 0;
  background: linear-gradient(90deg, #f6f2ff, #fff8ef);
  border: 1px solid rgba(137,106,255,0.12);
  font-size: 14px; line-height: 1.7; color: #3d3066;
}

/* Force light theme */
.gradio-container, .gradio-container .contain, body,
.dark .gradio-container, .dark body {
  background: #fafafa !important; color: #1f1f1f !important;
}
.dark h1,.dark h2,.dark h3,.dark h4,.dark p,.dark span,.dark li,.dark label,.dark td,.dark th,
.gradio-container h1,.gradio-container h2,.gradio-container h3,.gradio-container h4,
.gradio-container p,.gradio-container span,.gradio-container li,.gradio-container label,
.gradio-container td,.gradio-container th, .dark .prose *, .prose * {
  color: #1f1f1f !important;
}
.dark input,.dark textarea,.dark select, input,textarea,select {
  background: #ffffff !important; color: #1f1f1f !important;
  border-color: rgba(20,20,20,0.15) !important;
}
.dark .block,.block { background: #ffffff !important; border-color: rgba(20,20,20,0.1) !important; }
.dark button.primary,button.primary { color: #ffffff !important; }
.dark .accordion,.accordion { background: #ffffff !important; color: #1f1f1f !important; }

@media (max-width: 900px) {
  .attention-hero h1 { font-size: 28px; }
  .attention-grid-preview { max-width: 100%; }
  .attention-panel { padding: 16px; }
}
"""

# ---------------------------------------------------------------------------
# Static HTML
# ---------------------------------------------------------------------------

HERO_HTML = """
<div class="attention-shell">
  <div class="attention-hero">
    <div class="attention-kicker">attention / 注意力</div>
    <h1>扔一堆图进来，帮你选出最强九宫格</h1>
    <p>从 15-50 张图里自动选出最强 9 张、排好封面和顺序、写出整组文案。三步搞定小红书发图。</p>
    <div class="attention-badges">
      <span>AI 选图</span>
      <span>封面推荐</span>
      <span>九宫格编排</span>
      <span>整组文案</span>
    </div>
  </div>
</div>
"""

# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def _format_tags(tag_text):
    tags = [t.strip() for t in str(tag_text or "").split() if t.strip()]
    if not tags:
        return ""
    return "".join(f"<span>{html.escape(t)}</span>" for t in tags)


def render_grid_html(payload):
    """Render 9-grid visual preview from pipeline result."""
    grid = (payload or {}).get("grid")
    if not grid or not grid.get("slots"):
        return '<div class="attention-flow-note">九宫格预览将在生成后出现。</div>'

    slots = grid["slots"]
    # Map filename to uploaded image path for display
    image_map = {}
    meta = (payload or {}).get("meta", {})
    source_images = meta.get("source_images", [])
    upload_dir = payload.get("_upload_dir", "")

    narrative = grid.get("grid_narrative", "")
    narrative_html = ""
    if narrative:
        narrative_html = f'<div class="attention-narrative">{html.escape(narrative)}</div>'

    cells = []
    for slot in slots:
        pos = slot.get("position", 0)
        fname = slot.get("filename", "")
        role = slot.get("role", "")
        score = slot.get("composite_score", 0)
        is_cover = pos == 1
        cover_cls = " is-cover" if is_cover else ""

        # Try to find actual image file
        img_html = ""
        if upload_dir and fname:
            img_path = Path(upload_dir) / fname
            if img_path.exists():
                img_html = f'<img src="file={img_path}" alt="{html.escape(fname)}">'

        badge_text = "封面" if is_cover else str(pos)

        cells.append(f"""
        <div class="attention-grid-cell{cover_cls}">
          {img_html}
          <div class="attention-grid-badge">{badge_text}</div>
          <div class="attention-grid-score">{score:.1f}</div>
          <div class="attention-grid-role">{html.escape(role)}</div>
        </div>
        """)

    # Pad to 9 if less
    while len(cells) < 9:
        cells.append('<div class="attention-grid-cell"><div class="attention-grid-badge">-</div></div>')

    grid_html = '<div class="attention-grid-preview">' + "".join(cells[:9]) + "</div>"

    # Cover alternatives
    alt_html = ""
    alts = grid.get("cover_alternatives", [])
    if alts:
        alt_names = ", ".join(a.get("filename", "?") for a in alts)
        alt_html = f'<p style="font-size:13px;color:#666;margin-top:8px;">封面备选：{html.escape(alt_names)}</p>'

    return f"""
    <div>
      <h3 style="margin:0 0 8px;">九宫格编排</h3>
      {narrative_html}
      {grid_html}
      {alt_html}
    </div>
    """


def render_excluded_html(payload):
    """Render excluded images table."""
    grid = (payload or {}).get("grid")
    if not grid:
        return ""
    excluded = grid.get("excluded", [])
    if not excluded:
        return "<p>全部图片都被选入九宫格。</p>"

    rows = []
    for ex in excluded:
        fname = html.escape(ex.get("filename", "?"))
        score = ex.get("composite_score", 0)
        reason = html.escape(ex.get("exclude_reason", ""))
        rows.append(f"<tr><td>{fname}</td><td>{score:.1f}</td><td>{reason}</td></tr>")

    return f"""
    <table class="attention-excluded-table">
      <thead><tr><th>文件</th><th>综合分</th><th>淘汰原因</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
    """


def render_best_copy_html(payload):
    best_copy = (payload or {}).get("best_copy") or {}
    title_a = str(best_copy.get("title_a", "")).strip()
    title_b = str(best_copy.get("title_b", "")).strip()
    content = str(best_copy.get("content", "")).strip()
    flip_guide = str(best_copy.get("flip_guide", "")).strip()
    tags_html = _format_tags(best_copy.get("tags", ""))

    if not (title_a or title_b or content):
        return """
        <div class="attention-result-card">
          <div class="attention-result-kicker">整组文案</div>
          <h3>文案结果</h3>
          <div style="padding:20px;border-radius:18px;background:#fafafa;border:1px dashed rgba(20,20,20,0.12);color:#616161;line-height:1.7;">
            生成完成后，这里会出现基于九宫格编排的整组文案。
          </div>
        </div>
        """

    title_items = []
    if title_a:
        title_items.append(f"<li>{html.escape(title_a)}</li>")
    if title_b:
        title_items.append(f"<li>{html.escape(title_b)}</li>")
    titles_html = "".join(title_items) or "<li>暂无标题建议</li>"
    content_html = html.escape(content).replace("\n", "<br>")

    flip_html = ""
    if flip_guide:
        flip_html = f'<div class="attention-result-subhead">翻页引导</div><p>{html.escape(flip_guide)}</p>'

    return f"""
    <div class="attention-result-card">
      <div class="attention-result-kicker">整组文案</div>
      <h3>文案结果</h3>
      <div class="attention-result-subhead">标题建议</div>
      <ul class="attention-result-list">{titles_html}</ul>
      <div class="attention-result-subhead">正文草稿</div>
      <p>{content_html}</p>
      {flip_html}
      <div class="attention-result-subhead">标签建议</div>
      <div class="attention-tags">{tags_html or "<span>暂无标签</span>"}</div>
    </div>
    """


def render_insight_markdown(payload):
    intent = (payload or {}).get("intent") or {}
    why = str((payload or {}).get("why_it_works", "")).strip()
    grid = (payload or {}).get("grid") or {}

    if not intent:
        return "暂无分析。"

    lines = [
        "### 封面图分析",
        f"- 视觉主角：{intent.get('hero_element', '未识别')}",
        f"- 用户最想问：{intent.get('viewer_question', '未识别')}",
    ]
    if why:
        lines.append(f"- 叙事线：{why}")
    mood = str(intent.get("mood", "")).strip()
    if mood:
        lines.append(f"- 画面氛围：{mood}")

    meta = (payload or {}).get("meta", {})
    analyzed = meta.get("photos_analyzed")
    source = meta.get("source_images", [])
    if analyzed is not None:
        lines.append(f"- 分析了 {analyzed} 张图，来源 {len(source)} 张")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_attention(images, extra_context, progress=gr.Progress()):
    """Run the full pipeline with multiple uploaded images."""
    if not images:
        return (
            None,
            '<div class="attention-flow-note">请先上传图片。</div>',
            render_best_copy_html({}),
            "",
            "",
            "",
            None,
        )

    progress(0.1, desc="准备图片...")

    # Copy uploaded images into a temp directory
    tmpdir = tempfile.mkdtemp(prefix="attention_grid_")
    for img_path in images:
        src = Path(img_path)
        dst = Path(tmpdir) / src.name
        # Handle duplicate filenames
        counter = 1
        while dst.exists():
            dst = Path(tmpdir) / f"{src.stem}_{counter}{src.suffix}"
            counter += 1
        shutil.copy2(src, dst)

    photo_count = len(list(Path(tmpdir).iterdir()))
    progress(0.2, desc=f"分析 {photo_count} 张图片...")

    result = run_attention_pipeline(
        photos_dir=tmpdir,
        provider="auto",
        api_key="",
        include_viral_research=True,
        extra_context=extra_context,
    )

    if result.status != "ok":
        err_msg = result.error.message if result.error else "生成失败，请稍后重试。"
        return (
            None,
            f'<div class="attention-flow-note" style="background:#fff0f0;border-color:rgba(220,38,38,0.2);color:#991b1b;">{html.escape(err_msg)}</div>',
            render_best_copy_html({}),
            "",
            "",
            "",
            result.model_dump(exclude_none=True),
        )

    progress(0.9, desc="渲染结果...")
    payload = result.model_dump(exclude_none=True)
    payload["_upload_dir"] = tmpdir  # for grid image preview

    # Render actual grid PNG
    grid_image = None
    grid_slots = payload.get("grid", {}).get("slots", [])
    if grid_slots:
        try:
            grid_image = render_grid_png(slots=grid_slots, photos_dir=tmpdir)
        except Exception as e:
            logger.warning("Grid PNG render failed: %s", e)

    selected_count = len(grid_slots)
    return (
        grid_image,
        render_grid_html(payload),
        render_best_copy_html(payload),
        render_insight_markdown(payload),
        render_excluded_html(payload),
        f"已完成：从 {photo_count} 张图中选出 {selected_count} 张，编排九宫格并生成文案。",
        payload,
    )


# ---------------------------------------------------------------------------
# Gradio App
# ---------------------------------------------------------------------------

def build_demo():
    with gr.Blocks(
        title="attention / 注意力 — 九宫格选图引擎",
    ) as demo:
        gr.HTML(HERO_HTML)

        with gr.Row():
            # Left: Upload + Config
            with gr.Column(scale=6, elem_classes="attention-panel"):
                gr.Markdown("### 上传图片")
                gr.Markdown("拖入 15-50 张图片（一次拍摄/旅行/选品），支持 jpg/png/webp。", elem_classes="attention-subtitle")
                image_input = gr.File(
                    file_count="multiple",
                    file_types=["image"],
                    label="选择图片",
                    type="filepath",
                )
                with gr.Accordion("补充说明（可选）", open=False):
                    extra_context = gr.Textbox(
                        value="",
                        label="补充说明",
                        lines=3,
                        placeholder="例如：这是上海某咖啡店探店，人均 45 元。",
                    )
                run_btn = gr.Button("开始选图 + 生成文案", variant="primary", size="lg")

            # Right: Grid preview
            with gr.Column(scale=6, elem_classes="attention-panel"):
                grid_image_output = gr.Image(
                    label="九宫格预览（可直接下载）",
                    type="pil",
                    show_download_button=True,
                    interactive=False,
                )
                grid_output = gr.HTML(
                    '<div class="attention-flow-note">九宫格预览将在生成后出现。</div>'
                )

        # Results section
        status_bar = gr.Markdown("", visible=True)

        best_copy_output = gr.HTML(render_best_copy_html({}))

        with gr.Row():
            with gr.Column():
                with gr.Accordion("封面图分析", open=False):
                    insight_output = gr.Markdown("")
                with gr.Accordion("被淘汰的图片", open=False):
                    excluded_output = gr.HTML("")
                with gr.Accordion("开发者：详细数据", open=False):
                    json_output = gr.JSON(label="调试 JSON", value=None)

        run_btn.click(
            fn=run_attention,
            inputs=[image_input, extra_context],
            outputs=[
                grid_image_output,
                grid_output,
                best_copy_output,
                insight_output,
                excluded_output,
                status_bar,
                json_output,
            ],
        )

    return demo


def build_parser():
    parser = argparse.ArgumentParser(description="attention 九宫格选图引擎 Web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--share", action="store_true")
    parser.add_argument("--inbrowser", action="store_true")
    return parser


def main():
    args = build_parser().parse_args()
    build_demo().launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        inbrowser=args.inbrowser,
        show_error=True,
        theme=gr.themes.Default(),
        css=DEMO_CSS,
    )


if __name__ == "__main__":
    main()
