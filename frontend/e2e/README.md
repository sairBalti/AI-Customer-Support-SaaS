# Playwright E2E environment
# ==========================

## Services

- **Backend / DB / Redis:** from repo root run `docker compose up -d` until backend health is green
  (`http://127.0.0.1:8000/health` → 200). On a fresh volume also run
  `docker compose exec backend alembic upgrade head`.
- **LLM:** keep `LLM_PROVIDER=fake` (`LLM_MODEL=fake-v1`). E2E must not require Gemini/OpenAI keys.
- **Frontend:** Playwright starts `npm run dev` on port **5175** unless one is already running
  (`reuseExistingServer` is enabled outside CI).

## Credentials / seed

1. Copy `.env.e2e.example` → `.env.e2e` (gitignored). Do not commit real secrets.
2. Bootstrap Super Admin must already exist (local bootstrap or CI seed step).
3. `global-setup` then:
   - Creates missing shared role users (`e2e.company.admin@…`, manager, agent, customer) on the
     Super Admin tenant (or `E2E_COMPANY_ID`) so knowledge/chat stay co-tenant
   - Creates/reuses a dedicated FREE company (`E2E_COMPANY_SLUG`, default `e2e-tenant`) plus
     `e2e.free.admin@…` for the oversized-upload test only
   - Never deletes documents/companies/users and never touches non-`e2e.*` accounts

## Auth strategy (refresh-token rotation)

The backend **rotates refresh tokens** on login/refresh. Playwright `storageState` /
`addInitScript` patterns that re-inject a stale refresh token on every navigation force logout
when the client rotates and writes a new token to `sessionStorage`.

Current strategy (required):

- Fresh **API login per authenticated fixture**
- Inject refresh token into `sessionStorage` **once** after opening `/login`
- Prefer UI login fallback if `/app` still redirects to login
- `workers: 1` so fixtures never race the same credentials/session
- Role metadata under `e2e/.auth/*.json` is for helpers (user ids), **not** Playwright storageState auth

## Commands

```bash
npm run test:e2e
npm run test:e2e:ui
npm run test:e2e:debug
npm run test:e2e:report
```

Artifacts on failure: `test-results/` (trace / screenshot / video) and `playwright-report/`.

## Browser coverage

- **Required:** Chromium (local + CI)
- **Future:** Firefox / WebKit (not in CI yet)

## Size-limit E2E

Backend enforces per-plan upload limits (`FREE` = 10 MB). The oversized upload test authenticates
as the FREE-tenant Company Admin and uploads an 11 MB `.txt` file.
