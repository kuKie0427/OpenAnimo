"""字体工具 — 中文字体查找与缓存

优先使用系统已安装的中文字体；
如果没有，自动下载 Google Noto Sans SC（免费开源）。
字体缓存到 static/fonts/ 目录。
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# 字体缓存目录
FONTS_DIR = Path(__file__).parent.parent / "static" / "fonts"

# 候选系统字体名称（按优先级排列）
_SYSTEM_FONT_CANDIDATES = [
    # Noto Sans CJK SC（TTC 格式）
    "NotoSansCJK-Regular.ttc",
    "NotoSansCJKsc-Regular.otf",
    # Noto Sans SC（独立 OTF/TTF）
    "NotoSansSC-Regular.otf",
    "NotoSansSC-Regular.ttf",
    # Source Han Sans SC
    "SourceHanSansSC-Regular.otf",
    # 文泉驿
    "wqy-microhei.ttc",
    "wqy-zenhei.ttc",
    # Windows 中文字体
    "msyh.ttc",       # 微软雅黑
    "simsun.ttc",     # 宋体
    "simhei.ttf",     # 黑体
]

# 缓存找到的字体路径
_cached_font_path: str | None = None


def _find_system_font() -> str | None:
    """尝试在系统中查找中文字体"""
    # 1. 用 fc-list 查找（Linux/Mac）
    try:
        result = subprocess.run(
            ["fc-list", ":lang=zh", "-f", "%{file}\\n"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line and os.path.isfile(line):
                    # 优先选择 Regular 字体
                    lower = line.lower()
                    if any(k in lower for k in ["regular", "-regular.", "medium"]):
                        return line
            # 如果没有 Regular，取第一个可用的
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line and os.path.isfile(line):
                    return line
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # 2. 在常见目录中查找
    search_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        "/System/Library/Fonts",
        "/Library/Fonts",
        os.path.expanduser("~/.fonts"),
        os.path.expanduser("~/.local/share/fonts"),
        # Windows
        "C:/Windows/Fonts",
    ]

    for search_dir in search_dirs:
        search_path = Path(search_dir)
        if not search_path.is_dir():
            continue
        for candidate in _SYSTEM_FONT_CANDIDATES:
            # 递归搜索
            for match in search_path.rglob(candidate):
                if match.is_file():
                    return str(match)

    return None


def _download_noto_sans_sc() -> str | None:
    """下载 Google Noto Sans SC 字体到缓存目录"""
    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    target_path = FONTS_DIR / "NotoSansSC-Regular.ttf"
    if target_path.exists():
        return str(target_path)

    # Google Fonts CDN 下载链接（免费开源）
    # Noto Sans SC 单独 TTF 文件（不是 TTC）
    # 使用 fonts.google.com CSS 解析得到的实际 URL
    download_urls = [
        "https://fonts.gstatic.com/s/notosanssc/v36/k3kCo84MPvpLmixcA63oeAL7Iqp5IZJF9bmaG9_EnYxNbPzS5HE.ttf",
    ]

    import httpx
    for url in download_urls:
        try:
            logger.info(f"Downloading Noto Sans SC from {url}...")
            client = httpx.Client(timeout=60.0, follow_redirects=True)
            res = client.get(url)
            res.raise_for_status()

            # 根据后缀保存
            suffix = url.rsplit('.', 1)[-1].lower()
            if suffix in ('otf', 'ttf'):
                target_path = FONTS_DIR / f"NotoSansSC-Regular.{suffix}"
            target_path.write_bytes(res.content)
            logger.info(f"Font downloaded to {target_path}")
            return str(target_path)
        except (httpx.HTTPError, OSError) as e:
            logger.warning(f"Failed to download font from {url}: {e}")
            continue

    logger.error("All font download sources failed")
    return None


def get_chinese_font_path() -> str:
    """获取中文字体路径

    优先级：
    1. 系统已安装的中文字体
    2. 缓存目录中已下载的字体
    3. 自动下载 Noto Sans SC
    4. 返回 reportlab 默认字体路径（降级）
    """
    global _cached_font_path

    if _cached_font_path is not None:
        return _cached_font_path

    # 1. 查找系统字体
    system_font = _find_system_font()
    if system_font:
        _cached_font_path = system_font
        logger.info(f"Using system font: {system_font}")
        return system_font

    # 2. 检查缓存目录
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    for candidate in _SYSTEM_FONT_CANDIDATES:
        cached = FONTS_DIR / candidate
        if cached.exists():
            _cached_font_path = str(cached)
            logger.info(f"Using cached font: {cached}")
            return str(cached)

    # 3. 自动下载
    downloaded = _download_noto_sans_sc()
    if downloaded:
        _cached_font_path = downloaded
        return downloaded

    # 4. 降级：返回空字符串，调用方应使用 reportlab 默认字体
    logger.warning(
        "No Chinese font found. Chinese characters may not render correctly. "
        "Please install Noto Sans CJK or Noto Sans SC manually."
    )
    return ""


def get_reportlab_font_name() -> str:
    """获取 reportlab 中可用的中文字体注册名称

    如果系统有 TTC 字体，使用 CID 字体名称；
    否则注册 TTF/OTF 字体并返回注册名称。
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont

    font_path = get_chinese_font_path()
    if not font_path:
        # 使用 reportlab 内置 CID 字体（支持中日韩）
        try:
            font_name = "STSong-Light"
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))
            return font_name
        except Exception:  # noqa: BLE001
            # reportlab CID font registration may fail for various system-level reasons
            return "Helvetica"

    lower_path = font_path.lower()

    # TTC 文件需要指定 subfontIndex
    if lower_path.endswith(".ttc"):
        try:
            font_name = "NotoSansCJKsc"
            pdfmetrics.registerFont(TTFont(font_name, font_path, subfontIndex=0))
            return font_name
        except Exception as e:  # noqa: BLE001
            # reportlab TTC font registration may fail for various system-level reasons
            logger.warning(f"Failed to register TTC font: {e}")
            try:
                font_name = "STSong-Light"
                pdfmetrics.registerFont(UnicodeCIDFont(font_name))
                return font_name
            except Exception:  # noqa: BLE001
                # reportlab CID font registration may fail for various system-level reasons
                return "Helvetica"

    # TTF / OTF 文件
    try:
        font_name = f"CustomChinese_{Path(font_path).stem}"
        pdfmetrics.registerFont(TTFont(font_name, font_path))
        return font_name
    except Exception as e:  # noqa: BLE001
        # reportlab TTF font registration may fail for various system-level reasons
        logger.warning(f"Failed to register font {font_path}: {e}")
        try:
            font_name = "STSong-Light"
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))
            return font_name
        except Exception:  # noqa: BLE001
            # reportlab CID font registration may fail for various system-level reasons
            return "Helvetica"


def get_pillow_font_path() -> str:
    """获取 Pillow 可用的字体路径

    Pillow 需要 TTF/OTF 文件（不支持 TTC）。
    """
    font_path = get_chinese_font_path()
    if not font_path:
        return ""

    # TTC 不被 Pillow 直接支持，尝试找独立的 TTF/OTF
    if font_path.lower().endswith(".ttc"):
        # 查找缓存目录中的 TTF/OTF
        FONTS_DIR.mkdir(parents=True, exist_ok=True)
        for candidate in _SYSTEM_FONT_CANDIDATES:
            if not candidate.lower().endswith(".ttc"):
                cached = FONTS_DIR / candidate
                if cached.exists():
                    return str(cached)

        # 尝试下载独立的 TTF
        downloaded = _download_noto_sans_sc()
        if downloaded and not downloaded.lower().endswith(".ttc"):
            return downloaded

        # 降级：Pillow 可以尝试加载 TTC（部分版本支持）
        return font_path

    return font_path
