# attention / 注意力

一个面向中文社交内容的 CLI 工具：读取图片，分析用户第一眼会被什么吸引、最可能追问什么，再输出一条更容易抓住注意力的文案。

## 这个版本做什么

- 分析图片里的视觉主角、用户最想问的问题和最强注意力切入点
- 可选抓取同类热门内容线索，补充标题结构、关键词和语气参考
- 基于图片意图和上下文，生成一条中文社交平台文案
- 输出结构化 JSON 和一份便于快速查看的 Markdown 摘要

## 目录约定

- `photos/`: 运行时放待分析图片
- `context/context_YYYYMMDD.json`: 运行时可选填写的真实上下文
- `output/attention_YYYYMMDD.json`: 本次运行的完整结果
- `output/attention_YYYYMMDD.md`: 本次运行的摘要结果
- `examples/`: 仓库内的脱敏示例输入输出

## 快速开始

1. 复制配置模板。
2. 至少填写 `gemini_api_key`。
3. 把图片放到 `photos/`。
4. 运行：

```bash
cp config.example.json config.json
python3 main.py
```

如果你不想做可选的爆款线索研究，可以运行：

```bash
python3 main.py --skip-viral-research
```

查看帮助：

```bash
python3 main.py --help
```

## 配置说明

`config.json` 不会提交到 Git。当前只要求：

- `gemini_api_key`: 必填，图片意图分析和主文案生成
- `tavily_api_key`: 可选，用于抓取同类热门内容线索
- `glm_api_key` / `minimax_api_key`: 可选，文字或视觉兜底
- `persona`: 控制文案语气、背景和禁用风格
- `forbidden_words`: 自定义违禁词检查

## 上下文模板

仓库内提供了 `context/context.example.json`。

运行 `main.py` 时，如果当天的上下文文件不存在，会自动生成 `context/context_YYYYMMDD.json`。你可以在里面补充主体信息、场景和配角信息，生成时会优先使用这些真实信息。

## 示例

- `examples/attention_sample.json`
- `examples/attention_sample.md`

## 安全说明

- 不要提交真实 `config.json`
- 不要提交真实图片、日志和运行产物
- 如果你曾经在别处暴露过真实 API key，建议在推送前主动轮换
