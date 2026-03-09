import base64
import json
import os
import re
import urllib.request
from datetime import datetime
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
CONFIG_EXAMPLE_PATH = BASE_DIR / "config.example.json"
TODAY = datetime.now().strftime("%Y%m%d")
NOW = datetime.now()


def get_config_path():
    env_path = os.environ.get("ATTENTION_CONFIG")
    if env_path:
        return Path(env_path).expanduser()
    if CONFIG_PATH.exists():
        return CONFIG_PATH
    return CONFIG_EXAMPLE_PATH


@lru_cache(maxsize=1)
def load_config():
    config_path = get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    with open(config_path, encoding="utf-8") as handle:
        return json.load(handle)


def log(msg, level="INFO"):
    icons = {
        "INFO": "ℹ️",
        "OK": "✅",
        "WARN": "⚠️",
        "ERR": "❌",
        "START": "🚀",
        "DONE": "🎉",
    }
    icon = icons.get(level, "·")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {icon} {msg}")


def _post_json(url, payload, headers=None, timeout=60):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _image_parts(images):
    parts = []
    for img_path in images or []:
        path = Path(img_path)
        try:
            encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        except OSError as exc:
            log(f"图片读取失败 {path}: {exc}", "WARN")
            continue

        mime = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(path.suffix.lower(), "image/jpeg")
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime,
                    "data": encoded,
                }
            }
        )
    return parts


def _call_gemini(prompt, images=None, temperature=0.8):
    cfg = load_config()
    key = str(cfg.get("gemini_api_key", "")).strip()
    if not key or key.startswith("YOUR_"):
        return None

    parts = _image_parts(images)
    parts.append({"text": prompt})
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 8192,
        },
    }
    data = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}",
        payload,
        timeout=90,
    )
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_glm(prompt, temperature=0.8):
    cfg = load_config()
    key = str(cfg.get("glm_api_key", "")).strip()
    if not key or key.startswith("YOUR_"):
        return None

    data = _post_json(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        {
            "model": "glm-4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 4096,
        },
        headers={"Authorization": f"Bearer {key}"},
        timeout=30,
    )
    return data["choices"][0]["message"]["content"]


def _call_minimax(prompt, images=None, temperature=0.8):
    cfg = load_config()
    key = str(cfg.get("minimax_api_key", "")).strip()
    if not key or key.startswith("YOUR_"):
        return None

    if images:
        content = []
        for part in _image_parts(images):
            inline = part["inline_data"]
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{inline['mime_type']};base64,{inline['data']}",
                    },
                }
            )
        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]
        model = "MiniMax-VL-01"
    else:
        messages = [{"role": "user", "content": prompt}]
        model = "MiniMax-Text-01"

    data = _post_json(
        "https://api.minimax.chat/v1/text/chatcompletion_v2",
        {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        },
        headers={"Authorization": f"Bearer {key}"},
        timeout=90,
    )
    choices = data.get("choices", [])
    if not choices:
        return None

    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        return " ".join(item.get("text", "") for item in content if item.get("type") == "text")
    return content


def _call_qwen_local(prompt, temperature=0.8):
    cfg = load_config()
    base_url = cfg.get("qwen_ollama_url", "http://localhost:11434")
    model = cfg.get("qwen_model", "qwen2.5:0.5b")
    data = _post_json(
        f"{base_url.rstrip('/')}/api/generate",
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 2048},
        },
        timeout=120,
    )
    return data.get("response", "")


def vision_request(prompt, images):
    try:
        result = _call_gemini(prompt, images=images, temperature=0.3)
        if result and result.strip():
            return result
    except Exception as exc:
        log(f"Gemini 视觉分析失败: {str(exc)[:120]}", "WARN")

    try:
        result = _call_minimax(prompt, images=images, temperature=0.3)
        if result and result.strip():
            log("使用 MiniMax 作为视觉兜底。", "WARN")
            return result
    except Exception as exc:
        log(f"MiniMax 视觉兜底失败: {str(exc)[:120]}", "WARN")

    log("所有视觉模型均失败。", "ERR")
    return None


def gemini_request(prompt, images=None, model=None, temperature=0.8):
    del model
    providers = [
        ("Gemini", lambda: _call_gemini(prompt, images=images, temperature=temperature)),
        ("GLM", lambda: _call_glm(prompt, temperature=temperature) if not images else None),
        ("MiniMax", lambda: _call_minimax(prompt, images=images, temperature=temperature)),
        ("Qwen 本地", lambda: _call_qwen_local(prompt, temperature=temperature) if not images else None),
    ]
    for name, fn in providers:
        try:
            result = fn()
            if result and str(result).strip():
                if name != "Gemini":
                    log(f"使用备用模型：{name}", "WARN")
                return result
        except Exception as exc:
            log(f"{name} 请求失败: {str(exc)[:120]}", "WARN")
    log("所有模型均失败。", "ERR")
    return None


def tavily_search(query, max_results=5, retry=2):
    cfg = load_config()
    key = str(cfg.get("tavily_api_key", "")).strip()
    if not key or key.startswith("YOUR_"):
        return []

    payload = {
        "api_key": key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
    }
    try:
        data = _post_json("https://api.tavily.com/search", payload, timeout=20)
        return data.get("results", [])
    except Exception as exc:
        if retry > 0:
            return tavily_search(query, max_results=max_results, retry=retry - 1)
        log(f"Tavily 搜索失败: {str(exc)[:120]}", "WARN")
        return []


def clean_json(text):
    return re.sub(r"```json\s*|\s*```", "", text or "").strip()


def check_forbidden(text):
    cfg = load_config()
    return [word for word in cfg.get("forbidden_words", []) if word in text]
