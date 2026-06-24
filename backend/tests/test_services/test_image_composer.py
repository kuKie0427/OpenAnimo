from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.image_composer import ImageComposer


def _make_image(width: int, height: int, color: tuple[int, int, int] = (255, 0, 0)) -> Image.Image:
    return Image.new("RGB", (width, height), color=color)


def test_resize_to_fit_keeps_original_when_small_enough():
    composer = ImageComposer(max_width=800, max_height=600)
    img = _make_image(400, 300)

    resized = composer._resize_to_fit(img, 800, 600)

    assert resized.size == (400, 300)


def test_resize_to_fit_scales_down_preserving_aspect_ratio():
    composer = ImageComposer(max_width=800, max_height=600)
    img = _make_image(1600, 900)

    resized = composer._resize_to_fit(img, 800, 600)

    assert resized.size == (800, 450)


@pytest.mark.asyncio
async def test_compose_reference_image_without_characters_returns_shot_only(monkeypatch):
    composer = ImageComposer(max_width=800, max_height=600)
    shot = _make_image(1600, 900)

    async def fake_download(url: str):
        return shot

    monkeypatch.setattr(composer, "_download_image", fake_download)

    result = await composer.compose_reference_image("shot.png", [])
    image = Image.open(io.BytesIO(result))

    assert image.size == (800, 450)


@pytest.mark.asyncio
async def test_compose_reference_image_skips_failed_character_download(monkeypatch):
    composer = ImageComposer(max_width=800, max_height=600)
    shot = _make_image(1000, 600)
    character = _make_image(200, 200, (0, 255, 0))

    async def fake_download(url: str):
        if url == "broken.png":
            raise RuntimeError("download failed")
        if url == "shot.png":
            return shot
        return character

    monkeypatch.setattr(composer, "_download_image", fake_download)

    result = await composer.compose_reference_image("shot.png", ["broken.png", "char.png"])
    image = Image.open(io.BytesIO(result))

    assert image.width == 800
    assert image.height > 450


@pytest.mark.asyncio
async def test_compose_character_reference_image_validates_inputs(monkeypatch):
    composer = ImageComposer(max_width=800, max_height=600)

    with pytest.raises(ValueError, match="No character images"):
        await composer.compose_character_reference_image([])


@pytest.mark.asyncio
async def test_compose_character_reference_image_raises_when_all_fail(monkeypatch):
    composer = ImageComposer(max_width=800, max_height=600)

    async def fake_download(url: str):
        raise RuntimeError("download failed")

    monkeypatch.setattr(composer, "_download_image", fake_download)

    with pytest.raises(RuntimeError, match="All character images failed"):
        await composer.compose_character_reference_image(["char1.png", "char2.png"])


@pytest.mark.asyncio
async def test_compose_and_save_reference_image_writes_png(tmp_path, monkeypatch):
    composer = ImageComposer(max_width=800, max_height=600)
    composed = _make_image(500, 300)

    async def fake_compose(shot, chars):
        buffer = io.BytesIO()
        composed.save(buffer, format="PNG")
        return buffer.getvalue()

    monkeypatch.setattr(composer, "compose_reference_image", fake_compose)
    monkeypatch.setattr("app.services.image_composer.STATIC_DIR", tmp_path)

    url = await composer.compose_and_save_reference_image("shot.png", ["char.png"])

    assert url.startswith("/static/images/composed_")
    assert (tmp_path / "images").exists()


@pytest.mark.asyncio
async def test_compose_character_reference_image_scales_down_when_too_wide(monkeypatch):
    composer = ImageComposer(max_width=300, max_height=300)
    chars = [_make_image(400, 200), _make_image(400, 200)]

    async def fake_download(url: str):
        return chars.pop(0)

    monkeypatch.setattr(composer, "_download_image", fake_download)

    result = await composer.compose_character_reference_image(["a.png", "b.png"])
    image = Image.open(io.BytesIO(result))

    assert image.width <= 300
    assert image.height <= 300


@pytest.mark.asyncio
async def test_compose_character_reference_image_uses_min_target_height_when_zero(monkeypatch):
    composer = ImageComposer(max_width=800, max_height=0)
    char = _make_image(100, 100)

    async def fake_download(url: str):
        return char

    monkeypatch.setattr(composer, "_download_image", fake_download)

    result = await composer.compose_character_reference_image(["char.png"])
    image = Image.open(io.BytesIO(result))

    assert image.height >= 1
