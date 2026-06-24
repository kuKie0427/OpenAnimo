from __future__ import annotations

import hashlib
import html
from pathlib import Path
from typing import Any

from app.config import Settings

STATIC_IMAGE_DIR = Path(__file__).parent.parent / "static" / "images"
DEFAULT_FAKE_IMAGE_FILENAME = "fake_provider_placeholder.svg"

DEFAULT_FAKE_IMAGE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
<rect width="1024" height="1024" fill="#f4f4f5"/>
<rect x="80" y="80" width="864" height="864" rx="48" fill="none" stroke="#71717a" stroke-width="24" stroke-dasharray="40 24"/>
<text x="512" y="470" text-anchor="middle" font-family="system-ui, sans-serif" font-size="72" font-weight="700" fill="#3f3f46">Fake Image</text>
<text x="512" y="560" text-anchor="middle" font-family="system-ui, sans-serif" font-size="34" fill="#71717a">local test mode · no API call</text>
</svg>"""

FAKE_PALETTES = (
    ("#111827", "#2563eb", "#fbbf24"),
    ("#1e1b4b", "#7c3aed", "#22d3ee"),
    ("#422006", "#f97316", "#fde68a"),
    ("#052e16", "#16a34a", "#a7f3d0"),
    ("#3b0764", "#db2777", "#fbcfe8"),
    ("#0f172a", "#64748b", "#e2e8f0"),
)


def _safe_slug(text: str, *, fallback: str = "prompt") -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{fallback}_{digest}.svg"


def _prompt_label(prompt: str) -> str:
    compact = " ".join(prompt.split())
    if not compact:
        return "本地 Fake 占位图"
    return compact[:42]


def _placeholder_svg(prompt: str) -> str:
    digest = int(hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:8], 16)
    bg, accent, ink = FAKE_PALETTES[digest % len(FAKE_PALETTES)]
    label = html.escape(_prompt_label(prompt))
    index = digest % 97 + 1
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
<defs>
  <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
    <path d="M 48 0 L 0 0 0 48" fill="none" stroke="rgba(255,255,255,0.10)" stroke-width="2"/>
  </pattern>
</defs>
<rect width="1024" height="1024" fill="{bg}"/>
<rect width="1024" height="1024" fill="url(#grid)"/>
<circle cx="790" cy="210" r="150" fill="{accent}" opacity="0.25"/>
<circle cx="250" cy="760" r="190" fill="{ink}" opacity="0.18"/>
<rect x="88" y="88" width="848" height="848" rx="56" fill="none" stroke="{accent}" stroke-width="18" stroke-dasharray="36 22"/>
<rect x="148" y="640" width="728" height="196" rx="36" fill="rgba(0,0,0,0.34)" stroke="rgba(255,255,255,0.20)"/>
<text x="512" y="310" text-anchor="middle" font-family="system-ui, sans-serif" font-size="76" font-weight="800" fill="white">Fake Image</text>
<text x="512" y="390" text-anchor="middle" font-family="system-ui, sans-serif" font-size="32" fill="{ink}">local placeholder · no API call</text>
<text x="512" y="555" text-anchor="middle" font-family="system-ui, sans-serif" font-size="140" font-weight="900" fill="{accent}" opacity="0.92">#{index:02d}</text>
<text x="512" y="715" text-anchor="middle" font-family="system-ui, sans-serif" font-size="34" font-weight="700" fill="white">{label}</text>
<text x="512" y="770" text-anchor="middle" font-family="system-ui, sans-serif" font-size="26" fill="rgba(255,255,255,0.72)">占位图片 / 本地测试 / 不扣费</text>
</svg>"""


class FakeImageService:
    """Local/dev image provider that never calls external APIs."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate(self, **kwargs: Any) -> dict[str, Any]:
        url = await self.generate_url(prompt=str(kwargs.get("prompt", "test")))
        return {"data": [{"url": url}], "provider": "fake"}

    async def generate_url(
        self,
        *,
        prompt: str,
        size: str = "1024x1024",
        image_bytes: bytes | None = None,
        **kwargs: Any,
    ) -> str:
        fixture_url = (self.settings.fake_image_fixture_url or "").strip()
        if fixture_url:
            return fixture_url

        STATIC_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        if prompt and prompt.strip():
            filename = _safe_slug(prompt, fallback="fake_image")
            placeholder = STATIC_IMAGE_DIR / filename
            svg = _placeholder_svg(prompt)
            if not placeholder.exists() or placeholder.read_text(encoding="utf-8") != svg:
                placeholder.write_text(svg, encoding="utf-8")
            return f"/static/images/{filename}"

        placeholder = STATIC_IMAGE_DIR / DEFAULT_FAKE_IMAGE_FILENAME
        if not placeholder.exists() or placeholder.read_text(encoding="utf-8") != DEFAULT_FAKE_IMAGE_SVG:
            placeholder.write_text(DEFAULT_FAKE_IMAGE_SVG, encoding="utf-8")
        return f"/static/images/{DEFAULT_FAKE_IMAGE_FILENAME}"

    async def cache_external_image(self, url: str) -> str:
        return url
