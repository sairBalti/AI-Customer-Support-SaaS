# Alembic Migrations

Async SQLAlchemy 2.0 environment wired to the application:

| Piece | Source |
|-------|--------|
| Database URL | `Settings.database_url` (`.env` → `DATABASE_URL`) |
| Metadata | `app.infrastructure.database.base.Base.metadata` |
| Models import | `app.infrastructure.database.models` |
| Engine | `async_engine_from_config` + `NullPool` + `run_sync` |

## Commands (from `backend/`)

```bash
# Host tools against Compose MySQL (default publish 3307 → container 3306):
# DATABASE_URL=mysql+aiomysql://user:password@localhost:3307/ai_customer_support
#
# Inside the backend container, Compose sets @mysql:3306 automatically.
# Prefer: docker compose exec backend alembic upgrade head

alembic revision --autogenerate -m "describe change"
alembic upgrade head
alembic downgrade -1
alembic history
alembic check
```

Rules (see `docs/database/01_Design_Principles.md`):

- One logical change per migration
- Migrations must be reversible
- Never edit a migration after it has been applied in any shared environment
- Empty autogenerate diffs are skipped (no empty revision files)
