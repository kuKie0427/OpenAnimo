from __future__ import annotations

from dataclasses import dataclass
import hashlib
import time
from typing import Literal


ProviderStatus = Literal["valid", "degraded", "invalid"]


@dataclass(slots=True)
class TextProviderCapability:
    status: ProviderStatus
    generate: bool
    stream: bool
    reason_code: str | None = None
    reason_message: str | None = None


_CAPABILITY_CACHE: dict[str, tuple[float, TextProviderCapability]] = {}


def build_provider_capability_cache_key(
    *,
    provider: str,
    text_base_url: str,
    text_model: str,
    text_endpoint: str,
    anthropic_base_url: str | None,
    anthropic_model: str,
    secret: str | None,
) -> str:
    secret_hash = hashlib.sha256((secret or "").encode("utf-8")).hexdigest()[:12] if secret else "none"
    return "|".join(
        [
            provider,
            text_base_url,
            text_model,
            text_endpoint,
            anthropic_base_url or "",
            anthropic_model,
            secret_hash,
        ]
    )


def get_cached_provider_capability(cache_key: str) -> TextProviderCapability | None:
    cached = _CAPABILITY_CACHE.get(cache_key)
    if cached is None:
        return None
    expires_at, result = cached
    if expires_at <= time.monotonic():
        _CAPABILITY_CACHE.pop(cache_key, None)
        return None
    return result


def set_cached_provider_capability(
    cache_key: str, result: TextProviderCapability, *, ttl_s: float
) -> TextProviderCapability:
    _CAPABILITY_CACHE[cache_key] = (time.monotonic() + ttl_s, result)
    return result
