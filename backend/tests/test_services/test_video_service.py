from __future__ import annotations

import pytest

from app.config import Settings
from app.services import video_merger
from app.services.video import VideoService


def test_build_url():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        video_base_url="https://video.example.com/",
        video_endpoint="videos/generations",
    )
    service = VideoService(settings)
    assert service._build_url() == "https://video.example.com/videos/generations"


@pytest.mark.asyncio
async def test_generate_url_standard(monkeypatch):
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        video_base_url="https://video.example.com",
        video_endpoint="/videos/generations",
        video_api_key="test",
    )
    service = VideoService(settings)

    async def fake_post(url, payload):
        return {"data": [{"url": "https://cdn.example.com/video.mp4"}]}

    monkeypatch.setattr(service, "_post_json_with_retry", fake_post)

    url = await service.generate_url(prompt="scene")
    assert url == "https://cdn.example.com/video.mp4"


@pytest.mark.asyncio
async def test_generate_url_chat_completions(monkeypatch):
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        video_base_url="https://video.example.com",
        video_endpoint="/chat/completions",
        video_api_key="test",
    )
    service = VideoService(settings)

    async def fake_stream(url, payload):
        return "result https://cdn.example.com/stream.mp4 done"

    monkeypatch.setattr(service, "_post_stream_with_retry", fake_stream)

    url = await service.generate_url(prompt="scene")
    assert url == "https://cdn.example.com/stream.mp4"


@pytest.mark.asyncio
async def test_generate_url_i2v(monkeypatch):
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        video_base_url="https://video.example.com",
        video_endpoint="/videos/generations",
        video_api_key="test",
        enable_image_to_video=True,
    )
    service = VideoService(settings)

    async def fake_post(url, payload):
        return {"data": [{"url": "https://cdn.example.com/i2v.mp4"}]}

    monkeypatch.setattr(service, "_post_json_with_retry", fake_post)

    url = await service.generate_url(prompt="scene", image_bytes=b"fake")
    assert url == "https://cdn.example.com/i2v.mp4"


@pytest.mark.asyncio
async def test_merge_urls(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    service = VideoService(settings)

    class StubMerger:
        async def merge_videos(self, urls):
            return "/static/videos/merged.mp4"

    monkeypatch.setattr(video_merger, "get_video_merger_service", lambda: StubMerger())

    url = await service.merge_urls(["https://cdn.example.com/1.mp4", "https://cdn.example.com/2.mp4"])
    assert url == "/static/videos/merged.mp4"
