"""Tests for style template API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_list_style_templates_empty(async_client: AsyncClient):
    """Initially no templates unless seeded."""
    res = await async_client.get("/api/v1/style-templates")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data


async def test_create_custom_template(async_client: AsyncClient):
    """Create a custom style template via POST."""
    res = await async_client.post(
        "/api/v1/style-templates",
        json={
            "name": "My Custom",
            "slug": "my-custom",
            "style_prompt": "custom style, unique vibes",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["slug"] == "my-custom"
    assert data["category"] == "custom"
    assert data["name"] == "My Custom"


async def test_create_duplicate_slug_fails(async_client: AsyncClient):
    """Creating a template with an existing slug returns 409."""
    await async_client.post(
        "/api/v1/style-templates",
        json={
            "name": "First",
            "slug": "dup-slug",
            "style_prompt": "first style",
        },
    )
    res = await async_client.post(
        "/api/v1/style-templates",
        json={
            "name": "Second",
            "slug": "dup-slug",
            "style_prompt": "second style",
        },
    )
    assert res.status_code == 409


async def test_get_template_by_slug(async_client: AsyncClient):
    """Get a template by slug."""
    await async_client.post(
        "/api/v1/style-templates",
        json={
            "name": "Test Get",
            "slug": "test-get",
            "style_prompt": "test style",
        },
    )
    res = await async_client.get("/api/v1/style-templates/test-get")
    assert res.status_code == 200
    assert res.json()["slug"] == "test-get"


async def test_get_nonexistent_slug_404(async_client: AsyncClient):
    """Getting a nonexistent slug returns 404."""
    res = await async_client.get("/api/v1/style-templates/nonexistent")
    assert res.status_code == 404


async def test_update_custom_template(async_client: AsyncClient):
    """Update a custom style template."""
    await async_client.post(
        "/api/v1/style-templates",
        json={
            "name": "Updatable",
            "slug": "updatable",
            "style_prompt": "old prompt",
        },
    )
    res = await async_client.put(
        "/api/v1/style-templates/updatable",
        json={"name": "Updated Name", "style_prompt": "new prompt"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Updated Name"
    assert data["style_prompt"] == "new prompt"


async def test_delete_custom_template(async_client: AsyncClient):
    """Delete a custom style template."""
    await async_client.post(
        "/api/v1/style-templates",
        json={
            "name": "Deletable",
            "slug": "deletable",
            "style_prompt": "bye style",
        },
    )
    res = await async_client.delete("/api/v1/style-templates/deletable")
    assert res.status_code == 204

    # Verify it's gone
    res = await async_client.get("/api/v1/style-templates/deletable")
    assert res.status_code == 404


async def test_delete_nonexistent_404(async_client: AsyncClient):
    """Deleting a nonexistent template returns 404."""
    res = await async_client.delete("/api/v1/style-templates/nonexistent")
    assert res.status_code == 404


async def test_list_with_category_filter(async_client: AsyncClient):
    """Filter templates by category."""
    # Create a custom one
    await async_client.post(
        "/api/v1/style-templates",
        json={
            "name": "Filtered",
            "slug": "filtered-custom",
            "style_prompt": "filter style",
        },
    )
    res_custom = await async_client.get("/api/v1/style-templates?category=custom")
    assert res_custom.status_code == 200
    data_custom = res_custom.json()
    assert all(t["category"] == "custom" for t in data_custom["items"])
