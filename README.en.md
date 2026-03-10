# attention

Find the most attention-grabbing angle in an image, then turn it into usable copy.

![attention demo](./assets/demo-ui.png)

## What It Is

`attention` is not a blank-page copywriting tool.  
It first identifies the strongest visual hook in an image, then extracts the question a viewer is most likely to ask, and finally turns that into reusable copy.

Good fit for:
- daily image posts
- fashion, nails, accessories
- cafes, detail shots, mood-driven content

Out of scope:
- automatic publishing
- guaranteed virality
- inventing facts you did not provide

## For Individuals

Fastest path:

```bash
python3 -m pip install -r requirements.txt
python3 app.py --inbrowser
```

What you need:
- an image
- your own model key

What you get:
- the strongest attention hook in the image
- the question viewers are most likely to ask
- a Chinese draft you can keep editing

More:
- [Individual usage guide](./docs/for-individuals.md)

## For Developers

Install:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

Entry points:
- `attention-cli`
- `attention-api`
- `attention-mcp`

Open interfaces:
- CLI for local batch runs
- HTTP API for web apps, extensions, and backend services
- MCP for agents and workflow systems
- Skill for Codex/agent integrations

Developer docs:
- [Developer guide](./docs/for-developers.md)
- [HTTP API](./docs/http-api.md)
- [MCP](./docs/mcp.md)
- [Skill](./docs/skill.md)

## Output Contract

Unified schema: `attention.v1`

Core response fields:
- `status`
- `intent`
- `copy_candidates`
- `best_copy`
- `why_it_works`
- `meta`

Examples:
- `examples/attention_sample.json`
- `examples/attention_sample.md`

## Security

- real keys are not committed
- runtime keys are not written to disk automatically
- `config.json`, logs, outputs, and real photos stay out of Git by default
- failed vision analysis returns explicit errors instead of fake success

## Current Scope

Included in v1:
- image intent analysis
- copy generation
- Gradio demo
- HTTP API
- base MCP server
- skill

Not included in v1:
- auto-posting
- comment monitoring
- account operations modules
