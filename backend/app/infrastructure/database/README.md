# Database package layout

Infrastructure (this package)

- `base.py` — DeclarativeBase + MetaData naming conventions
- `session.py` — async engine, session factory, `get_db`, connectivity check
- `models/` — ORM entities (not generated yet)
- `repositories/` — repository adapters (later)

Rules

- Never connect to MySQL at import time or during app construction.
- `/health` must remain 200 even if MySQL is down.
- `/ready` reports database readiness without crashing the process.
- Application services own transactions; `get_db` only yields/closes sessions.
