---
name: attention-mcp
description: Use this skill when a user wants to analyze an image's attention hook and turn it into Chinese copy through the attention MCP tools. It is especially useful for image-first copy ideation, social content drafting, BYOK workflows, and two-step intent-then-copy generation.
---

# Attention MCP

This skill assumes an MCP server is available with two tools:

- `analyze_image_intent`
- `generate_attention_copy`

Use this skill when the task is "look at this image, find the strongest angle, and write copy from it."

## Workflow

1. If the user gives an image and wants insight, call `analyze_image_intent` first.
2. Only if `status == "ok"`, continue to `generate_attention_copy`.
3. If the user already has a verified `intent`, skip directly to `generate_attention_copy`.
4. If the user did not provide runtime keys, explain that `attention` runs in BYOK mode by default and needs `provider/api_key` from the caller or hosting product.

## Tool Mapping

### `analyze_image_intent`

Use for:
- extracting the visual hero
- identifying the viewer's first question
- getting the strongest attention angle before writing

Required input:
- `image`
- `provider`
- `api_key`

### `generate_attention_copy`

Use for:
- converting a verified intent into Chinese copy candidates
- adding optional context
- optionally layering viral research when a Tavily key is available

Required input:
- `intent`
- `provider`
- `api_key`

Optional input:
- `context`
- `include_viral_research`
- `tavily_api_key`

## Behavior Rules

- Never generate copy if the previous intent analysis failed.
- Treat `status=error` as a real failure, not as partial success.
- Do not assume a local `config.json` exists.
- Prefer a two-step flow over jumping directly to copy generation.
- Keep the final user-facing explanation concise: visual hero, viewer question, best copy, and why it works.
