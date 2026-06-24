from __future__ import annotations

from app.config import Settings, apply_settings_overrides, get_settings


# --- anthropic_env ---


def test_anthropic_env_all_fields():
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        anthropic_api_key="key-1",
        anthropic_auth_token="token-2",
        anthropic_base_url="https://example.com",
    )
    env = s.anthropic_env()
    assert env == {
        "ANTHROPIC_API_KEY": "key-1",
        "ANTHROPIC_AUTH_TOKEN": "token-2",
        "ANTHROPIC_BASE_URL": "https://example.com",
    }


def test_anthropic_env_empty():
    s = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert s.anthropic_env() == {}


# --- build_public_url ---


def test_build_public_url_none_path():
    s = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert s.build_public_url(None) is None


def test_build_public_url_empty_path():
    s = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert s.build_public_url("") == ""


def test_build_public_url_already_absolute():
    s = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert s.build_public_url("https://cdn.example.com/img.png") == "https://cdn.example.com/img.png"


def test_build_public_url_http():
    s = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert s.build_public_url("http://cdn.example.com/img.png") == "http://cdn.example.com/img.png"


def test_build_public_url_no_base():
    s = Settings(database_url="sqlite+aiosqlite:///:memory:")
    assert s.build_public_url("/static/img.png") == "/static/img.png"


def test_build_public_url_with_base():
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        public_base_url="https://api.example.com",
    )
    assert s.build_public_url("/static/img.png") == "https://api.example.com/static/img.png"


def test_build_public_url_no_leading_slash():
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        public_base_url="https://api.example.com",
    )
    assert s.build_public_url("static/img.png") == "https://api.example.com/static/img.png"


def test_build_public_url_trailing_slash():
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        public_base_url="https://api.example.com/",
    )
    assert s.build_public_url("/static/img.png") == "https://api.example.com/static/img.png"


# --- text_headers ---


def test_text_headers_with_key():
    s = Settings(database_url="sqlite+aiosqlite:///:memory:", text_api_key="sk-test")
    headers = s.text_headers()
    assert headers["Authorization"] == "Bearer sk-test"


def test_text_headers_no_key():
    s = Settings(database_url="sqlite+aiosqlite:///:memory:")
    headers = s.text_headers()
    assert "Authorization" not in headers


# --- image_headers ---


def test_image_headers_with_key():
    s = Settings(database_url="sqlite+aiosqlite:///:memory:", image_api_key="img-key")
    headers = s.image_headers()
    assert headers["Authorization"] == "Bearer img-key"


# --- video_headers ---


def test_video_headers_with_key():
    s = Settings(database_url="sqlite+aiosqlite:///:memory:", video_api_key="vid-key")
    headers = s.video_headers()
    assert headers["Authorization"] == "Bearer vid-key"


# --- apply_settings_overrides ---


def test_apply_settings_overrides_empty():
    """Empty overrides should be no-op."""
    apply_settings_overrides({})


def test_apply_settings_overrides_updates_field(monkeypatch):
    settings = get_settings()
    original_app_name = settings.app_name
    try:
        apply_settings_overrides({"app_name": "TestOverride"})
        assert get_settings().app_name == "TestOverride"
    finally:
        settings.app_name = original_app_name


# --- enable_image_to_video property ---


def test_enable_image_to_video_property():
    s = Settings(database_url="sqlite+aiosqlite:///:memory:", enable_image_to_video=True)
    assert s.enable_image_to_video is True
