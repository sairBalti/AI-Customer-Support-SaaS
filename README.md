# AI Customer Support Agent Platform

FastAPI backend with Clean Architecture. Local development uses free, Docker-hosted
infrastructure only (no paid cloud services required).

## Prerequisites

- Python 3.11+ (3.14 recommended; matches CI)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Engine + Compose v2)
- Git

## Quick start (Docker)

```bash
# 1. Environment files
cp .env.example .env
cp backend/.env.example backend/.env

# 2. Validate Compose file
docker compose config

# 3. Build and start MySQL, Redis, and the API
docker compose up --build -d

# 4. Apply Alembic migrations (schema is managed only via Alembic)
docker compose exec backend alembic upgrade head

# 5. Verify
curl http://127.0.0.1:8000/health
# → {"status":"ok"} (or equivalent 200 JSON)
```

| Resource | URL |
|----------|-----|
| Health | http://127.0.0.1:8000/health |
| Readiness | http://127.0.0.1:8000/ready |
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |

Default published ports: API `8000`, MySQL host `3307` → container `3306`, Redis `6379`
(override in root `.env` via `MYSQL_PORT`, `REDIS_PORT`, `API_PORT`).

**Database URLs**

| Runtime | `DATABASE_URL` host | Port |
|---------|---------------------|------|
| Backend container | `mysql` (Compose DNS) | `3306` (set by `docker-compose.yml`) |
| Host Alembic / host API | `localhost` | `3307` (Compose published port; see `backend/.env.example`) |

## Local development (without Docker for the API)

Use Docker for MySQL/Redis (or local installs) and run the API on the host:

```bash
docker compose up -d mysql redis

cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
# Ensure DATABASE_URL / REDIS_URL use localhost (Compose MySQL → localhost:3307)
alembic upgrade head
uvicorn app.main:app --reload
```

## Common Docker commands

```bash
# Logs
docker compose logs -f backend
docker compose logs -f mysql

# Stop
docker compose stop

# Stop and remove containers (keeps volumes)
docker compose down

# Reset local database + Redis + storage volumes (destructive)
docker compose down -v

# Rebuild API image after dependency changes
docker compose build --no-cache backend
docker compose up -d backend

# Shell inside the API container
docker compose exec backend bash
```

## Database migrations

Schema changes go through Alembic only — never create tables by hand.

```bash
# Inside Docker
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
docker compose exec backend alembic history

# On the host (backend venv active)
cd backend
alembic upgrade head
alembic check
```

## Tests and quality checks

Tests use in-memory SQLite and do **not** require Docker MySQL.

```bash
cd backend
python -m pytest
python -m ruff check .
python -m black --check .
python -m isort --check-only .
python -m mypy app
alembic check
```

GitHub Actions (`.github/workflows/backend-ci.yml`) runs the same quality gates on push/PR.

## Services in Compose

| Service | Image | Purpose |
|---------|-------|---------|
| `mysql` | `mysql:8.4` | Primary database (persistent volume) |
| `redis` | `redis:7-alpine` | Cache / future background jobs (AOF volume) |
| `backend` | build `./backend` | FastAPI API (`uvicorn app.main:app`) |

Celery workers, vector DB containers, Document/RAG/AI, and the frontend are **not**
started here; add them in later phases when those features are implemented.

## Documentation

Backend layout and modules: [`backend/README.md`](backend/README.md)

Architecture notes: `docs/`
