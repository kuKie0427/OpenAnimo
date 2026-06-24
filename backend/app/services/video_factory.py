"""视频服务工厂

根据配置选择使用 OpenAI 兼容接口或豆包视频服务。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.config import Settings


@runtime_checkable
class VideoServiceProtocol(Protocol):
    """视频服务协议（接口定义）"""

    async def generate_url(
        self,
        *,
        prompt: str,
        image_bytes: bytes | None = None,
        image_url: str | None = None,
        **kwargs: Any,
    ) -> str:
        """生成视频并返回 URL

        Args:
            prompt: 视频描述文本
            image_bytes: 参考图片字节流（图生视频模式，OpenAI 兼容接口）
            image_url: 参考图片 URL（图生视频模式，豆包接口）
            **kwargs: 其他参数

        Returns:
            生成的视频 URL
        """
        ...

    async def merge_urls(self, video_urls: list[str]) -> str:
        """拼接多个视频 URL

        Args:
            video_urls: 要拼接的视频 URL 列表

        Returns:
            拼接后的视频 URL
        """
        ...


def create_video_service(settings: Settings) -> VideoServiceProtocol:
    """根据配置创建视频服务实例

    Args:
        settings: 应用配置

    Returns:
        视频服务实例（OpenAI 兼容或豆包）
    """
    provider = settings.video_provider.lower()

    if provider == "doubao":
        from app.services.doubao_video import DoubaoVideoService

        return DoubaoVideoService(settings)
    if provider == "openai":
        from app.services.video import VideoService

        return VideoService(settings)
    if provider == "fake":
        from app.services.fake_video import FakeVideoService

        return FakeVideoService(settings)
    raise ValueError(f"Unsupported video provider: {settings.video_provider}")
