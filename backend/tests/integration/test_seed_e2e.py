from __future__ import annotations

import pytest

from app.agents.render import RenderAgent
from tests.agent_fixtures import FakeImageService, FakeLLM, make_context
from tests.factories import create_character, create_project, create_run, create_shot

INT32_MAX = 2_147_483_647


@pytest.mark.asyncio
async def test_character_seed_passed_to_image_on_first_render(
    monkeypatch, test_session, test_settings
):
    """E2E-SM-01: Character seed is generated and passed to image service on first render.

    Verifies that when a character is rendered for the first time with no pre-existing seed,
    (1) a random int32 seed is generated, (2) it is passed to the image service via
    generate_url kwargs, and (3) the character receives an image_url.
    """
    project = await create_project(test_session, title="SM01")
    run = await create_run(test_session, project_id=project.id)
    char = await create_character(
        test_session, project_id=project.id, name="Hero", image_url=None
    )

    # Stub services that try to download images or call LLM during character rendering
    async def _stub_compute_face_embedding(image_url: str):
        return None

    async def _stub_auto_populate_visual_notes(character, llm_service):
        return "stub visual notes"

    monkeypatch.setattr(
        "app.agents.render.compute_face_embedding", _stub_compute_face_embedding
    )
    monkeypatch.setattr(
        "app.agents.render.auto_populate_visual_notes", _stub_auto_populate_visual_notes
    )

    # Wire up FakeImageService with kwargs capture
    image_service = FakeImageService()
    captured_kwargs: dict = {}
    original_generate = image_service.generate_url

    async def _record_generate(**kwargs):
        captured_kwargs.update(kwargs)
        return await original_generate(**kwargs)

    monkeypatch.setattr(image_service, "generate_url", _record_generate)

    ctx = await make_context(
        test_session,
        test_settings,
        project=project,
        run=run,
        llm=FakeLLM("{}"),
        image=image_service,
    )

    agent = RenderAgent()
    await agent.run_characters(ctx)

    await test_session.refresh(char)

    # Assert character received an image URL
    assert char.image_url is not None, "Expected character.image_url to be set after render"

    # Assert seed was passed to generate_url
    assert "seed" in captured_kwargs, (
        f"Expected 'seed' in generate_url kwargs, got: {list(captured_kwargs.keys())}"
    )
    seed_val = captured_kwargs["seed"]
    assert 1 <= seed_val <= INT32_MAX, f"seed {seed_val} should be in int32 range [1, {INT32_MAX}]"


@pytest.mark.asyncio
async def test_shot_seed_generated_and_persisted(
    monkeypatch, test_session, test_settings
):
    """E2E-SM-02: Shot seed is generated on first render and persisted to database.

    Verifies that when a shot is rendered for the first time with no pre-existing seed,
    (1) a random int32 seed is generated, (2) it is stored on the Shot model, and
    (3) the shot receives an image_url.
    """
    project = await create_project(test_session, title="SM02")
    run = await create_run(test_session, project_id=project.id)
    shot = await create_shot(
        test_session, project_id=project.id, order=1, image_url=None
    )

    assert shot.seed is None, "Precondition: shot.seed should be None before render"

    image_service = FakeImageService()
    captured_kwargs: dict = {}
    original_generate = image_service.generate_url

    async def _record_generate(**kwargs):
        captured_kwargs.update(kwargs)
        return await original_generate(**kwargs)

    monkeypatch.setattr(image_service, "generate_url", _record_generate)

    ctx = await make_context(
        test_session,
        test_settings,
        project=project,
        run=run,
        llm=FakeLLM("{}"),
        image=image_service,
    )

    agent = RenderAgent()
    await agent.run_shots(ctx)

    await test_session.refresh(shot)

    # Assert shot.seed was persisted
    assert shot.seed is not None, "Expected shot.seed to be set after render"
    assert 1 <= shot.seed <= INT32_MAX, (
        f"shot.seed {shot.seed} should be in int32 range [1, {INT32_MAX}]"
    )

    # Assert shot received an image URL
    assert shot.image_url is not None, "Expected shot.image_url to be set after render"

    # Assert seed was passed to generate_url
    assert "seed" in captured_kwargs, (
        f"Expected 'seed' in generate_url kwargs, got: {list(captured_kwargs.keys())}"
    )
    assert captured_kwargs["seed"] == shot.seed, (
        f"Seed in generate_url ({captured_kwargs['seed']}) "
        f"should match shot.seed ({shot.seed})"
    )


@pytest.mark.asyncio
async def test_shot_seed_passed_to_image_service_matches_db(
    monkeypatch, test_session, test_settings
):
    """E2E-SM-03: Seed passed to image service matches the seed stored in database.

    Verifies that when a shot renders, the seed sent to the image service's generate_url
    is exactly the same value as shot.seed stored in the database.
    """
    project = await create_project(test_session, title="SM03")
    run = await create_run(test_session, project_id=project.id)
    shot = await create_shot(
        test_session, project_id=project.id, order=1, image_url=None
    )

    image_service = FakeImageService()
    captured_kwargs: dict = {}
    original_generate = image_service.generate_url

    async def _record_generate(**kwargs):
        captured_kwargs.update(kwargs)
        return await original_generate(**kwargs)

    monkeypatch.setattr(image_service, "generate_url", _record_generate)

    ctx = await make_context(
        test_session,
        test_settings,
        project=project,
        run=run,
        llm=FakeLLM("{}"),
        image=image_service,
    )

    agent = RenderAgent()
    await agent.run_shots(ctx)

    await test_session.refresh(shot)

    # Primary assertion: DB seed == generate_url seed
    assert shot.seed is not None, "Expected shot.seed to be set"
    assert "seed" in captured_kwargs, "Expected seed in generate_url kwargs"
    assert captured_kwargs["seed"] == shot.seed, (
        f"Mismatch: generate_url seed={captured_kwargs['seed']}, "
        f"shot.seed={shot.seed}"
    )


@pytest.mark.asyncio
async def test_shot_seed_reused_on_regeneration(
    monkeypatch, test_session, test_settings
):
    """E2E-SM-04: Seed is reused (not regenerated) on subsequent renders.

    Verifies that:
    (1) When a shot with a pre-set seed renders, the existing seed is passed to the
        image service (not replaced with a new random value).
    (2) After clearing image_url and re-rendering, the same seed is reused.
    """
    project = await create_project(test_session, title="SM04")
    run = await create_run(test_session, project_id=project.id)
    shot = await create_shot(
        test_session, project_id=project.id, order=1, image_url=None
    )

    # Pre-set a known seed on the shot
    KNOWN_SEED = 42
    shot.seed = KNOWN_SEED
    test_session.add(shot)
    await test_session.commit()

    image_service = FakeImageService()
    captured_kwargs: dict = {}
    original_generate = image_service.generate_url

    async def _record_generate(**kwargs):
        captured_kwargs.update(kwargs)
        return await original_generate(**kwargs)

    monkeypatch.setattr(image_service, "generate_url", _record_generate)

    ctx = await make_context(
        test_session,
        test_settings,
        project=project,
        run=run,
        llm=FakeLLM("{}"),
        image=image_service,
    )

    agent = RenderAgent()

    # ── First render: should use the pre-set seed ──
    captured_kwargs.clear()
    await agent.run_shots(ctx)

    await test_session.refresh(shot)
    assert shot.seed == KNOWN_SEED, (
        f"After first render, shot.seed should remain {KNOWN_SEED}, got {shot.seed}"
    )
    assert captured_kwargs.get("seed") == KNOWN_SEED, (
        f"First render: expected seed={KNOWN_SEED} in generate_url, "
        f"got {captured_kwargs.get('seed')}"
    )

    # ── Simulate regeneration: clear image_url so the shot is picked up again ──
    shot.image_url = None
    test_session.add(shot)
    await test_session.commit()

    # ── Second render: should reuse the same seed ──
    captured_kwargs.clear()
    await agent.run_shots(ctx)

    await test_session.refresh(shot)
    assert shot.seed == KNOWN_SEED, (
        f"After second render, shot.seed should remain {KNOWN_SEED}, got {shot.seed}"
    )
    assert captured_kwargs.get("seed") == KNOWN_SEED, (
        f"Second render: expected seed={KNOWN_SEED} in generate_url, "
        f"got {captured_kwargs.get('seed')}"
    )
