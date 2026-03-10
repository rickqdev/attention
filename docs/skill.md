# Skill

仓库内提供一个可分发的 skill：`skills/attention-mcp/`

用途：
- 告诉 Agent 什么时候该先看图、什么时候该继续出文案
- 强制两步调用顺序
- 缺少 key 时明确提示运行时提供

推荐安装方式：

1. 将 `skills/attention-mcp/` 复制到你的 `$CODEX_HOME/skills/`
2. 在你的 MCP 客户端中注册本地 `attention-mcp` server
3. 显式使用 `$attention-mcp`

这个 skill 假设本地已经存在同名 MCP server，并暴露：
- `analyze_image_intent`
- `generate_attention_copy`
