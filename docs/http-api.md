# HTTP API

`attention` 提供两个同构 JSON 接口，适合 Web/H5、浏览器插件和第三方后端接入。

启动本地服务：

```bash
python3 -m pip install -r requirements.txt
attention-api --host 127.0.0.1 --port 8000
```

默认地址：`http://127.0.0.1:8000`

如果你要让手机、浏览器插件或另一台机器访问本机 API，可改为：

```bash
attention-api --host 0.0.0.0 --port 8000
```

## Endpoints

### `POST /v1/intent/analyze`

请求体：

```json
{
  "schema_version": "attention.v1",
  "image": {
    "path": "/absolute/path/to/image.jpg"
  },
  "provider": "gemini",
  "api_key": "YOUR_PROVIDER_API_KEY"
}
```

也支持 Base64：

```json
{
  "schema_version": "attention.v1",
  "image": {
    "base64": "BASE64_IMAGE_DATA",
    "mime_type": "image/jpeg"
  },
  "provider": "auto",
  "api_key": "YOUR_PROVIDER_API_KEY"
}
```

### `POST /v1/copy/generate`

请求体：

```json
{
  "schema_version": "attention.v1",
  "intent": {
    "hero_element": "蜘蛛装饰美甲",
    "hero_reason": "局部细节反差强，第一眼最容易停住",
    "supporting_elements": ["紫色针织", "库洛米发夹"],
    "mood": "怪甜、轻微暗黑感",
    "viewer_question": "这个蜘蛛装饰美甲是怎么做出来的？",
    "attention_angle": "先用怪细节把人停住，再展开整张图的气氛",
    "social_search_query": "蜘蛛美甲 紫色美甲",
    "info_needed": ["是否手作", "是否定制"],
    "relevance_score": 9
  },
  "context": {
    "subject": {
      "name": "",
      "source": "",
      "price": "",
      "notes": ""
    },
    "supporting": [],
    "scene": {
      "location": "",
      "time": "",
      "feeling": ""
    },
    "extra": ""
  },
  "provider": "gemini",
  "api_key": "YOUR_PROVIDER_API_KEY",
  "include_viral_research": false,
  "tavily_api_key": ""
}
```

## Error Contract

所有失败统一返回：

```json
{
  "schema_version": "attention.v1",
  "status": "error",
  "meta": {
    "provider_requested": "auto",
    "provider_used": "",
    "warnings": []
  },
  "error": {
    "code": "vision_analysis_failed",
    "message": "视觉分析失败，未获得有效图片意图。",
    "suggestions": [
      "确认 provider 与 api_key 可用。",
      "更换一张更清晰的图片再试。"
    ]
  }
}
```
