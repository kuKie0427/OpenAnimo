from __future__ import annotations

from pathlib import Path
import pytest

from app.config import Settings
from app.services.doubao_video import DoubaoVideoService, MAX_IMAGE_SIZE_BYTES


def make_settings(**overrides):
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        doubao_api_key=overrides.get("doubao_api_key", "doubao-key"),
        video_inline_local_images=overrides.get("video_inline_local_images", False),
    )


def test_get_headers_requires_api_key():
    svc = DoubaoVideoService(make_settings(doubao_api_key=""))

    with pytest.raises(ValueError, match="not configured"):
        svc._get_headers()


def test_inline_local_image_returns_original_when_not_local(monkeypatch):
    svc = DoubaoVideoService(make_settings())
    monkeypatch.setattr("app.services.doubao_video.get_local_path", lambda url: None)

    assert svc._inline_local_image("https://example.com/a.png") == "https://example.com/a.png"


def test_inline_local_image_rejects_too_large_file(monkeypatch, tmp_path: Path):
    svc = DoubaoVideoService(make_settings())
    file_path = tmp_path / "a.png"
    file_path.write_bytes(b"x" * (MAX_IMAGE_SIZE_BYTES + 1))
    monkeypatch.setattr("app.services.doubao_video.get_local_path", lambda url: file_path)

    with pytest.raises(ValueError, match="too large"):
        svc._inline_local_image("/static/a.png")


def test_is_retryable_status_matches_http_codes():
    svc = DoubaoVideoService(make_settings())

    assert svc._is_retryable_status(429) is True
    assert svc._is_retryable_status(400) is False


@pytest.mark.asyncio
async def test_request_with_retry_returns_json_on_success(monkeypatch):
    svc = DoubaoVideoService(make_settings(), max_retries=1)

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, headers, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.services.doubao_video.httpx.AsyncClient", lambda *args, **kwargs: FakeClient())

    assert await svc._request_with_retry("POST", "https://example.com") == {"ok": True}


@pytest.mark.asyncio
async def test_request_with_retry_retries_on_retryable_status(monkeypatch):
    svc = DoubaoVideoService(make_settings(), max_retries=1)

    class RetryResponse:
        status_code = 500

        def raise_for_status(self):
            raise RuntimeError("should not reach")

        def json(self):
            return {}

    class OkResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    calls = {"n": 0}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, headers, **kwargs):
            calls["n"] += 1
            return RetryResponse() if calls["n"] == 1 else OkResponse()

    monkeypatch.setattr("app.services.doubao_video.httpx.AsyncClient", lambda *args, **kwargs: FakeClient())
    async def noop_sleep(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.doubao_video.asyncio.sleep", noop_sleep)

    assert await svc._request_with_retry("POST", "https://example.com") == {"ok": True}
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_create_task_inlines_local_image_and_returns_task_id(monkeypatch, tmp_path):
    svc = DoubaoVideoService(make_settings(video_inline_local_images=True))
    file_path = tmp_path / "a.png"
    file_path.write_bytes(b"abc")
    monkeypatch.setattr("app.services.doubao_video.get_local_path", lambda url: file_path)

    seen = {}

    async def fake_request(method, url, **kwargs):
        seen.update(kwargs["json"])
        return {"id": "task-1"}

    monkeypatch.setattr(svc, "_request_with_retry", fake_request)

    task_id = await svc.create_task(prompt="make video", image_url="/static/a.png", duration=10, ratio="16:9")

    assert task_id == "task-1"
    assert seen["content"][0]["text"].startswith("make video")
    assert seen["content"][1]["image_url"]["role"] == "first_frame"


@pytest.mark.asyncio
async def test_create_task_raises_when_task_id_missing(monkeypatch):
    svc = DoubaoVideoService(make_settings())

    async def fake_request(method, url, **kwargs):
        return {"foo": "bar"}

    monkeypatch.setattr(svc, "_request_with_retry", fake_request)

    with pytest.raises(RuntimeError, match="missing task ID"):
        await svc.create_task(prompt="make video")


@pytest.mark.asyncio
async def test_wait_for_completion_returns_on_succeeded(monkeypatch):
    svc = DoubaoVideoService(make_settings(), poll_interval=0.0, max_poll_time=10.0)
    results = iter([
        {"status": svc.STATUS_RUNNING},
        {"status": svc.STATUS_SUCCEEDED, "data": {"url": "https://cdn.example.com/a.mp4"}},
    ])

    async def fake_query(task_id):
        return next(results)

    monkeypatch.setattr(svc, "query_task", fake_query)
    async def noop_sleep(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.doubao_video.asyncio.sleep", noop_sleep)

    result = await svc.wait_for_completion("task-1")

    assert result["status"] == svc.STATUS_SUCCEEDED


@pytest.mark.asyncio
async def test_wait_for_completion_times_out(monkeypatch):
    svc = DoubaoVideoService(make_settings(), poll_interval=0.0, max_poll_time=0.0)

    async def fake_query(task_id):
        return {"status": svc.STATUS_RUNNING}

    monkeypatch.setattr(svc, "query_task", fake_query)

    with pytest.raises(TimeoutError, match="timed out"):
        await svc.wait_for_completion("task-1")


@pytest.mark.asyncio
async def test_generate_url_from_bytes_too_large():
    svc = DoubaoVideoService(make_settings())
    big = b"x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="Image too large"):
        await svc.generate_url_from_bytes(prompt="p", image_bytes=big)


@pytest.mark.asyncio
async def test_generate_url_from_bytes_creates_data_uri(monkeypatch):
    svc = DoubaoVideoService(make_settings())
    captured = {}

    async def fake_generate_url(*, prompt, image_url, **kw):
        captured["image_url"] = image_url
        captured["prompt"] = prompt
        return "https://video.example.com/out.mp4"

    monkeypatch.setattr(svc, "generate_url", fake_generate_url)
    result = await svc.generate_url_from_bytes(prompt="a cat running", image_bytes=b"\x89PNG")
    assert result == "https://video.example.com/out.mp4"
    assert captured["image_url"].startswith("data:image/png;base64,")
    assert captured["prompt"] == "a cat running"


@pytest.mark.asyncio
async def test_merge_urls_requires_urls():
    svc = DoubaoVideoService(make_settings())

    with pytest.raises(RuntimeError, match="No video URLs"):
        await svc.merge_urls([])


# --- _request_with_retry error paths ---


@pytest.mark.asyncio
async def test_request_with_retry_breaks_on_non_retryable_http_error(monkeypatch):
    svc = DoubaoVideoService(make_settings(), max_retries=2)
    call_count = {"n": 0}

    class ForbiddenResponse:
        status_code = 403

        def raise_for_status(self):
            import httpx

            raise httpx.HTTPStatusError("403", request=None, response=self)

        def json(self):
            return {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, headers, **kwargs):
            call_count["n"] += 1
            return ForbiddenResponse()

    monkeypatch.setattr("app.services.doubao_video.httpx.AsyncClient", lambda *a, **k: FakeClient())

    with pytest.raises(RuntimeError, match="request failed after retries"):
        await svc._request_with_retry("POST", "https://example.com")
    assert call_count["n"] == 1  # broke immediately on non-retryable


@pytest.mark.asyncio
async def test_request_with_retry_raises_after_all_retries_exhausted(monkeypatch):
    svc = DoubaoVideoService(make_settings(), max_retries=0)

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, headers, **kwargs):
            import httpx

            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("app.services.doubao_video.httpx.AsyncClient", lambda *a, **k: FakeClient())

    with pytest.raises(RuntimeError, match="request failed after retries"):
        await svc._request_with_retry("POST", "https://example.com")


@pytest.mark.asyncio
async def test_request_with_retry_retries_on_network_error(monkeypatch):
    svc = DoubaoVideoService(make_settings(), max_retries=1)
    call_count = {"n": 0}

    class OkResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, headers, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                import httpx

                raise httpx.NetworkError("connection reset")
            return OkResponse()

    async def noop_sleep(*a, **k):
        return None

    monkeypatch.setattr("app.services.doubao_video.httpx.AsyncClient", lambda *a, **k: FakeClient())
    monkeypatch.setattr("app.services.doubao_video.asyncio.sleep", noop_sleep)

    result = await svc._request_with_retry("POST", "https://example.com")
    assert result == {"ok": True}
    assert call_count["n"] == 2


# --- query_task ---


@pytest.mark.asyncio
async def test_query_task_calls_request_with_retry(monkeypatch):
    svc = DoubaoVideoService(make_settings())
    seen = {}

    async def fake_request(method, url, **kwargs):
        seen["method"] = method
        seen["url"] = url
        return {"status": "running", "id": "task-1"}

    monkeypatch.setattr(svc, "_request_with_retry", fake_request)

    result = await svc.query_task("task-1")
    assert result["status"] == "running"
    assert seen["method"] == "GET"
    assert "task-1" in seen["url"]


# --- wait_for_completion edge cases ---


@pytest.mark.asyncio
async def test_wait_for_completion_on_progress_callback_invoked(monkeypatch):
    svc = DoubaoVideoService(make_settings(), poll_interval=0.0, max_poll_time=10.0)
    results = iter([
        {"status": svc.STATUS_RUNNING},
        {"status": svc.STATUS_SUCCEEDED, "content": {"video_url": "https://cdn.example.com/a.mp4"}},
    ])

    async def fake_query(task_id):
        return next(results)

    monkeypatch.setattr(svc, "query_task", fake_query)

    async def noop_sleep(*a, **k):
        return None

    monkeypatch.setattr("app.services.doubao_video.asyncio.sleep", noop_sleep)

    progress_calls = []

    def on_progress(status, progress):
        progress_calls.append((status, progress))

    result = await svc.wait_for_completion("task-1", on_progress=on_progress)
    assert result["status"] == svc.STATUS_SUCCEEDED
    assert len(progress_calls) >= 1


@pytest.mark.asyncio
async def test_wait_for_completion_on_progress_callback_error_swallowed(monkeypatch):
    svc = DoubaoVideoService(make_settings(), poll_interval=0.0, max_poll_time=10.0)
    results = iter([
        {"status": svc.STATUS_SUCCEEDED, "content": {"video_url": "https://cdn.example.com/a.mp4"}},
    ])

    async def fake_query(task_id):
        return next(results)

    monkeypatch.setattr(svc, "query_task", fake_query)

    async def noop_sleep(*a, **k):
        return None

    monkeypatch.setattr("app.services.doubao_video.asyncio.sleep", noop_sleep)

    def bad_callback(status, progress):
        raise ValueError("boom")

    # Should not raise — callback error is swallowed
    result = await svc.wait_for_completion("task-1", on_progress=bad_callback)
    assert result["status"] == svc.STATUS_SUCCEEDED


@pytest.mark.asyncio
async def test_wait_for_completion_raises_on_failed_status(monkeypatch):
    svc = DoubaoVideoService(make_settings(), poll_interval=0.0, max_poll_time=10.0)

    async def fake_query(task_id):
        return {"status": svc.STATUS_FAILED, "error": {"message": "bad input"}}

    monkeypatch.setattr(svc, "query_task", fake_query)

    with pytest.raises(RuntimeError, match="task failed"):
        await svc.wait_for_completion("task-1")


@pytest.mark.asyncio
async def test_wait_for_completion_raises_on_cancelled_status(monkeypatch):
    svc = DoubaoVideoService(make_settings(), poll_interval=0.0, max_poll_time=10.0)

    async def fake_query(task_id):
        return {"status": svc.STATUS_CANCELLED}

    monkeypatch.setattr(svc, "query_task", fake_query)

    with pytest.raises(RuntimeError, match="was cancelled"):
        await svc.wait_for_completion("task-1")


# --- generate_url full path ---


@pytest.mark.asyncio
async def test_generate_url_extracts_video_url_from_content(monkeypatch):
    svc = DoubaoVideoService(make_settings())

    async def fake_create_task(**kwargs):
        return "task-1"

    async def fake_wait(task_id, on_progress=None):
        return {"status": "succeeded", "content": {"video_url": "https://cdn.example.com/a.mp4"}}

    monkeypatch.setattr(svc, "create_task", fake_create_task)
    monkeypatch.setattr(svc, "wait_for_completion", fake_wait)

    url = await svc.generate_url(prompt="make video")
    assert url == "https://cdn.example.com/a.mp4"


@pytest.mark.asyncio
async def test_generate_url_falls_back_to_url_field(monkeypatch):
    svc = DoubaoVideoService(make_settings())

    async def fake_create_task(**kwargs):
        return "task-1"

    async def fake_wait(task_id, on_progress=None):
        return {"status": "succeeded", "content": {"url": "https://cdn.example.com/b.mp4"}}

    monkeypatch.setattr(svc, "create_task", fake_create_task)
    monkeypatch.setattr(svc, "wait_for_completion", fake_wait)

    url = await svc.generate_url(prompt="make video")
    assert url == "https://cdn.example.com/b.mp4"


@pytest.mark.asyncio
async def test_generate_url_raises_when_no_video_url_found(monkeypatch):
    svc = DoubaoVideoService(make_settings())

    async def fake_create_task(**kwargs):
        return "task-1"

    async def fake_wait(task_id, on_progress=None):
        return {"status": "succeeded", "content": {}}

    monkeypatch.setattr(svc, "create_task", fake_create_task)
    monkeypatch.setattr(svc, "wait_for_completion", fake_wait)

    with pytest.raises(RuntimeError, match="missing video URL"):
        await svc.generate_url(prompt="make video")
