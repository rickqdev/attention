"""Platform formatter base class.

Pure text formatting -- char limits, tag rules, image count validation.
No network calls, no auth, no browser.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class FormattedPost:
    """Platform-formatted post output."""
    platform: str
    title: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PlatformFormatter(ABC):
    """Format copy output for a specific platform."""

    name: str = "unknown"
    max_title: int = 100
    max_content: int = 2000
    max_tags: int = 30
    max_images: int = 9

    def format(self, title: str, content: str, tags: list[str], images: list[str] | None = None) -> FormattedPost:
        """Apply platform constraints and return formatted post."""
        warnings = []
        images = images or []

        fmt_title = self._truncate(title, self.max_title, "title", warnings)
        fmt_content = self._truncate(content, self.max_content, "content", warnings)
        fmt_tags = self._limit_tags(tags, self.max_tags, warnings)
        fmt_images = self._limit_images(images, self.max_images, warnings)

        post = FormattedPost(
            platform=self.name,
            title=fmt_title,
            content=fmt_content,
            tags=fmt_tags,
            images=fmt_images,
            warnings=warnings,
        )
        self._platform_rules(post)
        return post

    def validate(self, post: FormattedPost) -> list[str]:
        """Return list of validation warnings."""
        issues = []
        if len(post.title) > self.max_title:
            issues.append(f"Title exceeds {self.max_title} chars ({len(post.title)})")
        if len(post.content) > self.max_content:
            issues.append(f"Content exceeds {self.max_content} chars ({len(post.content)})")
        if len(post.tags) > self.max_tags:
            issues.append(f"Too many tags: {len(post.tags)} > {self.max_tags}")
        if len(post.images) > self.max_images:
            issues.append(f"Too many images: {len(post.images)} > {self.max_images}")
        return issues

    def _truncate(self, text: str, limit: int, field_name: str, warnings: list[str]) -> str:
        if len(text) <= limit:
            return text
        warnings.append(f"{field_name} truncated: {len(text)} -> {limit} chars")
        return text[:limit]

    def _limit_tags(self, tags: list[str], limit: int, warnings: list[str]) -> list[str]:
        if len(tags) <= limit:
            return tags
        warnings.append(f"Tags trimmed: {len(tags)} -> {limit}")
        return tags[:limit]

    def _limit_images(self, images: list[str], limit: int, warnings: list[str]) -> list[str]:
        if len(images) <= limit:
            return images
        warnings.append(f"Images trimmed: {len(images)} -> {limit}")
        return images[:limit]

    @abstractmethod
    def _platform_rules(self, post: FormattedPost) -> None:
        """Apply platform-specific formatting rules. Modifies post in place."""
        ...
