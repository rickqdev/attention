"""Douyin formatter."""

from .base import FormattedPost, PlatformFormatter


class DouyinFormatter(PlatformFormatter):
    name = "douyin"
    max_title = 55
    max_content = 2200
    max_tags = 20
    max_images = 35  # Douyin image mode supports more

    def _platform_rules(self, post: FormattedPost) -> None:
        # Douyin tags use # prefix
        cleaned = []
        for tag in post.tags:
            tag = tag.strip()
            if not tag.startswith("#"):
                tag = f"#{tag}"
            # Douyin tags end with a space
            cleaned.append(tag)
        post.tags = cleaned
