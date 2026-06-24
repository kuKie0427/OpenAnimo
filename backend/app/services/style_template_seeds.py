"""Built-in style template seed data.

Defines the 11 existing styles from RenderAgent._style_descriptor plus 3 new ones
(guofeng-manga, cyberpunk, fairy-tale) as builtin templates.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.style_template import StyleTemplate

logger = logging.getLogger(__name__)

BUILTIN_STYLE_TEMPLATES: list[dict] = [
    {
        "slug": "anime",
        "name": "日系动漫",
        "category": "builtin",
        "description": "经典日式动画风格，赛璐珞上色，清晰线稿，大眼睛表现",
        "style_prompt": "anime, 2D illustration, cel-shading, vibrant colors, Japanese animation style",
        "color_palette": ["vibrant", "saturated", "warm"],
        "sort_order": 100,
    },
    {
        "slug": "shonen",
        "name": "少年热血",
        "category": "builtin",
        "description": "高对比明暗，动态构图，夸张透视",
        "style_prompt": "anime, shonen style, high contrast, dynamic composition, dramatic lighting, bold lines",
        "color_palette": ["high-contrast", "dramatic", "bold"],
        "sort_order": 90,
    },
    {
        "slug": "slice-of-life",
        "name": "日常治愈",
        "category": "builtin",
        "description": "柔和色调，圆润线条，温馨光影",
        "style_prompt": "anime, slice of life, soft pastel colors, warm lighting, rounded lines, cozy atmosphere",
        "color_palette": ["pastel", "soft", "warm"],
        "sort_order": 80,
    },
    {
        "slug": "manga",
        "name": "黑白漫画",
        "category": "builtin",
        "description": "网点纸，速度线，夸张表情，高对比",
        "style_prompt": "manga style, black and white, halftone dots, speed lines, high contrast ink",
        "color_palette": ["monochrome", "high-contrast"],
        "sort_order": 70,
    },
    {
        "slug": "donghua",
        "name": "国风动画",
        "category": "builtin",
        "description": "水墨质感，飘逸线条，东方配色",
        "style_prompt": "Chinese animation, ink wash, flowing lines, oriental color palette, watercolor textures",
        "color_palette": ["oriental", "muted", "ink-wash"],
        "sort_order": 60,
    },
    {
        "slug": "cinematic",
        "name": "电影质感",
        "category": "builtin",
        "description": "35mm胶片感，自然光，浅景深",
        "style_prompt": "cinematic, photorealistic, 35mm film grain, natural lighting, shallow depth of field",
        "color_palette": ["natural", "desaturated", "film"],
        "sort_order": 50,
    },
    {
        "slug": "pixar",
        "name": "3D卡通",
        "category": "builtin",
        "description": "Pixar风格渲染，圆润造型，全局光照",
        "style_prompt": "3D cartoon, Pixar-style rendering, smooth surfaces, global illumination, rounded shapes",
        "color_palette": ["vibrant", "smooth", "colorful"],
        "sort_order": 40,
    },
    {
        "slug": "lowpoly",
        "name": "低多边形",
        "category": "builtin",
        "description": "几何化造型，硬边光影，简约配色",
        "style_prompt": "low poly, geometric, faceted surfaces, hard edge lighting, minimalist palette",
        "color_palette": ["minimalist", "geometric", "hard-edge"],
        "sort_order": 30,
    },
    {
        "slug": "watercolor",
        "name": "水彩",
        "category": "builtin",
        "description": "晕染边缘，透明叠色，留白呼吸",
        "style_prompt": "watercolor, soft bleeding edges, transparent layering, white space breathing, painterly",
        "color_palette": ["soft", "translucent", "organic"],
        "sort_order": 20,
    },
    {
        "slug": "sketch",
        "name": "素描",
        "category": "builtin",
        "description": "铅笔线条，交叉排线，单色明暗",
        "style_prompt": "pencil sketch, cross-hatching, monochrome shading, rough lines, hand-drawn",
        "color_palette": ["monochrome", "rough", "hand-drawn"],
        "sort_order": 10,
    },
    {
        "slug": "realistic",
        "name": "写实风格",
        "category": "builtin",
        "description": "照片级真实，自然光影，细节精确",
        "style_prompt": "photorealistic, natural lighting, detailed textures, real-world proportions",
        "color_palette": ["natural", "detailed", "realistic"],
        "sort_order": 0,
    },
    # --- New styles ---
    {
        "slug": "guofeng-manga",
        "name": "国风漫画",
        "category": "builtin",
        "description": "融合国风与漫画，工笔线条，水墨上色，古韵意境",
        "style_prompt": "guofeng manga, Chinese traditional art, fine ink lines, watercolor coloring, classical oriental atmosphere",
        "color_palette": ["oriental", "ink-wash", "classical"],
        "sort_order": 65,
    },
    {
        "slug": "cyberpunk",
        "name": "赛博朋克",
        "category": "builtin",
        "description": "霓虹灯光，暗黑都市，科技感与破败并存",
        "style_prompt": "cyberpunk, neon lights, dark urban, high-tech low-life, rain-slicked streets, holographic",
        "color_palette": ["neon", "dark", "futuristic"],
        "negative_prompt": "bright, sunny, cheerful, pastoral",
        "sort_order": 45,
    },
    {
        "slug": "fairy-tale",
        "name": "童话绘本",
        "category": "builtin",
        "description": "柔和圆润，温暖色调，手绘质感，梦幻氛围",
        "style_prompt": "fairy tale illustration, soft rounded shapes, warm colors, hand-painted texture, dreamy atmosphere",
        "color_palette": ["warm", "soft", "dreamy"],
        "sort_order": 55,
    },
]


async def ensure_builtin_templates(session: AsyncSession) -> None:
    """Insert builtin style templates on first run (ON CONFLICT DO NOTHING via slug check)."""
    inserted = 0
    for seed in BUILTIN_STYLE_TEMPLATES:
        slug = seed["slug"]
        res = await session.execute(
            select(StyleTemplate).where(StyleTemplate.slug == slug)
        )
        if res.scalar_one_or_none() is not None:
            continue
        template = StyleTemplate(
            name=seed["name"],
            slug=slug,
            category=seed.get("category", "builtin"),
            description=seed.get("description"),
            style_prompt=seed["style_prompt"],
            color_palette=seed.get("color_palette", []),
            negative_prompt=seed.get("negative_prompt"),
            preview_image_url=seed.get("preview_image_url"),
            sort_order=seed.get("sort_order", 0),
            is_active=True,
        )
        session.add(template)
        inserted += 1
    if inserted:
        await session.commit()
        logger.info("ensure_builtin_templates: inserted %d new builtin style templates", inserted)
