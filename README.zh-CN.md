# attention / 注意力

从图片里找出最值得展开的点，再生成一版可继续修改的中文文案草稿。

![attention demo](./assets/demo-ui.png)

## 产品定位

`attention` 不是从空白开始硬写文案的工具。  
它先分析图片里最抓人的视觉点，再提炼出用户最可能会问的一句话，最后生成标题、正文和标签草稿。

适合的内容：
- 日常发图
- 穿搭、美甲、饰品
- 探店、局部细节、氛围图

不做的事：
- 不自动发布内容
- 不承诺爆款
- 不凭空补你没有提供的事实

## 个人使用

最快方式：

```bash
python3 -m pip install -r requirements.txt
python3 app.py --inbrowser
```

你需要：
- 一张图片
- 你自己的模型 key

你会得到：
- 图里最抓人的点
- 别人最想问的一句话
- 一版可以继续改的中文文案

更多说明：
- [个人使用说明](./docs/for-individuals.md)

## 开发者接入

安装：

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

可执行入口：
- `attention-cli`
- `attention-api`
- `attention-mcp`

开放能力：
- CLI：本地批量处理
- HTTP API：供 Web、插件、后端接入
- MCP：供 Agent 和工作流系统接入
- Skill：供 Codex/Agent 调用

开发者文档：
- [开发者接入说明](./docs/for-developers.md)
- [HTTP API](./docs/http-api.md)
- [MCP](./docs/mcp.md)
- [Skill](./docs/skill.md)

## 输出结构

统一 schema：`attention.v1`

核心返回字段：
- `status`
- `intent`
- `copy_candidates`
- `best_copy`
- `why_it_works`
- `meta`

示例文件：
- `examples/attention_sample.json`
- `examples/attention_sample.md`

## 安全与隐私

- 真实 key 不提交到仓库
- 运行时输入的 key 不会自动写入文件
- `config.json`、日志、输出、真实图片默认不会进入 Git
- 视觉分析失败时会明确报错，不会伪造成功结果

## 当前范围

v1 保留：
- 图片意图分析
- 文案生成
- Gradio Demo
- HTTP API
- 基础 MCP
- Skill

v1 不包含：
- 自动发布
- 评论监控
- 养号和运营模块
