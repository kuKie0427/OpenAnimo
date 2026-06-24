from __future__ import annotations

import pytest

from app.config import Settings
from app.services.video_factory import create_video_service


def test_create_video_service_openai():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        video_provider="openai",
        video_base_url="https://video.example.com",
        video_endpoint="/v1/generate",
        video_api_key="test",
    )
    svc = create_video_service(settings)
    from app.services.video import VideoService

    assert isinstance(svc, VideoService)


def test_create_video_service_doubao():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        video_provider="doubao",
        video_base_url="https://ark.cn-beijing.volces.com/api/v3/contents/generations",
        video_endpoint="/v1/generate",
        video_api_key="test",
    )
    svc = create_video_service(settings)
    from app.services.doubao_video import DoubaoVideoService

    assert isinstance(svc, DoubaoVideoService)


def test_create_video_service_fake():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        video_provider="fake",
        fake_video_fixture_url="/static/videos/dev_clip.mp4",
    )
    svc = create_video_service(settings)
    from app.services.fake_video import FakeVideoService

    assert isinstance(svc, FakeVideoService)


def test_create_video_service_unsupported():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        video_provider="unsupported",
    )
    with pytest.raises(ValueError, match="Unsupported video provider"):
        create_video_service(settings)
