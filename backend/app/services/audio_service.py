"""TTS + BGM 音频服务

使用 Edge TTS（免费）生成角色语音，内置 BGM 匹配场景情绪，
FFmpeg 混流将音频叠加到视频中。

容错设计：
- Edge TTS 不可用时跳过 TTS
- BGM 文件缺失时跳过 BGM
- FFmpeg 失败时保留原视频
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings
from app.models.project import Character, Shot
from app.services.tts_voices import get_voice_for_character

logger = logging.getLogger(__name__)

# 输出目录
AUDIO_OUTPUT_DIR = Path(__file__).parent.parent / "static" / "audio"
BGM_BASE_DIR = Path(__file__).parent.parent  # bgm_directory 相对于此

# BGM 情绪关键词映射
_BGM_KEYWORD_MAP: dict[str, list[str]] = {
    "suspense": ["紧张", "危险", "黑暗", "恐惧", "悬疑", "神秘", "阴影", "暗夜", "陷阱"],
    "warm": ["温暖", "阳光", "微笑", "治愈", "温馨", "春天", "花", "晨曦"],
    "action": ["战斗", "激烈", "热血", "冲突", "追逐", "爆发", "冲锋", "对决"],
    "sad": ["悲伤", "哭泣", "离别", "失落", "雨", "黄昏", "孤独", "消逝"],
    "happy": ["欢乐", "庆祝", "胜利", "欢笑", "舞会", "节日", "聚会"],
}

# 默认 BGM
_DEFAULT_BGM = "ambient"

# BGM 文件名列表（与目录中的文件一一对应）
_BGM_FILES = ["suspense.mp3", "warm.mp3", "action.mp3", "sad.mp3", "happy.mp3", "ambient.mp3"]


def _ensure_output_dir() -> None:
    """确保音频输出目录存在"""
    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_bgm_dir(settings: Settings) -> Path:
    """确保 BGM 目录存在并生成占位文件（如果需要）

    如果 BGM 目录下没有实际音频文件，使用 FFmpeg 生成静音占位文件。
    用户可自行替换为真实 BGM 文件。

    Args:
        settings: 应用配置

    Returns:
        BGM 目录路径
    """
    bgm_dir = BGM_BASE_DIR / settings.bgm_directory
    bgm_dir.mkdir(parents=True, exist_ok=True)

    for filename in _BGM_FILES:
        filepath = bgm_dir / filename
        if not filepath.exists() or filepath.stat().st_size < 100:
            # 生成 15 秒静音占位 MP3
            # 用户可自行替换为真实 BGM 文件
            _generate_silence_placeholder(filepath, duration=15)

    return bgm_dir


def _generate_silence_placeholder(dest: Path, duration: int = 15) -> None:
    """使用 FFmpeg 生成静音占位文件

    Args:
        dest: 目标文件路径
        duration: 时长（秒）
    """
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            str(dest),
        ]
        subprocess.run(cmd, capture_output=True, timeout=30, check=True)
        logger.info("Generated silence placeholder BGM: %s", dest)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        logger.warning("Failed to generate silence placeholder for %s (FFmpeg unavailable?)", dest)


class AudioService:
    """TTS + BGM 音频服务"""

    def __init__(self, settings: Settings):
        self.settings = settings
        _ensure_output_dir()
        self._bgm_dir: Path | None = None

    def _get_bgm_dir(self) -> Path:
        """获取 BGM 目录（延迟初始化）"""
        if self._bgm_dir is None:
            self._bgm_dir = _ensure_bgm_dir(self.settings)
        return self._bgm_dir

    async def generate_tts(
        self,
        text: str,
        voice: str = "zh-CN-XiaoxiaoNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> str | None:
        """用 Edge TTS 生成语音，返回音频文件 URL

        Args:
            text: 要合成的文本
            voice: Edge TTS 语音名称
            rate: 语速调整（如 "+10%" 或 "-5%"）
            pitch: 音调调整（如 "+2Hz" 或 "-3Hz"）

        Returns:
            音频文件 URL（如 /static/audio/tts_xxx.mp3），失败返回 None
        """
        if not text or not text.strip():
            return None

        try:
            import edge_tts
        except ImportError:
            logger.warning("edge-tts not installed, skipping TTS generation")
            return None

        filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
        output_path = AUDIO_OUTPUT_DIR / filename

        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(str(output_path))
            logger.info("TTS generated: %s (voice=%s, text=%s...)", output_path, voice, text[:30])
            return f"/static/audio/{filename}"
        except Exception:  # noqa: BLE001
            # edge_tts may raise various OSError/httpx errors on network failure
            logger.warning("TTS generation failed (text=%s..., voice=%s)", text[:30], voice, exc_info=True)
            return None

    async def generate_character_tts(
        self,
        dialogue: str,
        character_name: str,
        characters: list[Character],
    ) -> str | None:
        """根据角色选择合适的 TTS 语音并生成

        Args:
            dialogue: 对白文本
            character_name: 角色名称
            characters: 项目角色列表

        Returns:
            TTS 音频 URL，失败返回 None
        """
        if not dialogue or not dialogue.strip():
            return None

        if not self.settings.tts_enabled:
            return None

        # 查找匹配的角色
        voice = self.settings.tts_default_voice
        for char in characters:
            if char.name == character_name:
                voice = get_voice_for_character(char)
                break

        return await self.generate_tts(dialogue, voice=voice)

    async def generate_track(
        self,
        track_type: str,
        text: str,
        voice_profile: dict | None = None,
        voice: str | None = None,
    ) -> str | None:
        """Generate a single audio track of the specified type.

        Maps voice_profile to Edge TTS parameters (rate/pitch) and delegates
        to generate_tts for the actual synthesis.

        Args:
            track_type: One of "dialogue", "narrator", "sfx"
            text: Text to synthesize
            voice_profile: Optional voice profile dict with speed/pitch keys
            voice: Edge TTS voice name (falls back to tts_default_voice)

        Returns:
            Audio file URL, or None on failure
        """
        allowed_types = {"dialogue", "narrator", "sfx"}
        if track_type not in allowed_types:
            logger.warning(
                "Invalid track_type: %s (allowed: %s)", track_type, allowed_types,
            )
            return None

        if not self.settings.tts_enabled:
            return None

        if not text or not text.strip():
            return None

        # Map voice_profile to Edge TTS parameters
        if voice_profile is not None:
            speed = voice_profile.get("speed", 1.0)
            rate = f"{round((speed - 1.0) * 100):+d}%"
            pitch_val = voice_profile.get("pitch", 0)
            pitch = f"{pitch_val:+d}Hz"
        else:
            rate = "+0%"
            pitch = "+0Hz"

        # Fallback voice
        actual_voice = voice or self.settings.tts_default_voice

        logger.info(
            "Generating %s track: text=%s..., voice=%s, rate=%s, pitch=%s",
            track_type, text[:30], actual_voice, rate, pitch,
        )

        result = await self.generate_tts(
            text, voice=actual_voice, rate=rate, pitch=pitch,
        )
        if result is None:
            logger.warning(
                "Failed to generate %s track: text=%s..., voice=%s",
                track_type, text[:30], actual_voice,
            )
        return result

    async def generate_tracks(
        self,
        shot: Shot,
        characters: list[Character],
    ) -> dict[str, str | None]:
        """Generate all audio tracks for a shot: dialogue, narrator, and SFX.

        Each track is generated independently with partial failure tolerance.

        Args:
            shot: Shot object with dialogue, action, sfx, character_ids fields
            characters: List of Character objects for voice matching

        Returns:
            Dict with keys "dialogue", "narrator", "sfx" mapping to audio URLs or None
        """
        results: dict[str, str | None] = {"dialogue": None, "narrator": None, "sfx": None}
        default_voice = self.settings.tts_default_voice

        # --- Dialogue track ---
        if shot.dialogue and shot.dialogue.strip():
            char = next(
                (c for c in characters if c.id in (shot.character_ids or [])), None,
            )
            char_profile = char.voice_profile if char else None
            char_voice = get_voice_for_character(char) if char else default_voice
            try:
                results["dialogue"] = await self.generate_track(
                    "dialogue", shot.dialogue,
                    voice_profile=char_profile, voice=char_voice,
                )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Failed to generate dialogue track for shot (order=%s)",
                    shot.order, exc_info=True,
                )
        logger.info("Dialogue track result: %s", results["dialogue"])

        # --- Narrator track ---
        if shot.action and shot.action.strip():
            try:
                results["narrator"] = await self.generate_track(
                    "narrator", shot.action,
                    voice_profile=None, voice=default_voice,
                )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Failed to generate narrator track for shot (order=%s)",
                    shot.order, exc_info=True,
                )
        logger.info("Narrator track result: %s", results["narrator"])

        # --- SFX track ---
        if shot.sfx and shot.sfx.strip():
            try:
                results["sfx"] = await self.generate_track(
                    "sfx", shot.sfx,
                    voice_profile=None, voice=default_voice,
                )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Failed to generate sfx track for shot (order=%s)",
                    shot.order, exc_info=True,
                )
        logger.info("SFX track result: %s", results["sfx"])

        return results

    def match_bgm(
        self,
        scene: str | None = None,
        expression: str | None = None,
        genre: str | None = None,
    ) -> str | None:
        """根据场景描述和表情匹配 BGM

        通过关键词匹配确定情绪类型，返回对应 BGM 文件路径。
        如果 BGM 未启用或无匹配文件，返回 None。

        Args:
            scene: 场景描述
            expression: 表情/情绪描述
            genre: 题材类型

        Returns:
            BGM 文件路径，无匹配返回 None
        """
        if not self.settings.bgm_enabled:
            return None

        # 合并所有可能包含情绪关键词的文本
        combined = " ".join(filter(None, [scene or "", expression or "", genre or ""]))

        # 关键词匹配
        for bgm_type, keywords in _BGM_KEYWORD_MAP.items():
            for kw in keywords:
                if kw in combined:
                    return self._resolve_bgm_path(bgm_type)

        # 默认 ambient
        return self._resolve_bgm_path(_DEFAULT_BGM)

    def _resolve_bgm_path(self, bgm_type: str) -> str | None:
        """解析 BGM 文件路径

        Args:
            bgm_type: BGM 类型名称

        Returns:
            BGM 文件 URL（如 /static/bgm/suspense.mp3），文件不存在返回 None
        """
        bgm_dir = self._get_bgm_dir()
        filepath = bgm_dir / f"{bgm_type}.mp3"
        if filepath.exists() and filepath.stat().st_size > 100:
            # 直接拼接为 /static/bgm/xxx.mp3 URL
            return f"/static/bgm/{bgm_type}.mp3"
        return None

    async def mix_audio_into_video(
        self,
        video_path: str,
        tts_path: str | None = None,
        bgm_path: str | None = None,
        bgm_volume: float | None = None,
        tts_volume: float | None = None,
    ) -> str:
        """用 FFmpeg 将 TTS 和 BGM 混入视频

        逻辑：
        1. 如果有 TTS，将 TTS 叠加到视频音轨
        2. 如果有 BGM，将 BGM 作为背景音混入（降低音量）
        3. 保留视频原始音频（如果有）
        4. FFmpeg 失败时返回原视频路径

        Args:
            video_path: 视频文件路径（/static/videos/xxx.mp4 或本地路径）
            tts_path: TTS 音频文件路径（/static/audio/xxx.mp3）
            bgm_path: BGM 文件路径（/static/bgm/xxx.mp3）
            bgm_volume: BGM 音量覆盖（0-1），None 使用 settings
            tts_volume: TTS 音量覆盖（0-1），None 使用 settings

        Returns:
            新视频文件路径（/static/videos/xxx.mp4），失败返回原 video_path
        """
        if not tts_path and not bgm_path:
            return video_path

        from app.services.file_cleaner import get_local_path

        # 解析本地文件路径
        video_local = get_local_path(video_path)
        if video_local is None:
            # 不是本地文件，无法混流
            logger.warning("Cannot mix audio: video is not a local file (%s)", video_path)
            return video_path

        # 构建输出文件
        output_filename = f"audio_{uuid.uuid4().hex[:8]}.mp4"
        output_path = AUDIO_OUTPUT_DIR.parent / "videos" / output_filename
        (AUDIO_OUTPUT_DIR.parent / "videos").mkdir(parents=True, exist_ok=True)

        # 解析音频本地路径
        tts_local = get_local_path(tts_path) if tts_path else None
        bgm_local = get_local_path(bgm_path) if bgm_path else None

        # 验证文件存在
        if tts_local and not tts_local.exists():
            logger.warning("TTS file not found: %s, skipping TTS", tts_local)
            tts_local = None
        if bgm_local and not bgm_local.exists():
            logger.warning("BGM file not found: %s, skipping BGM", bgm_local)
            bgm_local = None

        if not tts_local and not bgm_local:
            return video_path

        actual_bgm_vol = bgm_volume if bgm_volume is not None else self.settings.bgm_volume
        actual_tts_vol = tts_volume if tts_volume is not None else self.settings.tts_volume

        try:
            await self._ffmpeg_mix(
                video_local, tts_local, bgm_local,
                output_path, actual_tts_vol, actual_bgm_vol,
            )
            return f"/static/videos/{output_filename}"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            logger.warning("FFmpeg audio mixing failed, keeping original video", exc_info=True)
            return video_path

    async def _ffmpeg_mix(
        self,
        video_path: Path,
        tts_path: Path | None,
        bgm_path: Path | None,
        output_path: Path,
        tts_volume: float,
        bgm_volume: float,
    ) -> Path:
        """执行 FFmpeg 混流命令

        构建复杂的 FFmpeg filter_graph 将视频原始音频 + TTS + BGM 混合。

        Args:
            video_path: 视频文件本地路径
            tts_path: TTS 文件本地路径（可选）
            bgm_path: BGM 文件本地路径（可选）
            output_path: 输出文件本地路径
            tts_volume: TTS 音量
            bgm_volume: BGM 音量

        Returns:
            输出文件路径
        """
        # 构建 FFmpeg 输入和 filter
        inputs: list[str] = ["-i", str(video_path)]
        # 检测视频是否有音频轨
        # 我们使用 [0:a] 引用视频原始音频，如果不存在则用 anullsrc 填充

        audio_input_count = 1  # 下一个可用输入索引
        tts_idx = 0
        bgm_idx = 0

        if tts_path:
            inputs.extend(["-i", str(tts_path)])
            tts_idx = audio_input_count
            audio_input_count += 1

        if bgm_path:
            inputs.extend(["-i", str(bgm_path)])
            bgm_idx = audio_input_count
            audio_input_count += 1

        # 构建 filter graph
        # 1. 视频流直接复制
        # 2. 音频混合

        # 视频原始音频（如果存在），使用 amix 需要统一格式
        # 使用 pan=stereo|c0=c0|c1=c1 来确保单声道转立体声

        mix_inputs: list[str] = []

        # 视频原始音频
        mix_inputs.append("[0:a]aresample=44100,pan=stereo|c0=c0|c1=c1[vorig]")

        if tts_path:
            # TTS 音频：调整音量，截取到视频时长
            mix_inputs.append(
                f"[{tts_idx}:a]aresample=44100,pan=stereo|c0=c0|c1=c1,"
                f"volume={tts_volume},atrim=0:duration=9999[tts]"
            )

        if bgm_path:
            # BGM：循环播放 + 调整音量 + 截取到视频时长
            mix_inputs.append(
                f"[{bgm_idx}:a]aresample=44100,pan=stereo|c0=c0|c1=c1,"
                f"volume={bgm_volume},atrim=0:duration=9999[bgm]"
            )

        # amix 混合所有音频流
        n_inputs = len(mix_inputs)
        filter_chain = ";".join(mix_inputs)
        mix_labels = ["[vorig]"]
        if tts_path:
            mix_labels.append("[tts]")
        if bgm_path:
            mix_labels.append("[bgm]")

        filter_chain += f";{''.join(mix_labels)}amix=inputs={n_inputs}:duration=longest:dropout_transition=0[aout]"

        cmd = [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex", filter_chain,
            "-map", "0:v",       # 视频流
            "-map", "[aout]",    # 混合音频
            "-c:v", "copy",      # 视频流直接复制
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ]

        logger.info("Running FFmpeg audio mix: %s", " ".join(cmd[:10]))

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode(errors="replace")
            raise RuntimeError(f"FFmpeg audio mix failed: {error_msg[:500]}")

        logger.info("Audio mixed successfully: %s", output_path)
        return output_path

    async def mix_tracks(
        self,
        video_path: str,
        dialogue_path: str | None = None,
        narrator_path: str | None = None,
        sfx_path: str | None = None,
        bgm_path: str | None = None,
        volumes: dict[str, float] | None = None,
    ) -> str:
        """Mix multiple audio tracks into a video using FFmpeg amix filter.

        Supports up to 5 audio inputs: video original audio + 4 external tracks
        (dialogue, narrator, SFX, BGM) with per-track volume control and fade-in
        for speech tracks. Missing tracks are gracefully skipped.

        Args:
            video_path: Video file path (/static/videos/xxx.mp4 or local path)
            dialogue_path: Dialogue audio file path
            narrator_path: Narrator audio file path
            sfx_path: SFX audio file path
            bgm_path: BGM audio file path
            volumes: Per-track volume overrides (0-1). Missing keys use settings defaults.

        Returns:
            New video path (/static/videos/xxx.mp4), or original video_path on failure
        """
        from app.services.file_cleaner import get_local_path

        # 1. If no tracks provided, return immediately
        tracks: dict[str, str | None] = {
            "dialogue": dialogue_path,
            "narrator": narrator_path,
            "sfx": sfx_path,
            "bgm": bgm_path,
        }
        if not any(tracks.values()):
            return video_path

        # 2. Resolve video local path
        video_local = get_local_path(video_path)
        if video_local is None:
            logger.warning(
                "Cannot mix tracks: video is not a local file (%s)", video_path,
            )
            return video_path

        # 3. Resolve and verify track local paths; skip missing
        track_locals: dict[str, Path | None] = {}
        for name, path in tracks.items():
            if path:
                local = get_local_path(path)
                if local and local.exists():
                    track_locals[name] = local
                else:
                    logger.warning(
                        "%s track not found: %s, skipping", name, path,
                    )
                    track_locals[name] = None
            else:
                track_locals[name] = None

        if not any(track_locals.values()):
            return video_path

        # 4. Build output path
        output_filename = f"mix_{uuid.uuid4().hex[:8]}.mp4"
        output_path = AUDIO_OUTPUT_DIR.parent / "videos" / output_filename
        (AUDIO_OUTPUT_DIR.parent / "videos").mkdir(parents=True, exist_ok=True)

        # 5. Resolve volumes (use settings defaults for missing keys)
        default_volumes: dict[str, float] = {
            "dialogue": self.settings.tts_volume,
            "narrator": self.settings.tts_volume,
            "sfx": self.settings.tts_volume,
            "bgm": self.settings.bgm_volume,
        }
        vol: dict[str, float] = {
            k: (volumes or {}).get(k, default_volumes[k]) for k in default_volumes
        }

        # 6. Build FFmpeg inputs and filter graph
        track_order = ["dialogue", "narrator", "sfx", "bgm"]
        inputs: list[str] = ["-i", str(video_local)]

        idx = 1  # next input index (0 = video)
        track_indices: dict[str, int] = {}
        for name in track_order:
            if track_locals.get(name):
                inputs.extend(["-i", str(track_locals[name])])
                track_indices[name] = idx
                idx += 1

        filter_lines: list[str] = []
        mix_labels: list[str] = []

        # Video original audio
        filter_lines.append("[0:a]aresample=44100,pan=stereo|c0=c0|c1=c1[vorig]")
        mix_labels.append("[vorig]")

        fade_tracks = {"dialogue", "narrator"}

        for name in track_order:
            if name in track_indices:
                i = track_indices[name]
                chain = (
                    f"[{i}:a]aresample=44100,pan=stereo|c0=c0|c1=c1,"
                    f"volume={vol[name]}"
                )
                if name in fade_tracks:
                    # Fade-in only. Fade-out requires knowing track duration at
                    # filter-construction time (afade=t=out:st=END:d=0.3), but
                    # duration is determined by amix's duration=longest + -shortest
                    # and is not available until runtime. Fade-out can be added
                    # in a future pass by probing track duration with ffprobe first.
                    chain += ",afade=t=in:st=0:d=0.3"
                chain += f"[{name[:4]}]"
                filter_lines.append(chain)
                mix_labels.append(f"[{name[:4]}]")

        n_inputs = len(mix_labels)
        filter_lines.append(
            f"{''.join(mix_labels)}amix=inputs={n_inputs}:"
            f"duration=longest:dropout_transition=0[aout]"
        )
        filter_chain = ";".join(filter_lines)

        cmd = [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex", filter_chain,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ]

        logger.info(
            "Running FFmpeg multi-track mix (%d audio inputs)", n_inputs,
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode(errors="replace")
                logger.warning(
                    "FFmpeg multi-track mix failed (rc=%d): %s",
                    process.returncode, error_msg[:300],
                )
                return video_path

            logger.info("Multi-track mix successful: %s", output_path)
            return f"/static/videos/{output_filename}"
        except OSError:
            logger.warning(
                "FFmpeg multi-track mix failed, keeping original video",
                exc_info=True,
            )
            return video_path

    async def export_tracks_zip(
        self,
        tracks: dict[str, str | None],
        project_id: int,
        run_id: int | None = None,
    ) -> str | None:
        """Export individual audio tracks as a downloadable zip file with metadata.json.

        Collects non-None track URLs, reads their local file content, and packages
        them into a zip archive alongside a metadata.json manifest. Failed or missing
        tracks are skipped gracefully without blocking the export.

        Args:
            tracks: Dict mapping track types ("dialogue", "narrator", "sfx") to
                    audio URLs or None (e.g. from generate_tracks() output).
            project_id: Project ID used in filename and metadata.
            run_id: Optional run ID used in filename and metadata.

        Returns:
            Zip download URL (e.g. /static/exports/tracks_42_1.zip), or None if
            no valid tracks could be exported.
        """
        from app.services.file_cleaner import get_local_path

        valid_tracks = {k: v for k, v in tracks.items() if v is not None}
        if not valid_tracks:
            logger.debug("export_tracks_zip: no non-None tracks provided")
            return None

        track_files: dict[str, Path] = {}
        for name, url in valid_tracks.items():
            local_path = get_local_path(url)
            if local_path and local_path.exists():
                track_files[name] = local_path
            else:
                logger.warning(
                    "export_tracks_zip: %s track not found or file missing: %s",
                    name, url,
                )

        if not track_files:
            return None

        STATIC_DIR = Path(__file__).parent.parent / "static"
        exports_dir = STATIC_DIR / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

        if run_id is not None:
            zip_name = f"tracks_{project_id}_{run_id}.zip"
        else:
            zip_name = f"tracks_{project_id}.zip"
        zip_path = exports_dir / zip_name

        metadata_tracks: dict[str, dict[str, str | int]] = {}

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for name, file_path in track_files.items():
                    try:
                        file_data = file_path.read_bytes()
                        file_size = len(file_data)
                        archive_name = f"{name}{file_path.suffix}"
                        zf.writestr(archive_name, file_data)
                        metadata_tracks[name] = {
                            "filename": archive_name,
                            "size_bytes": file_size,
                        }
                        logger.info(
                            "export_tracks_zip: added %s (%d bytes)",
                            archive_name, file_size,
                        )
                    except OSError:
                        logger.warning(
                            "export_tracks_zip: failed to read %s, skipping",
                            file_path, exc_info=True,
                        )

                if not metadata_tracks:
                    zip_path.unlink(missing_ok=True)
                    return None

                metadata = {
                    "project_id": project_id,
                    "run_id": run_id,
                    "tracks": metadata_tracks,
                    "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                zf.writestr(
                    "metadata.json",
                    json.dumps(metadata, indent=2, ensure_ascii=False),
                )
                logger.info(
                    "export_tracks_zip: metadata.json written with %d tracks",
                    len(metadata_tracks),
                )

        except (OSError, zipfile.BadZipFile) as e:
            logger.warning("export_tracks_zip: failed to create zip: %s", e)
            zip_path.unlink(missing_ok=True)
            return None

        return f"/static/exports/{zip_name}"

    async def mix_bgm_into_video(
        self,
        video_path: str,
        bgm_path: str | None = None,
        bgm_volume: float | None = None,
    ) -> str:
        """仅将 BGM 混入最终合并视频

        与 mix_audio_into_video 类似，但专门用于最终视频的 BGM 叠加。

        Args:
            video_path: 最终视频路径
            bgm_path: BGM 文件路径
            bgm_volume: BGM 音量

        Returns:
            新视频路径，失败返回原路径
        """
        return await self.mix_audio_into_video(
            video_path,
            tts_path=None,
            bgm_path=bgm_path,
            bgm_volume=bgm_volume,
        )
