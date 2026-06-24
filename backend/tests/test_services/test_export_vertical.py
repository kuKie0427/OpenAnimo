"""竖屏视频导出服务单元测试"""
from __future__ import annotations

import pytest


class TestExportVerticalService:
    """竖屏视频导出服务测试"""

    @pytest.fixture
    def service(self):
        from app.services.export_service import ExportService
        return ExportService()

    def test_export_service_init(self, service):
        assert service._http_client is None

    @pytest.mark.asyncio
    async def test_ffmpeg_not_found_raises_error(self, service, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda path: None)
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            await service.export_vertical_video("http://example.com/video.mp4")

    @pytest.mark.asyncio
    async def test_download_failure_raises_error(self, service, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda path: "/usr/bin/ffmpeg")
        with pytest.raises(RuntimeError, match="Failed to download video"):
            await service.export_vertical_video("")

    @pytest.mark.asyncio
    async def test_unsupported_aspect_ratio(self, service):
        with pytest.raises(ValueError, match="Unsupported target_aspect"):
            await service.export_vertical_video(
                video_url="http://example.com/video.mp4",
                target_aspect="4:3",
            )

    @pytest.mark.asyncio
    async def test_invalid_reframe_mode(self, service, monkeypatch):
        """reframe_mode 当前未校验，任意值都会透传。

        验证调用不同的 reframe_mode 不会因该参数本身而报错。
        """
        monkeypatch.setattr("shutil.which", lambda path: None)
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            await service.export_vertical_video(
                video_url="http://example.com/video.mp4",
                reframe_mode="face_tracking",
            )
