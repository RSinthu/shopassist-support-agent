# ShopAssist Backend

FastAPI backend for ShopAssist, a multi-agent e-commerce support system.

## Run

```powershell
uv sync
Copy-Item .env.example .env
uv run fastapi dev app/main.py
```

Open http://127.0.0.1:8000/docs.

## Test

```powershell
uv run pytest
```

## Layout

| Folder | Job |
|---|---|
| `app/db` | Database connection and tables |
| `app/auth` | Password hashing, JWT, role checks |
| `app/services` | All business logic and rules (no AI, no HTTP) |
| `app/api` | Thin HTTP routes that call services |
| `app/mcp_server` | MCP tools that call services |
| `app/agent` | LangGraph agent, prompts, RAG |
| `scripts` | Seed data, build the search index |
| `tests` | pytest: rules, ownership, auth |
| `evals` | AI behaviour evaluations |
