# Integration Overview

`attention` 当前提供四种接入层：

- CLI：适合本地批量运行
- Web/H5：适合普通用户和内部演示
- HTTP API：适合前端、插件和第三方后端
- MCP：适合 Agent 和工作流系统

统一原则：

- 所有接口共享 `attention.v1` schema
- 公开默认 `BYOK`
- 错误统一结构化返回
- 不在成功失败之间伪造结果

推荐接入顺序：

1. 先完成 `intent analyze`
2. 再做 `copy generate`
3. 根据需要补 `context`
4. 需要热点线索时再加 Tavily key
