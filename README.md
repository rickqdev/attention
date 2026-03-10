# attention / 注意力

**Image → Attention Copy**  
上传图片，自动识别视觉主角与“用户最想问的问题”，输出最可能抓住注意力的文案。

If this project is useful, please give it a Star.

## 30 秒上手 | Quick Start

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

打开 Gradio 页面后：
- 上传图片
- 选择 `provider`（`gemini` / `minimax` / `auto`）
- 输入你的 API key（仅本次运行使用，不落盘）
- 点击生成

## CLI 用法 | CLI Usage

```bash
python3 main.py --help
python3 main.py --provider gemini --api-key "$GEMINI_API_KEY" --skip-viral-research
```

默认路径约定：
- 输入图片：`photos/`
- 可选上下文：`context/context_YYYYMMDD.json`
- 输出结果：`output/attention_YYYYMMDD.json`
- 输出摘要：`output/attention_YYYYMMDD.md`

## 输出契约 | Output Contract

生成结果 JSON 至少包含：
- `intent`
- `user_question`
- `copy_candidates`
- `best_copy`
- `why_it_works`

示例文件：
- `examples/attention_sample.json`
- `examples/attention_sample.md`

## 安全与隐私 | Security

- 仓库只提供 `config.example.json` 模板。
- `config.json`、真实图片、日志、运行产物默认不会进入 Git。
- UI 中输入的 key 只在内存中用于当前请求，不会自动写入文件。

## Scope (v1)

- 保留：图片意图分析 + 文案生成核心链路 + Gradio 演示
- 不包含：自动发布、评论监控、养号、变现等运营模块
