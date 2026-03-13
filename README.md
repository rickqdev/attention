# attention

Turn an image into its strongest visual hook, the question viewers are most likely to ask, and a usable copy draft.

中文快速说明：`attention` 会先找出图片里最值得展开的注意力点，再生成一版可继续修改的中文文案草稿。

![attention demo](./assets/demo-ui.png)

[Try attention in 60s](https://rickqdev.github.io/attention/) | [Use via API / MCP](./docs/for-developers.md) | [Browse examples](./examples/use-cases/README.md) | [Share a use case](https://github.com/rickqdev/attention/issues/new/choose)

English-first repo, Chinese-ready output:
- creators can start from the demo flow
- developers can integrate through CLI, HTTP API, MCP, or skill
- all public interfaces share the same `attention.v1` schema

## What You Get

- the strongest attention hook in an image
- the question viewers are most likely to ask next
- a draft you can keep editing instead of a blank page
- a structured response you can reuse in products and agent workflows

`attention` is not:
- an auto-publishing tool
- a guaranteed virality engine
- a system that invents facts you did not provide

## Try It Now

### For Creators

Fastest path:

- open the [60-second quickstart page](https://rickqdev.github.io/attention/)
- or run the local browser demo:

```bash
python3 -m pip install -r requirements.txt
python3 app.py --inbrowser
```

You bring:
- an image
- your own model key

You get:
- the image's strongest hook
- a viewer question worth writing into
- a Chinese draft you can refine and publish

More:
- [individual usage guide](./docs/for-individuals.md)

### For Developers

Install and run one end-to-end request in a couple of minutes:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
attention-api --host 127.0.0.1 --port 8000
python3 scripts/http_demo.py --image /absolute/path/to/image.jpg --provider gemini --api-key "$GEMINI_API_KEY"
```

Developer entry points:
- `attention-cli`
- `attention-api`
- `attention-mcp`

More:
- [developer guide](./docs/for-developers.md)
- [HTTP API](./docs/http-api.md)
- [MCP](./docs/mcp.md)
- [Skill](./docs/skill.md)

## Example Outputs

Public example sets:
- [fashion / outfit focus](./examples/use-cases/fashion-lookbook.md)
- [accessories / detail focus](./examples/use-cases/accessories-detail.md)
- [cafe / mood shot focus](./examples/use-cases/cafe-detail.md)

Structured samples:
- [`examples/attention_sample.json`](./examples/attention_sample.json)
- [`examples/attention_sample.md`](./examples/attention_sample.md)

## Who It Is For

Good fit for creators who post:
- fashion, nails, accessories
- cafes, close-up details, mood-driven content
- image-led content that needs a stronger first line

Good fit for developers building:
- creator tools
- browser extensions
- content workflows
- agent systems that need `intent -> copy` as a reusable step

## Developer Integration

Supported interfaces:
- CLI for local or batch usage
- HTTP API for web apps, extensions, and backend services
- MCP for Codex, Claude Desktop, and local agent workflows
- skill packaging for teams that want a fixed two-step flow

Unified response contract: `attention.v1`

Core fields:
- `status`
- `intent`
- `copy_candidates`
- `best_copy`
- `why_it_works`
- `meta`

## Limits, BYOK, And Privacy

- BYOK by default: pass `provider` and `api_key` at runtime
- runtime keys are not written to disk automatically
- failed vision analysis returns explicit errors instead of fake success
- `config.json`, logs, outputs, and real photos stay out of Git by default
- v1 does not include auto-posting, account operations, or comment monitoring

## Roadmap And Feedback

- [roadmap](./ROADMAP.md)
- [GitHub Discussions](https://github.com/rickqdev/attention/discussions)
- [issue forms](https://github.com/rickqdev/attention/issues/new/choose)

If you are exploring `attention` for a product, share:
- what image type you are testing
- what hook you hoped it would find
- whether you are using the demo, API, MCP, or skill
