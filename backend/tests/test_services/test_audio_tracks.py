"""测试 AudioService.generate_track / generate_tracks 音频轨道生成

Mock edge_tts.Communicate 避免真实 TTS 调用，仅验证参数路由和部分失败容错。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.audio_service import AudioService


# ── Helper: mock edge_tts.Communicate ─────────────────────────────

def _mock_communicate(mock_comm_class):
    mock_instance = AsyncMock()
    mock_instance.save = AsyncMock()
    mock_comm_class.return_value = mock_instance
    return mock_instance


# ── Tests: generate_track ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_track_dialogue(test_settings):
    """Dialogue track generates successfully via Edge TTS."""
    service = AudioService(test_settings)

    with patch("edge_tts.Communicate") as mock_comm_class:
        _mock_communicate(mock_comm_class)

        result = await service.generate_track("dialogue", "你好世界")

    assert result is not None
    assert result.startswith("/static/audio/")
    mock_comm_class.assert_called_once()
    call_kwargs = mock_comm_class.call_args.kwargs
    assert call_kwargs["rate"] == "+0%"
    assert call_kwargs["pitch"] == "+0Hz"


@pytest.mark.asyncio
async def test_generate_track_narrator(test_settings):
    """Narrator track generates successfully via Edge TTS."""
    service = AudioService(test_settings)

    with patch("edge_tts.Communicate") as mock_comm_class:
        _mock_communicate(mock_comm_class)

        result = await service.generate_track("narrator", "夜幕降临，城市灯火渐亮")

    assert result is not None
    assert result.startswith("/static/audio/")
    mock_comm_class.assert_called_once()


@pytest.mark.asyncio
async def test_generate_track_sfx(test_settings):
    """SFX track generates successfully via Edge TTS."""
    service = AudioService(test_settings)

    with patch("edge_tts.Communicate") as mock_comm_class:
        _mock_communicate(mock_comm_class)

        result = await service.generate_track("sfx", "砰！")

    assert result is not None
    assert result.startswith("/static/audio/")
    mock_comm_class.assert_called_once()


@pytest.mark.asyncio
async def test_generate_track_empty_text(test_settings):
    """Empty or whitespace-only text returns None without calling TTS."""
    service = AudioService(test_settings)

    with patch("edge_tts.Communicate") as mock_comm_class:
        assert await service.generate_track("dialogue", "") is None
        assert await service.generate_track("dialogue", "   ") is None
        assert await service.generate_track("narrator", "\n\t  ") is None

    mock_comm_class.assert_not_called()


@pytest.mark.asyncio
async def test_generate_track_invalid_type(test_settings):
    """Invalid track_type returns None with a warning."""
    service = AudioService(test_settings)

    with patch("edge_tts.Communicate") as mock_comm_class:
        result = await service.generate_track("music", "test text")

    assert result is None
    mock_comm_class.assert_not_called()


@pytest.mark.asyncio
async def test_generate_track_speed_mapping(test_settings):
    """voice_profile speed/pitch maps correctly to Edge TTS rate/pitch format."""
    service = AudioService(test_settings)

    with patch("edge_tts.Communicate") as mock_comm_class:
        _mock_communicate(mock_comm_class)

        await service.generate_track(
            "dialogue", "你好", voice_profile={"speed": 1.5, "pitch": 2},
        )
        mock_comm_class.assert_called_with(
            "你好", "zh-CN-XiaoxiaoNeural", rate="+50%", pitch="+2Hz",
        )

        await service.generate_track(
            "dialogue", "你好", voice_profile={"speed": 0.8},
        )
        mock_comm_class.assert_called_with(
            "你好", "zh-CN-XiaoxiaoNeural", rate="-20%", pitch="+0Hz",
        )

        await service.generate_track(
            "dialogue", "你好", voice_profile={"speed": 1.0},
        )
        mock_comm_class.assert_called_with(
            "你好", "zh-CN-XiaoxiaoNeural", rate="+0%", pitch="+0Hz",
        )

        await service.generate_track(
            "dialogue", "你好", voice_profile={"pitch": 0},
        )
        mock_comm_class.assert_called_with(
            "你好", "zh-CN-XiaoxiaoNeural", rate="+0%", pitch="+0Hz",
        )

        await service.generate_track("dialogue", "你好")
        mock_comm_class.assert_called_with(
            "你好", "zh-CN-XiaoxiaoNeural", rate="+0%", pitch="+0Hz",
        )


@pytest.mark.asyncio
async def test_generate_track_custom_voice(test_settings):
    """Explicit voice parameter overrides tts_default_voice."""
    service = AudioService(test_settings)

    with patch("edge_tts.Communicate") as mock_comm_class:
        _mock_communicate(mock_comm_class)

        await service.generate_track(
            "dialogue", "你好", voice="zh-CN-YunxiNeural",
        )
        mock_comm_class.assert_called_with(
            "你好", "zh-CN-YunxiNeural", rate="+0%", pitch="+0Hz",
        )


# ── Tests: generate_tracks ────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_tracks_partial_failure(test_settings):
    """One track fails (sfx), others succeed — partial failure tolerance."""
    service = AudioService(test_settings)

    shot = MagicMock()
    shot.dialogue = "你好"
    shot.action = "他走向门口"
    shot.sfx = "脚步声"
    shot.character_ids = [1]
    shot.order = 1

    character = MagicMock()
    character.id = 1
    character.name = "Test"
    character.description = "A test character"
    character.voice_profile = None

    original = service.generate_track

    async def _fake_generate_track(track_type, text, voice_profile=None, voice=None):
        if track_type == "sfx":
            raise RuntimeError("Simulated SFX failure")
        return f"/static/audio/test_{track_type}.mp3"

    try:
        service.generate_track = _fake_generate_track
        result = await service.generate_tracks(shot, characters=[character])
    finally:
        service.generate_track = original

    assert set(result.keys()) == {"dialogue", "narrator", "sfx"}
    assert result["dialogue"] == "/static/audio/test_dialogue.mp3"
    assert result["narrator"] == "/static/audio/test_narrator.mp3"
    assert result["sfx"] is None


@pytest.mark.asyncio
async def test_generate_tracks_empty_shot(test_settings):
    """Shot with no dialogue/action/sfx — all tracks are None."""
    service = AudioService(test_settings)

    shot = MagicMock()
    shot.dialogue = None
    shot.action = None
    shot.sfx = None
    shot.character_ids = []
    shot.order = 1

    original = service.generate_track

    call_count = 0

    async def _counting_generate_track(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return "/static/audio/test.mp3"

    try:
        service.generate_track = _counting_generate_track
        result = await service.generate_tracks(shot, characters=[])
    finally:
        service.generate_track = original

    assert result == {"dialogue": None, "narrator": None, "sfx": None}
    assert call_count == 0


@pytest.mark.asyncio
async def test_generate_tracks_dialogue_only(test_settings):
    """Shot with only dialogue — only dialogue track populated."""
    service = AudioService(test_settings)

    shot = MagicMock()
    shot.dialogue = "你好"
    shot.action = None
    shot.sfx = None
    shot.character_ids = [1]
    shot.order = 1

    character = MagicMock()
    character.id = 1
    character.name = "Test"
    character.description = "A test character"
    character.voice_profile = None

    original = service.generate_track

    async def _fake_generate_track_2(track_type, text, voice_profile=None, voice=None):
        return f"/static/audio/test_{track_type}.mp3"

    try:
        service.generate_track = _fake_generate_track_2
        result = await service.generate_tracks(shot, characters=[character])
    finally:
        service.generate_track = original

    assert result["dialogue"] == "/static/audio/test_dialogue.mp3"
    assert result["narrator"] is None
    assert result["sfx"] is None
