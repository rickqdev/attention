"""OpenAI-compatible provider.

Covers any API that speaks the OpenAI chat completions format:
MiniMax, GLM (Zhipu), Ollama, DeepSeek, Qwen (cloud), vLLM, LM Studio, etc.

User provides: base_url, api_key, model. One implementation for all.
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.request
from pathlib import Path

from .base import LLMProvider

logger = logging.getLogger("attention.providers.openai_compat")

_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class OpenAICompatProvider(LLMProvider):
    """Provider for any OpenAI-compatible API endpoint."""

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        model: str = "gpt-4o-mini",
        name: str = "openai-compat",
        supports_vision: bool = False,
        timeout: int = 90,
    ):
        self.name = name
        self.supports_vision = supports_vision
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def is_available(self) -> bool:
        return bool(self._api_key) or self._is_local()

    def _is_local(self) -> bool:
        return "localhost" in self._base_url or "127.0.0.1" in self._base_url

    async def generate(
        self,
        prompt: str,
        images: list[bytes | str] | None = None,
        temperature: float = 0.8,
        max_tokens: int = 4096,
    ) -> str:
        if images and not self.supports_vision:
            raise ValueError(f"{self.name} does not support vision input")

        if images:
            content = self._build_vision_content(prompt, images)
        else:
            content = prompt

        messages = [{"role": "user", "content": content}]
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        url = f"{self._base_url}/chat/completions"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        choices = data.get("choices", [])
        if not choices:
            raise ValueError(f"{self.name} returned empty choices")

        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            return " ".join(
                item.get("text", "") for item in content if item.get("type") == "text"
            )
        return content

    def _build_vision_content(self, prompt: str, images: list[bytes | str]) -> list[dict]:
        parts = []
        for img in images:
            if isinstance(img, (str, Path)):
                path = Path(img)
                data = base64.b64encode(path.read_bytes()).decode("utf-8")
                mime = _MIME_MAP.get(path.suffix.lower(), "image/jpeg")
            elif isinstance(img, bytes):
                data = base64.b64encode(img).decode("utf-8")
                mime = "image/jpeg"
            else:
                continue
            parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{data}"},
            })
        parts.append({"type": "text", "text": prompt})
        return parts
