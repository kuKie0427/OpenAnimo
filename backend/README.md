# OpenAnimo Backend

FastAPI + SQLModel + PostgreSQL (asyncpg) 后端。测试使用内存 SQLite。

## Run

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 18765
```

WebSocket: `ws://localhost:18765/ws/projects/{project_id}`

