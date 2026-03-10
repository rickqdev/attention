# attention Chrome Demo

这是一个最小可用的浏览器插件示例，用来演示：

1. 从当前页面抓一张图片
2. 调用本地 `attention` HTTP API
3. 返回视觉切入和图文草案

## 使用方式

1. 本地启动 API：

```bash
attention-api
```

2. 打开 Chrome 扩展管理页
3. 开启开发者模式
4. 加载 `extensions/chrome/`
5. 在插件中输入 `provider` 和 `api_key`
6. 打开任意带图片的页面后点击运行

注意：
- 当前插件不持久化保存 key
- 默认抓取页面中面积最大的图片
- 也可以手动填写图片 URL 覆盖自动抓取
