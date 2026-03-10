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
DEFAULT_PROVIDER = "auto"

_RUNTIME_OPTIONS = {
    "provider": DEFAULT_PROVIDER,
    "model_id": "",
    "api_keys": {},
}


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


def set_runtime_options(provider=None, model_id=None, api_key=None, api_keys=None):
    if provider is not None:
        selected = str(provider).strip().lower()
        _RUNTIME_OPTIONS["provider"] = selected or DEFAULT_PROVIDER
    if model_id is not None:
        _RUNTIME_OPTIONS["model_id"] = str(model_id).strip()

    if api_keys is not None:
        cleaned = {}
        for key, value in dict(api_keys).items():
            provider_key = str(key).strip().lower()
            token = str(value).strip()
            if provider_key and token and not token.startswith("YOUR_"):
                cleaned[provider_key] = token
        _RUNTIME_OPTIONS["api_keys"] = cleaned

    if api_key is not None:
        selected = str(provider or _RUNTIME_OPTIONS.get("provider") or "").strip().lower()
        token = str(api_key).strip()
        if selected and selected != DEFAULT_PROVIDER:
            if token and not token.startswith("YOUR_"):
                _RUNTIME_OPTIONS["api_keys"][selected] = token
            else:
                _RUNTIME_OPTIONS["api_keys"].pop(selected, None)


def clear_runtime_options():
    _RUNTIME_OPTIONS["provider"] = DEFAULT_PROVIDER
    _RUNTIME_OPTIONS["model_id"] = ""
    _RUNTIME_OPTIONS["api_keys"] = {}


def get_runtime_options():
    return {
        "provider": _RUNTIME_OPTIONS.get("provider", DEFAULT_PROVIDER),
        "model_id": _RUNTIME_OPTIONS.get("model_id", ""),
        "api_keys": {key: "***" for key in _RUNTIME_OPTIONS.get("api_keys", {})},
    }


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


def _safe_token(value):
    token = str(value or "").strip()
    if not token or token.startswith("YOUR_"):
        return ""
    return token


def _selected_provider(provider=None):
    if provider:
        return str(provider).strip().lower()

    runtime_provider = str(_RUNTIME_OPTIONS.get("provider", "")).strip().lower()
    if runtime_provider:
        return runtime_provider

    cfg = load_config()
    return str(cfg.get("default_provider", DEFAULT_PROVIDER)).strip().lower() or DEFAULT_PROVIDER


def _selected_model(model_id=None):
    if model_id:
        return str(model_id).strip()
    runtime_model = str(_RUNTIME_OPTIONS.get("model_id", "")).strip()
    if runtime_model:
        return runtime_model
    return ""


def _resolve_api_key(provider, explicit_key=None):
    key = _safe_token(explicit_key)
    if key:
        return key

    runtime_keys = _RUNTIME_OPTIONS.get("api_keys", {})
    runtime_key = _safe_token(runtime_keys.get(provider))
    if runtime_key:
        return runtime_key

    cfg = load_config()
    config_key = _safe_token(cfg.get(f"{provider}_api_key", ""))
    return config_key


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


def _call_gemini(prompt, images=None, temperature=0.8, model=None, api_key=None):
    cfg = load_config()
    key = _resolve_api_key("gemini", explicit_key=api_key)
    if not key:
        return None

    model_name = model or _selected_model() or cfg.get("gemini_model", "gemini-2.5-flash")
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
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}",
        payload,
        timeout=90,
    )
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_glm(prompt, temperature=0.8, model=None, api_key=None):
    cfg = load_config()
    key = _resolve_api_key("glm", explicit_key=api_key)
    if not key:
        return None

    model_name = model or _selected_model() or cfg.get("glm_model", "glm-4-flash")
    data = _post_json(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 4096,
        },
        headers={"Authorization": f"Bearer {key}"},
        timeout=30,
    )
    return data["choices"][0]["message"]["content"]


def _call_minimax(prompt, images=None, temperature=0.8, model=None, api_key=None):
    cfg = load_config()
    key = _resolve_api_key("minimax", explicit_key=api_key)
    if not key:
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
        model_name = model or _selected_model() or cfg.get("minimax_vl_model", "MiniMax-VL-01")
    else:
        messages = [{"role": "user", "content": prompt}]
        model_name = model or _selected_model() or cfg.get("minimax_text_model", "MiniMax-Text-01")

    data = _post_json(
        "https://api.minimax.chat/v1/text/chatcompletion_v2",
        {
            "model": model_name,
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


def _call_qwen_local(prompt, temperature=0.8, model=None):
    cfg = load_config()
    base_url = cfg.get("qwen_ollama_url", "http://localhost:11434")
    model_name = model or _selected_model() or cfg.get("qwen_model", "qwen2.5:0.5b")
    data = _post_json(
        f"{base_url.rstrip('/')}/api/generate",
        {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 2048},
        },
        timeout=120,
    )
    return data.get("response", "")


def _run_provider(name, fn):
    try:
        result = fn()
        if result and str(result).strip():
            return result
    except Exception as exc:
        log(f"{name} 请求失败: {str(exc)[:120]}", "WARN")
    return None


def vision_request(prompt, images, provider=None, model_id=None):
    selected_provider = _selected_provider(provider)
    selected_model = _selected_model(model_id)

    if selected_provider in ("gemini", "minimax"):
        mapping = {
            "gemini": ("Gemini", lambda: _call_gemini(prompt, images=images, temperature=0.3, model=selected_model)),
            "minimax": ("MiniMax", lambda: _call_minimax(prompt, images=images, temperature=0.3, model=selected_model)),
        }
        name, fn = mapping[selected_provider]
        result = _run_provider(name, fn)
        if result:
            return result
        log(f"{name} 视觉分析失败。", "ERR")
        return None

    if selected_provider not in ("auto", ""):
        log(f"Provider {selected_provider} 不支持视觉输入，请改用 gemini 或 minimax。", "ERR")
        return None

    fallback_chain = [
        ("Gemini", lambda: _call_gemini(prompt, images=images, temperature=0.3, model=selected_model)),
        ("MiniMax", lambda: _call_minimax(prompt, images=images, temperature=0.3, model=selected_model)),
    ]
    for name, fn in fallback_chain:
        result = _run_provider(name, fn)
        if result:
            if name != "Gemini":
                log(f"视觉模型自动降级到 {name}。", "WARN")
            return result

    log("所有视觉模型均失败。", "ERR")
    return None


def gemini_request(prompt, images=None, model=None, temperature=0.8, provider=None):
    selected_provider = _selected_provider(provider)
    selected_model = _selected_model(model)

    if selected_provider in ("gemini", "minimax", "glm", "qwen_local"):
        provider_map = {
            "gemini": ("Gemini", lambda: _call_gemini(prompt, images=images, temperature=temperature, model=selected_model)),
            "minimax": ("MiniMax", lambda: _call_minimax(prompt, images=images, temperature=temperature, model=selected_model)),
            "glm": (
                "GLM",
                lambda: _call_glm(prompt, temperature=temperature, model=selected_model) if not images else None,
            ),
            "qwen_local": (
                "Qwen 本地",
                lambda: _call_qwen_local(prompt, temperature=temperature, model=selected_model) if not images else None,
            ),
        }
        name, fn = provider_map[selected_provider]
        if images and selected_provider in ("glm", "qwen_local"):
            log(f"Provider {selected_provider} 不支持视觉输入，请改用 gemini 或 minimax。", "ERR")
            return None
        result = _run_provider(name, fn)
        if not result:
            log(f"{name} 请求失败。", "ERR")
        return result

    providers = [
        ("Gemini", lambda: _call_gemini(prompt, images=images, temperature=temperature, model=selected_model)),
        ("GLM", lambda: _call_glm(prompt, temperature=temperature, model=selected_model) if not images else None),
        ("MiniMax", lambda: _call_minimax(prompt, images=images, temperature=temperature, model=selected_model)),
        ("Qwen 本地", lambda: _call_qwen_local(prompt, temperature=temperature, model=selected_model) if not images else None),
    ]
    for name, fn in providers:
        result = _run_provider(name, fn)
        if result:
            if name != "Gemini":
                log(f"使用备用模型：{name}", "WARN")
            return result

    log("所有模型均失败。", "ERR")
    return None


def tavily_search(query, max_results=5, retry=2):
    key = _resolve_api_key("tavily")
    if not key:
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
