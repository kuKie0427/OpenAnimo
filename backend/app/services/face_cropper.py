"""面部裁剪服务 - 使用 InsightFace 检测并裁剪面部区域。

用于从角色全身图中提取面部特写，提升分镜图生成时的角色面部一致性。
"""

from __future__ import annotations

import io
import logging

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# InsightFace 模型首次加载会自动下载 buffalo_l 模型（~300MB）
# 后续使用从缓存读取
_FACE_ANALYSIS_APP = None
_INIT_ATTEMPTED = False


def _get_face_analysis():
    """延迟初始化 InsightFace FaceAnalysis（线程安全的单例）"""
    global _FACE_ANALYSIS_APP, _INIT_ATTEMPTED
    if _FACE_ANALYSIS_APP is not None:
        return _FACE_ANALYSIS_APP
    if _INIT_ATTEMPTED:
        return None
    _INIT_ATTEMPTED = True
    try:
        from insightface.app import FaceAnalysis

        app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        app.prepare(ctx_id=-1, det_size=(640, 640))  # ctx_id=-1 表示 CPU
        _FACE_ANALYSIS_APP = app
        logger.info("InsightFace FaceAnalysis initialized successfully (CPU mode)")
        return app
    except (ImportError, OSError, RuntimeError) as e:
        logger.warning("Failed to initialize InsightFace, face cropping disabled: %s", e)
        return None


def is_face_cropping_available() -> bool:
    """检查面部裁剪功能是否可用"""
    return _get_face_analysis() is not None


def detect_faces(image_bytes: bytes) -> list[dict]:
    """检测图片中的面部，返回面部信息列表。

    Args:
        image_bytes: 图片字节流

    Returns:
        面部信息列表，每个元素包含:
        - bbox: [x1, y1, x2, y2] 边界框
        - det_score: 检测置信度
        - embedding: 面部嵌入向量（512维 numpy array）
    """
    app = _get_face_analysis()
    if app is None:
        return []

    # bytes → numpy array
    img_array = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img_array is None:
        return []

    faces = app.get(img_array)
    result = []
    for face in faces:
        result.append(
            {
                "bbox": face.bbox.tolist(),
                "det_score": float(face.det_score),
                "embedding": face.normed_embedding,
            }
        )
    return result


def crop_face_from_image(
    image_bytes: bytes,
    expand_ratio: float = 1.8,
    target_size: int | None = 512,
) -> bytes | None:
    """从图片中检测并裁剪最大的面部区域。

    Args:
        image_bytes: 图片字节流
        expand_ratio: 裁剪区域扩展比例（1.0 = 仅面部，1.8 = 包含头发和下巴）
        target_size: 目标裁剪尺寸（正方形），None 则保持原始比例

    Returns:
        裁剪后的图片字节流（PNG），未检测到面部则返回 None
    """
    faces = detect_faces(image_bytes)
    if not faces:
        return None

    # 取置信度最高的面部
    best_face = max(faces, key=lambda f: f["det_score"])
    x1, y1, x2, y2 = [int(v) for v in best_face["bbox"]]

    # 解码原图
    img_array = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img_array is None:
        return None

    img_h, img_w = img_array.shape[:2]

    # 计算扩展后的裁剪区域
    face_w, face_h = x2 - x1, y2 - y1
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    expand_w, expand_h = int(face_w * expand_ratio), int(face_h * expand_ratio)

    # 确保正方形裁剪（以较大的维度为准）
    crop_size = max(expand_w, expand_h)

    # 计算裁剪坐标（居中，不超出图片边界）
    crop_x1 = max(0, cx - crop_size // 2)
    crop_y1 = max(0, cy - crop_size // 2)
    crop_x2 = min(img_w, crop_x1 + crop_size)
    crop_y2 = min(img_h, crop_y1 + crop_size)

    # 修正：如果裁剪区域超出右/下边界，向左/上移动
    if crop_x2 - crop_x1 < crop_size:
        crop_x1 = max(0, crop_x2 - crop_size)
    if crop_y2 - crop_y1 < crop_size:
        crop_y1 = max(0, crop_y2 - crop_size)

    # 裁剪
    crop = img_array[crop_y1:crop_y2, crop_x1:crop_x2]

    # 缩放到目标尺寸
    if target_size and (crop.shape[0] != target_size or crop.shape[1] != target_size):
        crop = cv2.resize(crop, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)

    _, buf = cv2.imencode(".png", crop)
    return buf.tobytes()


def compose_face_reference_strip(
    image_bytes_list: list[bytes],
    expand_ratio: float = 1.8,
    face_size: int = 256,
    max_width: int = 1024,
) -> bytes | None:
    """从多张图片中裁剪面部并拼成横向条带。

    布局：
    ┌────────┬────────┬────────┐
    │  脸1   │  脸2   │  脸3   │
    └────────┴────────┴────────┘

    Args:
        image_bytes_list: 多张角色图片的字节流列表
        expand_ratio: 面部裁剪扩展比例
        face_size: 每张面部的尺寸（正方形）
        max_width: 最大宽度

    Returns:
        拼接后的图片字节流（PNG），全部未检测到面部则返回 None
    """
    face_crops: list[Image.Image] = []

    for img_bytes in image_bytes_list:
        face_bytes = crop_face_from_image(
            img_bytes, expand_ratio=expand_ratio, target_size=face_size
        )
        if face_bytes:
            face_img = Image.open(io.BytesIO(face_bytes)).convert("RGB")
            face_crops.append(face_img)

    if not face_crops:
        return None

    # 计算布局
    n = len(face_crops)
    cell_w = min(face_size, max_width // n)
    cell_h = cell_w  # 正方形

    # 缩放所有面部到相同尺寸
    resized = [img.resize((cell_w, cell_h), Image.Resampling.LANCZOS) for img in face_crops]

    # 创建画布
    total_w = cell_w * n
    canvas = Image.new("RGB", (total_w, cell_h), color=(255, 255, 255))

    x_pos = 0
    for img in resized:
        canvas.paste(img, (x_pos, 0))
        x_pos += cell_w

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()
