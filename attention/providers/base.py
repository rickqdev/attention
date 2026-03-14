"""LLM provider abstract base and chain."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from attention.errors import AllProvidersFailedError, ProviderError

logger = logging.getLogger("attention.providers")


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    name: str = "unknown"
    supports_vision: bool = False

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        images: list[bytes | str] | None = None,
        temperature: float = 0.8,
        max_tokens: int = 8192,
    ) -> str:
        """Generate text from prompt, optionally with images."""
        ...

    def is_available(self) -> bool:
        """Check if this provider has valid credentials."""
        return True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} vision={self.supports_vision}>"


class ProviderChain:
    """Auto-fallback across multiple providers.

    Tries each provider in order. Skips providers that don't support
    vision when images are provided. Logs failures and continues.
    """

    def __init__(self, providers: list[LLMProvider]):
        self.providers = providers
        self._last_used: str = ""

    @property
    def last_used(self) -> str:
        return self._last_used

    async def generate(
        self,
        prompt: str,
        images: list[bytes | str] | None = None,
        temperature: float = 0.8,
        max_tokens: int = 8192,
    ) -> str:
        errors: list[str] = []
        for provider in self.providers:
            if not provider.is_available():
                continue
            if images and not provider.supports_vision:
                continue
            try:
                result = await provider.generate(
                    prompt, images=images, temperature=temperature, max_tokens=max_tokens,
                )
                if result and result.strip():
                    self._last_used = provider.name
                    return result
            except Exception as exc:
                msg = f"{provider.name} failed: {str(exc)[:120]}"
                logger.warning(msg)
                errors.append(msg)
        raise AllProvidersFailedError()

    def available_providers(self, need_vision: bool = False) -> list[LLMProvider]:
        return [
            p for p in self.providers
            if p.is_available() and (not need_vision or p.supports_vision)
        ]
