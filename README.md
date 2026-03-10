# attention / 注意力

Find the most attention-grabbing angle in an image, then turn it into usable copy.  
从图片里找出最值得展开的点，再生成一版可继续修改的文案草稿。

![attention demo](./assets/demo-ui.png)

## Language

- [中文说明](./README.zh-CN.md)
- [English](./README.en.md)

## Quick Start

```bash
python3 -m pip install -r requirements.txt
python3 app.py --inbrowser
```

## Interfaces

- Web demo: `python3 app.py --inbrowser`
- CLI: `attention-cli`
- HTTP API: `attention-api --host 127.0.0.1 --port 8000`
- MCP: `attention-mcp`

## Docs

- [个人使用说明](./docs/for-individuals.md)
- [开发者接入说明](./docs/for-developers.md)
- [HTTP API](./docs/http-api.md)
- [MCP](./docs/mcp.md)
- [Skill](./docs/skill.md)

## Security

- runtime keys are not written to disk automatically
- failed vision analysis returns explicit errors instead of fake success
- real keys, outputs, logs, and private photos stay out of Git by default
