"""Generic formatter (no platform constraints)."""

from .base import FormattedPost, PlatformFormatter


class GenericFormatter(PlatformFormatter):
    name = "generic"
    max_title = 200
    max_content = 5000
    max_tags = 50
    max_images = 20

    def _platform_rules(self, post: FormattedPost) -> None:
        pass  # No platform-specific rules
