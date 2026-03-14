from .base import FormattedPost, PlatformFormatter
from .xiaohongshu import XiaohongshuFormatter
from .douyin import DouyinFormatter
from .weibo import WeiboFormatter
from .generic import GenericFormatter

FORMATTERS: dict[str, PlatformFormatter] = {
    "xiaohongshu": XiaohongshuFormatter(),
    "xhs": XiaohongshuFormatter(),
    "douyin": DouyinFormatter(),
    "weibo": WeiboFormatter(),
    "generic": GenericFormatter(),
}


def get_formatter(platform: str) -> PlatformFormatter:
    """Get formatter by platform name, fallback to generic."""
    return FORMATTERS.get(platform.lower(), FORMATTERS["generic"])


__all__ = [
    "FormattedPost",
    "PlatformFormatter",
    "XiaohongshuFormatter",
    "DouyinFormatter",
    "WeiboFormatter",
    "GenericFormatter",
    "get_formatter",
]
