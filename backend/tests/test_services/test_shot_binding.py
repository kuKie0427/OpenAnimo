from __future__ import annotations

import pytest

from app.services.shot_binding import resolve_shot_bound_approved_characters
from tests.factories import create_character, create_project, create_shot


@pytest.mark.asyncio
async def test_resolve_shot_bound_approved_characters_with_approved_ids(test_session, test_settings):
    project = await create_project(test_session)
    char1 = await create_character(test_session, project_id=project.id, name="A")
    char2 = await create_character(test_session, project_id=project.id, name="B")
    shot = await create_shot(test_session, project_id=project.id)
    shot.approved_character_ids = [char1.id, char2.id]
    await test_session.commit()

    result = await resolve_shot_bound_approved_characters(test_session, shot)
    assert len(result) == 2
    assert result[0].name == "A"
    assert result[1].name == "B"


@pytest.mark.asyncio
async def test_resolve_shot_bound_falls_back_to_character_ids(test_session, test_settings):
    project = await create_project(test_session)
    char = await create_character(test_session, project_id=project.id, name="C")
    shot = await create_shot(test_session, project_id=project.id)
    shot.approved_character_ids = None
    shot.character_ids = [char.id]
    await test_session.commit()

    result = await resolve_shot_bound_approved_characters(test_session, shot)
    assert len(result) == 1
    assert result[0].name == "C"


@pytest.mark.asyncio
async def test_resolve_shot_bound_no_character_ids(test_session, test_settings):
    project = await create_project(test_session)
    shot = await create_shot(test_session, project_id=project.id)
    shot.approved_character_ids = None
    shot.character_ids = []
    await test_session.commit()

    result = await resolve_shot_bound_approved_characters(test_session, shot)
    assert result == []


@pytest.mark.asyncio
async def test_resolve_shot_bound_preserves_order(test_session, test_settings):
    project = await create_project(test_session)
    char_a = await create_character(test_session, project_id=project.id, name="A")
    char_b = await create_character(test_session, project_id=project.id, name="B")
    shot = await create_shot(test_session, project_id=project.id)
    shot.approved_character_ids = [char_b.id, char_a.id]
    await test_session.commit()

    result = await resolve_shot_bound_approved_characters(test_session, shot)
    assert len(result) == 2
    assert result[0].id == char_b.id
    assert result[1].id == char_a.id


@pytest.mark.asyncio
async def test_resolve_shot_bound_missing_character(test_session, test_settings):
    project = await create_project(test_session)
    char = await create_character(test_session, project_id=project.id, name="X")
    shot = await create_shot(test_session, project_id=project.id)
    shot.approved_character_ids = [char.id, 99999]
    await test_session.commit()

    result = await resolve_shot_bound_approved_characters(test_session, shot)
    assert len(result) == 1
    assert result[0].id == char.id
