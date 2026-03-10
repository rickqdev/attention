# For Individuals / 个人怎么用

个人使用时，最简单的理解就是：
- 你上传图片
- 你自己填模型 key
- 它帮你找图里的亮点，并给你一版文案草稿

English:
For individual use, just upload an image, paste your own model key, and get a usable draft.

## 场景 1：桌面浏览器直接用

```bash
python3 -m pip install -r requirements.txt
python3 app.py --inbrowser
```

打开页面后：
- 上传图片
- 选择 `provider`
- 粘贴你自己的 API key
- 可选填写临时上下文
- 点击生成

适合：
- 想快速出一版草稿
- 想知道这张图该从哪里写
- 想先有标题和正文，再自己改

## 场景 2：手机浏览器访问 H5

English:
The Gradio UI is responsive enough for mobile browsers. You do not need a native app for v1.

做法：
- 在电脑或服务器启动 `python3 app.py --host 0.0.0.0`
- 查看电脑当前局域网 IP，例如 `192.168.1.23`
- 用手机浏览器打开 `http://192.168.1.23:7860`
- 上传相册图片
- 粘贴自己的 key

适合：
- 手上只有手机也想先出一版
- 看完图就想顺手改文案

## 场景 3：本地 CLI 批量跑

```bash
attention-cli --provider gemini --api-key "$GEMINI_API_KEY" --skip-viral-research
```

默认约定：
- 输入目录：`photos/`
- 上下文模板：`context/context_YYYYMMDD.json`
- 输出 JSON：`output/attention_YYYYMMDD.json`
- 输出 Markdown：`output/attention_YYYYMMDD.md`

适合：
- 你手里已经有一批图片
- 想把结果保存成文件
- 想反复改上下文再重跑

## 你需要准备什么

- 一张可读的图片
- 一个可用的 `provider/api_key`
- 可选的真实上下文
- 如果要用手机访问，需要电脑与手机在同一局域网，或你自己部署到可访问地址

不会发生的事：
- 不会自动把 key 写入 `config.json`
- 不会在视觉分析失败时伪造成功结果
- 不会替你自动发布内容
