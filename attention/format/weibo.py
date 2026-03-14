"""Weibo formatter."""

from .base import FormattedPost, PlatformFormatter


class WeiboFormatter(PlatformFormatter):
    name = "weibo"
    max_title = 0  # Weibo has no separate title field
    max_content = 2000
    max_tags = 10
    max_images = 9

    def _platform_rules(self, post: FormattedPost) -> None:
        # Weibo has no title -- merge title into content
        if post.title:
            post.content = f"{post.title}\n\n{post.content}"
            post.title = ""

        # Weibo tags use #tag# format (double hash)
        cleaned = []
        for tag in post.tags:
            tag = tag.strip().strip("#")
            if tag:
                cleaned.append(f"#{tag}#")
        post.tags = cleaned
