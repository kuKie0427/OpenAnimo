"""Test AudioService.mix_tracks() and AudioService.export_tracks_zip()

Mock FFmpeg subprocess — do NOT use real FFmpeg.
"""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.audio_service import AudioService


# ── Tests: mix_tracks ──────────────────────────────────────────────


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
@patch("app.services.file_cleaner.get_local_path")
async def test_mix_tracks_all_4_inputs(
    mock_get_local_path, mock_subprocess_exec, test_settings,
):
    """All 4 audio tracks provided — builds full FFmpeg amix filter graph."""
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.__fspath__.return_value = "/tmp/fake/test.mp4"
    mock_get_local_path.return_value = mock_path

    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"", b"")
    mock_subprocess_exec.return_value = mock_process

    service = AudioService(test_settings)
    result = await service.mix_tracks(
        video_path="/static/videos/test.mp4",
        dialogue_path="/static/audio/dialogue.mp3",
        narrator_path="/static/audio/narrator.mp3",
        sfx_path="/static/audio/sfx.mp3",
        bgm_path="/static/bgm/ambient.mp3",
    )

    assert result.startswith("/static/videos/")
    mock_subprocess_exec.assert_called_once()

    cmd_str = " ".join(
        str(a) for a in mock_subprocess_exec.call_args.args if isinstance(a, str)
    )
    assert "amix" in cmd_str
    assert "afade" in cmd_str
    assert "volume" in cmd_str
    # video (stream 0) + 4 tracks = 5 amix inputs
    assert "amix=inputs=5" in cmd_str


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
@patch("app.services.file_cleaner.get_local_path")
async def test_mix_tracks_partial_inputs(
    mock_get_local_path, mock_subprocess_exec, test_settings,
):
    """Only dialogue + bgm; narrator/sfx as None — amix with 3 inputs."""
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.__fspath__.return_value = "/tmp/fake/test.mp4"
    mock_get_local_path.return_value = mock_path

    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"", b"")
    mock_subprocess_exec.return_value = mock_process

    service = AudioService(test_settings)
    result = await service.mix_tracks(
        video_path="/static/videos/test.mp4",
        dialogue_path="/static/audio/dialogue.mp3",
        narrator_path=None,
        sfx_path=None,
        bgm_path="/static/bgm/ambient.mp3",
    )

    assert result.startswith("/static/videos/")
    cmd_str = " ".join(
        str(a) for a in mock_subprocess_exec.call_args.args if isinstance(a, str)
    )
    assert "amix=inputs=3" in cmd_str


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
@patch("app.services.file_cleaner.get_local_path")
async def test_mix_tracks_no_inputs(
    mock_get_local_path, mock_subprocess_exec, test_settings,
):
    """All tracks None — returns original video_path without calling FFmpeg."""
    service = AudioService(test_settings)
    result = await service.mix_tracks(
        video_path="/static/videos/test.mp4",
        dialogue_path=None,
        narrator_path=None,
        sfx_path=None,
        bgm_path=None,
    )

    assert result == "/static/videos/test.mp4"
    mock_subprocess_exec.assert_not_called()
    mock_get_local_path.assert_not_called()


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
@patch("app.services.file_cleaner.get_local_path")
async def test_mix_tracks_missing_file(
    mock_get_local_path, mock_subprocess_exec, test_settings,
):
    """SFX file doesn't exist — skipped gracefully, remaining tracks used."""

    def _resolve(url: str):
        path = MagicMock(spec=Path)
        path.__fspath__.return_value = "/tmp/fake/%s" % url.rsplit("/", 1)[-1]
        if "sfx" in url:
            path.exists.return_value = False
        else:
            path.exists.return_value = True
        return path

    mock_get_local_path.side_effect = _resolve

    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"", b"")
    mock_subprocess_exec.return_value = mock_process

    service = AudioService(test_settings)
    result = await service.mix_tracks(
        video_path="/static/videos/test.mp4",
        dialogue_path="/static/audio/dialogue.mp3",
        narrator_path="/static/audio/narrator.mp3",
        sfx_path="/static/audio/sfx.mp3",
        bgm_path="/static/bgm/ambient.mp3",
    )

    assert result.startswith("/static/videos/")
    cmd_str = " ".join(
        str(a) for a in mock_subprocess_exec.call_args.args if isinstance(a, str)
    )
    assert "amix=inputs=4" in cmd_str


# ── Tests: export_tracks_zip ───────────────────────────────────────

_EXPORT_ZIP_NAME_42_1 = "tracks_42_1.zip"


def _export_zip_path() -> Path:
    """Returns the absolute path where export_tracks_zip writes the zip."""
    import app.services.audio_service as _mod
    return Path(_mod.__file__).parent.parent / "static" / "exports" / _EXPORT_ZIP_NAME_42_1


def _verify_and_cleanup_zip(zip_path: Path, *, expected_tracks: list[str], expected_count: int):
    """Verify zip contents match expectations, then remove it."""
    assert zip_path.exists(), f"Expected zip at {zip_path}"
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert "metadata.json" in names
        for track_name in expected_tracks:
            assert track_name in names, f"Missing {track_name} in {names}"

        metadata = json.loads(zf.read("metadata.json"))
        assert metadata["project_id"] == 42
        assert metadata["run_id"] == 1
        assert len(metadata["tracks"]) == expected_count
    zip_path.unlink()


@pytest.mark.asyncio
async def test_export_tracks_zip(test_settings):
    """3 valid tracks → zip created with metadata.json and all track files."""
    service = AudioService(test_settings)

    with tempfile.TemporaryDirectory() as tmpdir:
        track_dir = Path(tmpdir) / "audio"
        track_dir.mkdir()
        (track_dir / "dialogue.mp3").write_text("fake dialogue data")
        (track_dir / "narrator.mp3").write_text("fake narrator data")
        (track_dir / "sfx.mp3").write_text("fake sfx data")

        with patch("app.services.file_cleaner.get_local_path") as mock_glp:

            def _resolve(url):
                if "dialogue" in url:
                    return track_dir / "dialogue.mp3"
                if "narrator" in url:
                    return track_dir / "narrator.mp3"
                if "sfx" in url:
                    return track_dir / "sfx.mp3"
                return None

            mock_glp.side_effect = _resolve

            result = await service.export_tracks_zip(
                {
                    "dialogue": "/static/audio/dialogue.mp3",
                    "narrator": "/static/audio/narrator.mp3",
                    "sfx": "/static/audio/sfx.mp3",
                },
                project_id=42,
                run_id=1,
            )

            assert result is not None
            assert result == f"/static/exports/{_EXPORT_ZIP_NAME_42_1}"

        _verify_and_cleanup_zip(
            _export_zip_path(),
            expected_tracks=["dialogue.mp3", "narrator.mp3", "sfx.mp3"],
            expected_count=3,
        )


@pytest.mark.asyncio
async def test_export_tracks_zip_partial(test_settings):
    """Narrator track is None — zip contains only dialogue and sfx."""
    service = AudioService(test_settings)

    with tempfile.TemporaryDirectory() as tmpdir:
        track_dir = Path(tmpdir) / "audio"
        track_dir.mkdir()
        (track_dir / "dialogue.mp3").write_text("fake dialogue data")
        (track_dir / "sfx.mp3").write_text("fake sfx data")

        with patch("app.services.file_cleaner.get_local_path") as mock_glp:

            def _resolve(url):
                if "dialogue" in url:
                    return track_dir / "dialogue.mp3"
                if "sfx" in url:
                    return track_dir / "sfx.mp3"
                return None

            mock_glp.side_effect = _resolve

            result = await service.export_tracks_zip(
                {
                    "dialogue": "/static/audio/dialogue.mp3",
                    "narrator": None,
                    "sfx": "/static/audio/sfx.mp3",
                },
                project_id=42,
                run_id=1,
            )

            assert result is not None
            assert result == f"/static/exports/{_EXPORT_ZIP_NAME_42_1}"

        _verify_and_cleanup_zip(
            _export_zip_path(),
            expected_tracks=["dialogue.mp3", "sfx.mp3"],
            expected_count=2,
        )


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
@patch("app.services.file_cleaner.get_local_path")
async def test_mix_tracks_custom_volumes(
    mock_get_local_path, mock_subprocess_exec, test_settings,
):
    """Custom volumes override settings defaults."""
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.__fspath__.return_value = "/tmp/fake/test.mp4"
    mock_get_local_path.return_value = mock_path

    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"", b"")
    mock_subprocess_exec.return_value = mock_process

    service = AudioService(test_settings)
    custom_volumes = {"dialogue": 0.8, "narrator": 0.6, "sfx": 0.5, "bgm": 0.1}
    result = await service.mix_tracks(
        video_path="/static/videos/test.mp4",
        dialogue_path="/static/audio/dialogue.mp3",
        bgm_path="/static/bgm/ambient.mp3",
        volumes=custom_volumes,
    )

    assert result.startswith("/static/videos/")
    cmd_str = " ".join(
        str(a) for a in mock_subprocess_exec.call_args.args if isinstance(a, str)
    )
    # Custom volumes should appear in the filter
    assert "volume=0.8" in cmd_str   # dialogue
    assert "volume=0.1" in cmd_str   # bgm
