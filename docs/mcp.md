# MCP

`attention` 提供基础 `stdio` MCP server，适合本地 Agent、Codex、Claude Desktop 等工作流接入。

启动：

```bash
python3 -m pip install -r requirements.txt
attention-mcp
```

公开工具：

## `analyze_image_intent`

参数：
- `image`
  - `path` 或 `base64 + mime_type`
- `provider`
- `api_key`

返回：
- `status`
- `intent`
- `meta`
- `error`

## `generate_attention_copy`

参数：
- `intent`
- `context`
- `provider`
- `api_key`
- `include_viral_research`
- `tavily_api_key`

返回：
- `status`
- `intent`
- `copy_candidates`
- `best_copy`
- `why_it_works`
- `markdown`
- `meta`
- `error`

## Recommended Flow

1. 先调用 `analyze_image_intent`
2. 确认 `status == "ok"`
3. 再调用 `generate_attention_copy`
4. 仅在需要补热点线索时传 `include_viral_research=true`

默认是 `BYOK`：运行时传入 `provider/api_key`，不会写入 `config.json`。
