"""Fake video service for local development and tests.

This provider never calls external video APIs. It can use a configured fixture,
but also creates a tiny local MP4 automatically so browser tests can run without
paid video APIs or extra manual setup.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.file_cleaner import get_local_path
from app.services.video_merger import get_video_merger_service

logger = logging.getLogger(__name__)

STATIC_VIDEO_DIR = Path(__file__).parent.parent / "static" / "videos"
DEFAULT_FAKE_VIDEO_FILENAME = "fake_provider_clip.mp4"
FAKE_VIDEO_COLORS = ("0x111827", "0x1e1b4b", "0x422006", "0x052e16", "0x3b0764", "0x0f172a")


def _video_slug(prompt: str, *, prefix: str = "fake_video") -> str:
    digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}.mp4"


def _prompt_label(prompt: str) -> str:
    compact = " ".join(prompt.split())
    return (compact or "local fake video")[:36]


class FakeVideoService:
    """Video provider used only for explicit local development/test configuration."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def _ensure_default_fixture(self, *, prompt: str = "Fake Video") -> str:
        STATIC_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        if prompt and prompt.strip():
            filename = _video_slug(prompt)
        else:
            filename = DEFAULT_FAKE_VIDEO_FILENAME
        destination = STATIC_VIDEO_DIR / filename
        if destination.exists() and destination.stat().st_size > 0:
            return f"/static/videos/{filename}"

        digest = int(hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:8], 16)
        color = FAKE_VIDEO_COLORS[digest % len(FAKE_VIDEO_COLORS)]
        label = _prompt_label(prompt).replace("\\", "\\\\").replace(":", "\\:")
        shot_no = digest % 97 + 1

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=960x540:d=2.0",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf",
            (
                "drawtext=text='Fake Video':fontcolor=white:fontsize=58:"
                "x=(w-text_w)/2:y=150,"
                f"drawtext=text='#{shot_no:02d} local placeholder':fontcolor=0xfbbf24:fontsize=34:"
                "x=(w-text_w)/2:y=230,"
                f"drawtext=text='{label}':fontcolor=white@0.82:fontsize=24:"
                "x=(w-text_w)/2:y=315,"
                "drawtext=text='no external API call':fontcolor=white@0.62:fontsize=22:"
                "x=(w-text_w)/2:y=370"
            ),
            "-shortest",
            "-c:v",
            "libx264",
            "-t",
            "2.0",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(destination),
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode != 0:
                raise RuntimeError(stderr.decode(errors="ignore")[:500])
        except FileNotFoundError as exc:
            raise RuntimeError("Fake video provider needs ffmpeg to create the default fixture") from exc

        return f"/static/videos/{filename}"

    async def generate_url(
        self,
        *,
        prompt: str,
        image_bytes: bytes | None = None,
        image_url: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Return configured fixture URL, local fixture path, or generated default MP4."""
        fixture_url = (self.settings.fake_video_fixture_url or "").strip()
        if fixture_url:
            logger.info("Fake video provider returning fixture URL: %s", fixture_url)
            return fixture_url

        fixture_path = (self.settings.fake_video_fixture_path or "").strip()
        if fixture_path:
            source = Path(fixture_path).expanduser().resolve()
            if not source.is_file():
                raise RuntimeError(f"Fake video fixture file not found: {source}")

            STATIC_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
            suffix = source.suffix or ".mp4"
            filename = f"fake_clip_{uuid.uuid4().hex[:8]}{suffix}"
            destination = STATIC_VIDEO_DIR / filename
            shutil.copyfile(source, destination)
            logger.info("Fake video provider copied fixture to %s", destination)
            return f"/static/videos/{filename}"

        return await self._ensure_default_fixture(prompt=prompt)

    async def merge_urls(self, video_urls: list[str]) -> str:
        """Return a local fake merged video without remote downloads when possible."""
        if not video_urls:
            raise RuntimeError("No video URLs provided for merging")

        fixture_url = (self.settings.fake_video_fixture_url or "").strip()
        if fixture_url:
            return fixture_url

        fixture_path = (self.settings.fake_video_fixture_path or "").strip()
        if fixture_path:
            return await self.generate_url(prompt="fake merged video")

        local_paths = [get_local_path(url) for url in video_urls]
        if all(path is not None and path.is_file() for path in local_paths):
            merger = get_video_merger_service()
            return await merger.merge_videos(video_urls, output_filename=f"fake_merged_{uuid.uuid4().hex[:8]}")

        # Last-resort behavior for explicit remote fixtures: reuse real merger.
        merger = get_video_merger_service()
        return await merger.merge_videos(video_urls)

    @staticmethod
    def is_local_static_url(url: str) -> bool:
        """Return whether URL points to a backend static file."""
        return get_local_path(url) is not None
