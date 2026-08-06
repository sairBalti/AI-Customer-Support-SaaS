# Backend — AI Customer Support Agent Platform

Production FastAPI backend scaffolded with **Clean Architecture**.

## Layers

| Layer | Path | Responsibility |
|-------|------|----------------|
| Presentation | `app/api` | HTTP routers, request/response schemas, middleware |
| Application | `app/application` | Use cases, application services, DTOs |
| Domain | `app/domain` | Entities, enums, value objects, repository/service ports |
| Infrastructure | `app/infrastructure` | MySQL, Redis, vector DB, S3, LLM SDKs, workers |
| Agents | `app/agents` | LangGraph support agent, prompts, tools |
| Core | `app/core` | Config, security, logging, shared cross-cutting concerns |

Dependencies point **inward** only: API → Application → Domain ← Infrastructure.

## Modules

Authentication · Company · Knowledge Base · Chat · Ticket · Analytics · Admin · AI

## Stack

- FastAPI (async)
- SQLAlchemy 2.x + Alembic (MySQL 8+)
- Redis, ChromaDB (dev) / Pinecone (prod)
- Local storage (dev) / S3 or R2 (prod)
- Gemini / OpenAI LLM clients
- Celery (or FastAPI BackgroundTasks for MVP)

## Getting started

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

- Liveness: `GET /health` → `200` (always, even if MySQL is down)
- Readiness: `GET /ready` → `200` when DB is up, `503` when unavailable
- OpenAPI: `http://127.0.0.1:8000/docs`

Database sessions are injected via `DbSession` (`app.api.deps`). The async engine
is created lazily and never required for process startup.

Business features are intentionally empty. Fill layers according to `docs/02_Architecture.md` and `docs/database/*`.
