"""Configuration management for attention v2.

Supports: config.json, config.yaml, environment variables.
Priority: env vars > runtime > config file > defaults.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
TODAY = __import__("datetime").datetime.now().strftime("%Y%m%d")


class PersonaConfig(BaseModel):
    name: str = ""
    background: str = ""
    specialty: str = ""
    style_core: str = ""
    tone: str = ""
    avoid: str = ""


class TargetAudienceConfig(BaseModel):
    age_range: str = ""
    gender: str = ""
    interest: str = ""


class PublishConfig(BaseModel):
    best_times_weekday: list[str] = Field(default_factory=lambda: ["12:00", "17:30", "22:00"])
    best_times_weekend: list[str] = Field(default_factory=lambda: ["10:00", "15:00", "22:00"])
    notes_per_day: int = 1
    publish_method: str = "browser"
    auto_publish: bool = False


class AttentionConfig(BaseModel):
    """Main configuration model."""

    # Provider keys
    default_provider: str = "auto"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    minimax_api_key: str = ""
    minimax_vl_model: str = "MiniMax-VL-01"
    minimax_text_model: str = "MiniMax-Text-01"
    glm_api_key: str = ""
    glm_model: str = "glm-4-flash"
    tavily_api_key: str = ""
    qwen_ollama_url: str = "http://localhost:11434"
    qwen_model: str = "qwen2.5:0.5b"

    # Notification keys
    resend_api_key: str = ""
    resend_from: str = ""
    resend_to: str = ""

    # Content
    persona: PersonaConfig = Field(default_factory=PersonaConfig)
    target_audience: TargetAudienceConfig = Field(default_factory=TargetAudienceConfig)
    publish: PublishConfig = Field(default_factory=PublishConfig)
    seed_keywords: list[str] = Field(default_factory=list)
    forbidden_words: list[str] = Field(default_factory=list)
    recommended_keywords: list[str] = Field(default_factory=list)
    mbti_hooks: dict[str, str] = Field(default_factory=dict)

    # Safety
    real_photo_min_ratio: float = 0.4
    warmup_days: int = 14

    def get_api_key(self, provider: str) -> str:
        """Resolve API key for a provider, checking env vars first."""
        env_key = os.environ.get(f"ATTENTION_{provider.upper()}_API_KEY", "")
        if env_key and not env_key.startswith("YOUR_"):
            return env_key
        key = getattr(self, f"{provider}_api_key", "")
        if key and not key.startswith("YOUR_"):
            return key
        return ""


def _find_config_path() -> Path:
    env_path = os.environ.get("ATTENTION_CONFIG")
    if env_path:
        return Path(env_path).expanduser()
    candidates = [
        BASE_DIR / "config.json",
        BASE_DIR / "config.yaml",
        BASE_DIR / "config.yml",
    ]
    for path in candidates:
        if path.exists():
            return path
    return BASE_DIR / "config.example.json"


@lru_cache(maxsize=1)
def load_config() -> AttentionConfig:
    """Load and validate configuration."""
    path = _find_config_path()
    if not path.exists():
        return AttentionConfig()

    with open(path, encoding="utf-8") as f:
        if path.suffix in (".yaml", ".yml"):
            try:
                import yaml
                raw = yaml.safe_load(f)
            except ImportError:
                raw = {}
        else:
            raw = json.load(f)

    return AttentionConfig.model_validate(raw)


def load_config_raw() -> dict[str, Any]:
    """Load raw config dict (for backward compatibility with v1 modules)."""
    path = _find_config_path()
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def reload_config() -> AttentionConfig:
    """Force reload config (clears cache)."""
    load_config.cache_clear()
    return load_config()
