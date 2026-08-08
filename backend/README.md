# Backend — AI Customer Support Agent Platform

Production FastAPI backend with **Clean Architecture**.

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

Authentication · Company · User · Role/RBAC · (Knowledge Base · Chat · Ticket · Analytics · AI — later)

## Stack

- FastAPI (async)
- SQLAlchemy 2.x + Alembic (MySQL 8+)
- Redis (prepared; optional until caching/workers land)
- Local storage (dev) / S3 or R2 (prod — later)
- Gemini / OpenAI LLM clients (later)
- Celery (later background-processing phase)

## Docker development (recommended)

From the **repository root** (see root [`README.md`](../README.md)):

```bash
cp .env.example .env
cp backend/.env.example backend/.env
docker compose up --build -d
docker compose exec backend alembic upgrade head
curl http://127.0.0.1:8000/health
```

Compose overrides `DATABASE_URL` / `REDIS_URL` to Docker DNS (`mysql:3306`, `redis:6379`).
`backend/.env` is for **host** tools and should use `localhost:3307` for MySQL when using
the default Compose publish mapping (see `.env.example`). Local storage persists in the
`backend_storage` volume.

## Local development (API on the host)

```bash
# Optional: infrastructure only
docker compose up -d mysql redis

cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
# Use localhost:3307 when MySQL is the Compose service (default published port)
alembic upgrade head
uvicorn app.main:app --reload
```

- Liveness: `GET /health` → `200` (always, even if MySQL is down)
- Readiness: `GET /ready` → `200` when DB is up, `503` when unavailable
- OpenAPI: `http://127.0.0.1:8000/docs`

Database sessions are injected via `DbSession` (`app.api.deps`). The async engine
is created lazily and never required for process startup.

## Migrations

```bash
# Host
alembic upgrade head
alembic check

# Docker
docker compose exec backend alembic upgrade head
```

## Tests and CI parity

```bash
python -m pytest
python -m ruff check .
python -m black --check .
python -m isort --check-only .
python -m mypy app
alembic check
```

Fill remaining domains according to `docs/` when those phases begin.
