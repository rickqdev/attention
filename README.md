# attention / 注意力

**Find the attention-driving angle in an image, then turn it into clear, reusable copy.**  
上传一张图，先找出最值得展开的意图，再把它整理成清晰、可继续修改的图文草案。

![attention demo](./assets/demo-ui.png)

## 为什么它不是普通文案工具

- 先解决“写什么”：不是每张图都该从整体开始写，真正值得展开的，常常是一个细节、反差或追问点。
- 再解决“怎么写”：把这个点转成更清晰的标题、正文和标签草案，方便你继续改成自己的表达。
- 尽量避免乱编：你可以补充真实信息，工具只负责放大亮点，不负责凭空补事实。

## 30 秒上手 | Quick Start

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

打开 Gradio 页面后：
- 上传图片
- 选择 `provider`（`gemini` / `minimax` / `auto`）
- 输入有效的 API key（仅本次运行使用，不落盘）
- 点击 `上传图片，生成图文草案`
- 或点击 `查看示例结果`

## 安装为包 | Install as a Package

```bash
python3 -m pip install -e .
```

可执行入口：
- `attention-cli`
- `attention-api`
- `attention-mcp`

## CLI 用法 | CLI Usage

```bash
attention-cli --help
attention-cli --provider gemini --api-key "$GEMINI_API_KEY" --skip-viral-research
```

默认路径约定：
- 输入图片：`photos/`
- 可选上下文：`context/context_YYYYMMDD.json`
- 输出结果：`output/attention_YYYYMMDD.json`
- 输出摘要：`output/attention_YYYYMMDD.md`

## 开发者接入 | Developer Interfaces

### HTTP API

```bash
attention-api
```

- `POST /v1/intent/analyze`
- `POST /v1/copy/generate`

文档：
- [docs/http-api.md](./docs/http-api.md)
- [docs/integration.md](./docs/integration.md)

### MCP

```bash
attention-mcp
```

公开工具：
- `analyze_image_intent`
- `generate_attention_copy`

文档：
- [docs/mcp.md](./docs/mcp.md)

### Skill

仓库内包含可分发 skill：
- [skills/attention-mcp/SKILL.md](./skills/attention-mcp/SKILL.md)

说明：
- [docs/skill.md](./docs/skill.md)

## 它具体会帮你做什么

- 识别最该写的点：从图片里找出最先抓住注意力的视觉主角，而不是泛泛描述“这张图很好看”。
- 预测用户最想问什么：把“看到这张图的人第一句会问什么”先找出来，文案开头就更容易抓住人。
- 生成可继续修改的表达：输出标题、正文和标签建议，让你更快得到一个结构清晰的图文初稿，而不是模板化营销稿。

## 示例结果拆解

公开示例顺序固定为：

1. 原图：局部细节穿搭照，第一眼会先停在无名指上的蜘蛛装饰。
2. 视觉主角：`蜘蛛装饰美甲`
3. 用户最想问：`这个蜘蛛装饰美甲是怎么做出来的？`
4. 为什么这个角度成立：不是泛泛写整套穿搭，而是先用一个反差细节把人停住。
5. 生成文案：把“先被细节吸走，再顺着气氛看完整张图”的过程写出来，形成更自然的图文展开。

## 输出契约 | Output Contract

统一 schema：`attention.v1`

公开响应至少包含：
- `status`
- `intent`
- `copy_candidates`
- `best_copy`
- `why_it_works`
- `meta`

示例文件：
- `examples/attention_sample.json`
- `examples/attention_sample.md`
- `examples/requests/analyze_path.json`
- `examples/requests/analyze_base64.template.json`
- `examples/requests/generate_copy.json`

## 安全与隐私 | Security

- 仓库只提供 `config.example.json` 模板。
- `config.json`、真实图片、日志、运行产物默认不会进入 Git。
- UI、HTTP API、MCP 中输入的 key 只在当前请求内存中使用，不会自动写入文件。
- 如果视觉分析失败，程序会明确报错，不会输出伪造成功结果。
- 公开模式默认 `BYOK`。

## FAQ

**它和普通 AI 文案工具有什么区别？**  
普通工具通常从空白开始写，`attention / 注意力` 会先从图片里找到最值得展开的那个点，再把它整理成更清晰的图文草案。

**适合什么内容？**  
适合个人账号、日常发图、穿搭、美甲、饰品、探店、局部细节这类需要“先抓注意力再展开”的内容。

**它不是做什么的？**  
它不是自动发布工具，也不承诺爆款；它的价值是帮你先找到那个真正值得展开的切入点。

**它能被第三方接入吗？**  
可以。仓库现在提供了 CLI、HTTP API、基础 `stdio MCP` 和可分发 skill，适合前端、插件、工作流系统和 Agent 使用。

## Browser Demo

仓库附带一个最小浏览器插件示例：
- [extensions/chrome/README.md](./extensions/chrome/README.md)

## Scope (v1)

- 保留：图片意图分析 + 文案生成核心链路 + Gradio 演示 + HTTP API + 基础 MCP + Skill
- 不包含：自动发布、评论监控、养号、变现等运营模块
