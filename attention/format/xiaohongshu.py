"""Xiaohongshu (XHS) formatter."""

from .base import FormattedPost, PlatformFormatter


class XiaohongshuFormatter(PlatformFormatter):
    name = "xiaohongshu"
    max_title = 20
    max_content = 1000
    max_tags = 30
    max_images = 9

    def _platform_rules(self, post: FormattedPost) -> None:
        if not post.title:
            post.warnings.append("XHS requires a title")

        # XHS prefers 3:4 aspect ratio images (noted as warning, can't enforce)
        if post.images and len(post.images) > 0:
            pass  # Image aspect ratio is caller's concern

        # Tags should use # prefix without spaces in tag text
        cleaned = []
        for tag in post.tags:
            tag = tag.strip()
            if not tag.startswith("#"):
                tag = f"#{tag}"
            cleaned.append(tag)
        post.tags = cleaned
