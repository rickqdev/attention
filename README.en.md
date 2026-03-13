# attention

Turn an image into its strongest visual hook, the question viewers are most likely to ask, and a usable copy draft.

![attention demo](./assets/demo-ui.png)

[Try attention in 60s](https://rickqdev.github.io/attention/) | [Use via API / MCP](./docs/for-developers.md) | [Browse examples](./examples/use-cases/README.md) | [Share a use case](https://github.com/rickqdev/attention/issues/new/choose)

This is the English-first project overview. For the detailed Chinese guide, see [README.zh-CN.md](./README.zh-CN.md).

## What You Get

- the strongest attention hook in an image
- the question viewers are most likely to ask next
- a draft you can keep editing instead of starting from zero
- a structured `attention.v1` response for product and workflow reuse

## Try It Now

### For Creators

```bash
python3 -m pip install -r requirements.txt
python3 app.py --inbrowser
```

- [60-second quickstart](https://rickqdev.github.io/attention/)
- [individual usage guide](./docs/for-individuals.md)

### For Developers

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
attention-api --host 127.0.0.1 --port 8000
python3 scripts/http_demo.py --image /absolute/path/to/image.jpg --provider gemini --api-key "$GEMINI_API_KEY"
```

- [developer guide](./docs/for-developers.md)
- [HTTP API](./docs/http-api.md)
- [MCP](./docs/mcp.md)
- [Skill](./docs/skill.md)

## Example Outputs

- [fashion / outfit focus](./examples/use-cases/fashion-lookbook.md)
- [accessories / detail focus](./examples/use-cases/accessories-detail.md)
- [cafe / mood shot focus](./examples/use-cases/cafe-detail.md)
- [`examples/attention_sample.json`](./examples/attention_sample.json)

## Limits

- BYOK by default
- no automatic publishing
- no guaranteed virality
- no invented facts
- no silent success on failed vision analysis
