"""Google Gemini provider."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import httpx

from attention.config import load_config
from .base import LLMProvider

logger = logging.getLogger("attention.providers.gemini")

_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _encode_images(images: list[bytes | str]) -> list[dict]:
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
        parts.append({"inline_data": {"mime_type": mime, "data": data}})
    return parts


class GeminiProvider(LLMProvider):
    name = "gemini"
    supports_vision = True

    def __init__(self, api_key: str = "", model: str = ""):
        self._api_key = api_key
        self._model = model

    def _resolve_key(self) -> str:
        if self._api_key:
            return self._api_key
        cfg = load_config()
        return cfg.get_api_key("gemini")

    def _resolve_model(self) -> str:
        if self._model:
            return self._model
        cfg = load_config()
        return cfg.gemini_model or "gemini-2.5-flash"

    def is_available(self) -> bool:
        return bool(self._resolve_key())

    async def generate(
        self,
        prompt: str,
        images: list[bytes | str] | None = None,
        temperature: float = 0.8,
        max_tokens: int = 8192,
    ) -> str:
        key = self._resolve_key()
        if not key:
            raise ValueError("Gemini API key not configured")

        model = self._resolve_model()
        parts = _encode_images(images) if images else []
        parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        with httpx.Client(timeout=90, follow_redirects=True) as client:
            resp = client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        return data["candidates"][0]["content"]["parts"][0]["text"]
