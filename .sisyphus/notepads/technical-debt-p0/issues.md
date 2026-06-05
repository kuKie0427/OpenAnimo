# Task 1+2 Issues

## Existing Test Breakage
- `tests/test_agents/test_orchestrator_helpers.py` line 138 (`test_get_redis_returns_singleton`) monkeypatches `app.agents.orchestrator._redis_client` and `app.agents.orchestrator.redis`, which no longer exist after extraction.
- The test will fail because `_redis_client` and the `redis` module are now in `app.orchestration.redis`.
- This was NOT addressed per the "Do NOT modify any existing tests" constraint. A follow-up task should update this test to target `app.orchestration.redis` instead.
