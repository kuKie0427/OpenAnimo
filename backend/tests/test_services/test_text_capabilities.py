from __future__ import annotations

import time

from app.services.text_capabilities import (
    TextProviderCapability,
    build_provider_capability_cache_key,
    get_cached_provider_capability,
    set_cached_provider_capability,
)


def test_build_provider_capability_cache_key():
    key = build_provider_capability_cache_key(
        provider="openai",
        text_base_url="https://example.com",
        text_model="gpt-4",
        text_endpoint="/chat/completions",
        anthropic_base_url=None,
        anthropic_model="claude-3",
        secret="sk-test",
    )
    assert "openai" in key
    assert "https://example.com" in key
    assert "gpt-4" in key


def test_build_provider_capability_cache_key_no_secret():
    key = build_provider_capability_cache_key(
        provider="openai",
        text_base_url="https://example.com",
        text_model="gpt-4",
        text_endpoint="/chat/completions",
        anthropic_base_url=None,
        anthropic_model="claude-3",
        secret=None,
    )
    assert "none" in key


def test_get_cached_provider_capability_miss():
    result = get_cached_provider_capability("nonexistent_key")
    assert result is None


def test_set_and_get_cached_provider_capability():
    cap = TextProviderCapability(
        status="valid",
        generate=True,
        stream=True,
    )
    key = "test_key"
    set_cached_provider_capability(key, cap, ttl_s=60.0)

    result = get_cached_provider_capability(key)
    assert result is not None
    assert result.status == "valid"
    assert result.generate is True
    assert result.stream is True


def test_get_cached_provider_capability_expired():
    cap = TextProviderCapability(
        status="valid",
        generate=True,
        stream=True,
    )
    key = "expired_key"
    # Set with 0 TTL
    _CAPABILITY_CACHE = {}
    from app.services import text_capabilities

    text_capabilities._CAPABILITY_CACHE[key] = (time.monotonic() - 1.0, cap)

    result = get_cached_provider_capability(key)
    assert result is None
    # Key should be cleaned up
    assert key not in text_capabilities._CAPABILITY_CACHE


def test_capability_dataclass_with_reason():
    cap = TextProviderCapability(
        status="invalid",
        generate=False,
        stream=False,
        reason_code="auth_failed",
        reason_message="Invalid API key",
    )
    assert cap.reason_code == "auth_failed"
    assert cap.reason_message == "Invalid API key"
