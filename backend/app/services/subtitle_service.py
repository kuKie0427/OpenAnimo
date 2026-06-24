"""字幕服务 — SRT 字幕生成与 FFmpeg 硬字幕烧录

提供两个核心函数：
- build_srt: 从 Shot 对象列表生成 SRT 格式字幕文本
- burn_subtitles_into_video: 用 FFmpeg 将 SRT 字幕烧录到视频中（硬字幕）
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.project import Shot

logger = logging.getLogger(__name__)


def _format_timestamp(seconds: float) -> str:
    """将秒数格式化为 SRT 时间戳（HH:MM:SS,mmm）

    >>> _format_timestamp(0.0)
    '00:00:00,000'
    >>> _format_timestamp(3.5)
    '00:00:03,500'
    >>> _format_timestamp(3661.5)
    '01:01:01,500'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_srt(shots: list[Shot], *, include_unapproved: bool = False) -> str:
    """从 Shot 列表生成 SRT 格式字幕

    按 shot.order 排序，根据 shot.duration 累加时间轴。
    include_unapproved=False 时使用 shot.approved_dialogue，
    include_unapproved=True 时使用 shot.dialogue（原始对话）。

    无对话或对话为空的镜头会被跳过，且不推进时间轴。

    Args:
        shots: Shot 对象列表（SQLModel ORM 对象）
        include_unapproved: 是否使用未审批的原始对话文本

    Returns:
        SRT 格式字幕字符串（UTF-8，CRLF 换行）
    """
    sorted_shots = sorted(shots, key=lambda s: s.order)

    entries: list[str] = []
    current_time = 0.0
    entry_index = 1

    for shot in sorted_shots:
        dialogue = shot.dialogue if include_unapproved else shot.approved_dialogue
        if not dialogue:
            # 无对话镜头：跳过，不创建字幕条目，不推进时间轴
            continue

        duration = shot.duration if shot.duration is not None else 5.0

        start_ts = _format_timestamp(current_time)
        end_ts = _format_timestamp(current_time + duration)

        entries.append(
            f"{entry_index}\r\n"
            f"{start_ts} --> {end_ts}\r\n"
            f"{dialogue}"
        )
        current_time += duration
        entry_index += 1

    if not entries:
        return ""

    return "\r\n\r\n".join(entries) + "\r\n"


async def burn_subtitles_into_video(
    video_path: str,
    srt_path: str,
    output_path: str,
    *,
    font_path: str | None = None,
) -> str:
    """用 FFmpeg 将 SRT 字幕硬烧录到视频中

    使用 FFmpeg 的 subtitles 滤镜将 SRT 字幕嵌入视频画面。
    音频流直接复制（-c:a copy），不重新编码。

    字体选择优先级：
    1. 显式传入 font_path 参数
    2. 调用 get_pillow_font_path() 自动检测系统中文字体
    3. 降级为 Arial（通过 logger.warning 记录）

    Args:
        video_path: 输入视频文件路径
        srt_path: SRT 字幕文件路径
        output_path: 输出视频文件路径
        font_path: 字体文件路径，为 None 时自动检测

    Returns:
        output_path（成功时）

    Raises:
        RuntimeError: FFmpeg 执行失败时
    """
    # --- 字体解析 ---
    resolved_font_path = font_path
    if resolved_font_path is None:
        from app.services.font_utils import get_pillow_font_path

        resolved_font_path = get_pillow_font_path()

    if resolved_font_path:
        font_dir = str(Path(resolved_font_path).parent)
        font_name = Path(resolved_font_path).stem
        vf_filter = (
            f"subtitles={srt_path}:fontsdir='{font_dir}':"
            f"force_style='FontName={font_name},FontSize=24,"
            f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2'"
        )
    else:
        logger.warning(
            "No Chinese font found for subtitle burn-in, falling back to Arial. "
            "Chinese characters may not render correctly."
        )
        vf_filter = (
            f"subtitles={srt_path}:"
            f"force_style='FontName=Arial,FontSize=24,"
            f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2'"
        )

    # --- FFmpeg 执行 ---
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vf",
        vf_filter,
        "-c:a",
        "copy",
        output_path,
    ]

    logger.info("Running ffmpeg subtitle burn-in: %s", " ".join(cmd))

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg subtitle burn-in failed: {stderr.decode()}")

    logger.info("Subtitles burned successfully: %s", output_path)
    return output_path
