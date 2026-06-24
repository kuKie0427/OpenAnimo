from __future__ import annotations

import pytest

from app.services.video_merger import VideoMergerService


def test_merge_videos_requires_urls(tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)
    with pytest.raises(ValueError, match="No video URLs"):
        import asyncio

        asyncio.run(svc.merge_videos([]))


@pytest.mark.asyncio
async def test_merge_videos_normalizes_single_url(monkeypatch, tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)

    async def fake_download(url, dest):
        dest.write_bytes(b"data")

    monkeypatch.setattr(svc, "download_video", fake_download)

    assert await svc.merge_videos(["https://cdn.example.com/a.mp4"], output_filename="single") == "/static/videos/single.mp4"
    assert (tmp_path / "single.mp4").read_bytes() == b"data"


@pytest.mark.asyncio
async def test_merge_videos_writes_output_and_uses_ffmpeg(monkeypatch, tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)

    async def fake_download(url, dest):
        dest.write_bytes(b"data")

    class FakeProc:
        returncode = 0

        async def communicate(self):
            return b"", b""

    async def fake_exec(*args, **kwargs):
        return FakeProc()

    monkeypatch.setattr(svc, "download_video", fake_download)
    monkeypatch.setattr("app.services.video_merger.asyncio.create_subprocess_exec", fake_exec)

    result = await svc.merge_videos(["https://cdn.example.com/a.mp4", "https://cdn.example.com/b.mp4"], output_filename="merged")

    assert result == "/static/videos/merged.mp4"


@pytest.mark.asyncio
async def test_merge_videos_reencodes_on_ffmpeg_copy_failure(monkeypatch, tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)

    async def fake_download(url, dest):
        dest.write_bytes(b"data")

    class FakeFailProc:
        returncode = 1

        async def communicate(self):
            return b"", b"copy failed"

    class FakeOkProc:
        returncode = 0

        async def communicate(self):
            return b"", b""

    procs = [FakeFailProc(), FakeOkProc()]

    async def fake_exec(*args, **kwargs):
        return procs.pop(0)

    monkeypatch.setattr(svc, "download_video", fake_download)
    monkeypatch.setattr("app.services.video_merger.asyncio.create_subprocess_exec", fake_exec)

    result = await svc.merge_videos(["https://cdn.example.com/a.mp4", "https://cdn.example.com/b.mp4"], output_filename="merged")

    assert result == "/static/videos/merged.mp4"


@pytest.mark.asyncio
async def test_merge_videos_raises_when_reencode_fails(monkeypatch, tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)

    async def fake_download(url, dest):
        dest.write_bytes(b"data")

    class FakeFailProc:
        returncode = 1

        async def communicate(self):
            return b"", b"copy failed"

    monkeypatch.setattr(svc, "download_video", fake_download)
    async def fake_exec(*args, **kwargs):
        return FakeFailProc()

    monkeypatch.setattr("app.services.video_merger.asyncio.create_subprocess_exec", fake_exec)

    with pytest.raises(RuntimeError, match="ffmpeg failed"):
        await svc.merge_videos(["https://cdn.example.com/a.mp4", "https://cdn.example.com/b.mp4"], output_filename="merged")


@pytest.mark.asyncio
async def test_get_client_creates_new_client(tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)
    assert svc._client is None
    client = await svc._get_client()
    assert client is not None
    assert svc._client is client


@pytest.mark.asyncio
async def test_get_client_reuses_existing(tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)
    client1 = await svc._get_client()
    client2 = await svc._get_client()
    assert client1 is client2


@pytest.mark.asyncio
async def test_get_client_creates_new_when_closed(tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)
    client1 = await svc._get_client()
    await svc.close()
    assert svc._client is None
    client2 = await svc._get_client()
    assert client2 is not None
    assert client2 is not client1


@pytest.mark.asyncio
async def test_close(tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)
    await svc._get_client()
    assert svc._client is not None
    await svc.close()
    assert svc._client is None


@pytest.mark.asyncio
async def test_close_when_no_client(tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)
    await svc.close()  # should not raise
    assert svc._client is None


@pytest.mark.asyncio
async def test_close_when_already_closed(tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)
    await svc._get_client()
    await svc.close()
    await svc.close()  # should not raise


@pytest.mark.asyncio
async def test_download_video_copies_local_static_file(monkeypatch, tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)
    source = tmp_path / "source.mp4"
    source.write_bytes(b"local-video")
    dest = tmp_path / "dest.mp4"

    monkeypatch.setattr("app.services.video_merger.get_local_path", lambda url: source)

    await svc.download_video("/static/videos/source.mp4", dest)

    assert dest.read_bytes() == b"local-video"


@pytest.mark.asyncio
async def test_download_video(tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)

    class FakeStreamResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        async def aiter_bytes(self, chunk_size=8192):
            yield b"video_data_chunk1"
            yield b"video_data_chunk2"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeClient:
        is_closed = False

        def stream(self, method, url):
            return FakeStreamResponse()

    svc._client = FakeClient()
    dest = tmp_path / "test.mp4"
    await svc.download_video("https://cdn.example.com/video.mp4", dest)
    assert dest.exists()
    assert dest.read_bytes() == b"video_data_chunk1video_data_chunk2"


def test_get_video_merger_service_singleton():
    import app.services.video_merger as vm_module

    # Reset singleton
    original = vm_module._merger_service
    vm_module._merger_service = None
    try:
        svc1 = vm_module.get_video_merger_service()
        svc2 = vm_module.get_video_merger_service()
        assert svc1 is svc2
    finally:
        vm_module._merger_service = original


@pytest.mark.asyncio
async def test_merge_videos_infer_extension_from_query_string(monkeypatch, tmp_path):
    svc = VideoMergerService(output_dir=tmp_path)

    async def fake_download(url, dest):
        dest.write_bytes(b"data")

    class FakeProc:
        returncode = 0

        async def communicate(self):
            return b"", b""

    async def fake_exec(*args, **kwargs):
        return FakeProc()

    monkeypatch.setattr(svc, "download_video", fake_download)
    monkeypatch.setattr("app.services.video_merger.asyncio.create_subprocess_exec", fake_exec)

    result = await svc.merge_videos(
        ["https://cdn.example.com/a.mp4?token=abc", "https://cdn.example.com/b.mp4?token=xyz"],
        output_filename="merged",
    )
    assert result == "/static/videos/merged.mp4"
