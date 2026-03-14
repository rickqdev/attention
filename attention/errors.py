"""Typed error hierarchy for attention v2."""

from __future__ import annotations


class AttentionError(Exception):
    """Base error for all attention operations."""

    code: str = "unknown"

    def __init__(self, message: str, suggestions: list[str] | None = None):
        super().__init__(message)
        self.suggestions = suggestions or []


class MissingAPIKeyError(AttentionError):
    code = "missing_api_key"


class VisionAnalysisError(AttentionError):
    code = "vision_analysis_failed"


class CopyGenerationError(AttentionError):
    code = "copy_generation_failed"


class ProviderError(AttentionError):
    code = "provider_error"


class AllProvidersFailedError(AttentionError):
    code = "all_providers_failed"

    def __init__(self):
        super().__init__("All configured providers failed.")


class ImageNotFoundError(AttentionError):
    code = "image_not_found"


class InvalidImageError(AttentionError):
    code = "invalid_image"


class PipelineAbortedError(AttentionError):
    code = "pipeline_aborted"


class PlatformError(AttentionError):
    code = "platform_error"


class SessionExpiredError(PlatformError):
    code = "session_expired"
