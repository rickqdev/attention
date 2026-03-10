# For Developers / 开发者接入

English:
`attention` can be consumed through HTTP API, stdio MCP, CLI, or a distributable skill. All interfaces share the same `attention.v1` schema.

## 快速接入路径

### 1. 安装

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

### 2. 启动 HTTP API

```bash
attention-api --host 127.0.0.1 --port 8000
```

### 3. 本地演示一次调用

```bash
python3 scripts/http_demo.py --image /absolute/path/to/image.jpg --provider gemini --api-key "$GEMINI_API_KEY"
```

如果你的前端、手机或插件需要从局域网访问本机 API：

```bash
attention-api --host 0.0.0.0 --port 8000
```

### 4. 如果你需要 Agent 工作流

```bash
attention-mcp
```

然后安装仓库自带的 skill：
- `skills/attention-mcp/`

## 公开接入面

### HTTP API

- `POST /v1/intent/analyze`
- `POST /v1/copy/generate`

适合：
- Web/H5
- 浏览器插件
- 第三方后端

### MCP

工具：
- `analyze_image_intent`
- `generate_attention_copy`

适合：
- Codex
- Claude Desktop
- 本地工作流系统

### Skill

适合：
- 需要固定两步调用顺序的 Agent
- 想强制 `intent -> copy` 流程的团队

## 开发者辅助脚本

- `scripts/http_demo.py`
  - 调本地 API，完整跑一次 `analyze -> copy`
- `scripts/encode_image.py`
  - 把本地图片转成 Base64，便于调试 API 或插件

## 接入约束

- 默认 `BYOK`
- 所有失败都返回结构化错误
- 图片输入支持本地路径和 Base64
- 输出内容默认中文
- 不要假设仓库存在真实 `config.json`
