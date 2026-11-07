# DC-IOC Platform · Data Center Intelligent Operations Center

> **v0.16.0** — An integrated DCIM + asset + operations platform for (AI) data centers.
> Four-phase upgrade completed: docs/quality gates, full OpenAPI contract + CMDB relations, IPAM/discovery/procurement/custom fields, plugin registry/GraphQL/tenant isolation/configurable dashboard. See [docs/IMPLEMENTATION_PLAN.md](./docs/IMPLEMENTATION_PLAN.md).
> Stack: **Vue 3 + TypeScript + Vite** (frontend) · **Python FastAPI** (backend) · **PostgreSQL/TimescaleDB + Redis** (storage) · **three.js** (3D digital twin).
> Full Chinese documentation: [README.md](./README.md) · Upgrade roadmap: [docs/IMPLEMENTATION_PLAN.md](./docs/IMPLEMENTATION_PLAN.md) · Changelog: [CHANGELOG.md](./CHANGELOG.md).

---

## What it is

DC-IOC is a self-hosted platform that unifies facility monitoring, alarm handling, IT asset management and operations workflows for data centers. It covers 9 navigation groups and 60+ pages:

| Domain | Highlights |
|---|---|
| **IOC Cockpit** | Campus/room KPIs, PUE trends, per-domain health, active alarms |
| **Facility Monitoring** | Chiller plant (8 chillers, 4+2+N), CRAC, liquid cooling (CDU / cold plate / GPU-level), 10kV / 0.4kV power, genset, fuel, batteries, CCTV / ACS / IDS / fire, network devices, health scoring, 3D twin & big screens |
| **Alarms** | Threshold engine (13 device classes), 5-min convergence, suppression, notification center, alarm→ticket automation |
| **Operations** | Inspection, maintenance, duty rosters, tickets with state machine + SLA, room access, fault impact analysis, drills, risk matrix, suppliers, iHealth monthly report |
| **Assets** | Unified equipment ledger (11 domains), U-position (RFID + work-order fusion), cabinets, capacity What-if simulator, lifecycle, tenants |
| **Energy** | Power forecasting and iCooling optimization |
| **Knowledge & AI** | Knowledge base (PDF/Word import), collaboration, AI assistant with hot-swappable LLM models |
| **Integration** | Thing models (property/service/event), collectors, telemetry, ITIL workflows, multi-datacenter management & comparison |
| **System** | Operation audit + row-level change audit |

Data flow: collectors (mock / Kafka / real BMS/DCIM) → `POST /api/external/*` → `metric_raws` TimescaleDB hypertable → `dc_aggregator` (real data preferred, generated fallback with `_source` marker) → all business endpoints → WebSocket push (5s KPI snapshot + alarms).

---

## Quick start

### Option A — Docker Compose (recommended)

```bash
# Development: hot reload + Prometheus + frontend dev server on :5173
docker compose -f docker-compose.yml -f deploy/docker-compose.dev.yml up -d --build

# Windows one-click
start.bat
```

| Service | URL |
|---|---|
| Frontend | http://localhost:8080 (prod image) / http://localhost:5173 (dev) |
| API docs (Swagger) | http://localhost:8000/docs |
| Health / readiness | http://localhost:8000/health · `/ready` |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (staging / prod) |
| Default login | `admin` / `admin123` |

### Option B — Local development (no Docker for the app itself)

```bash
# 1. Databases
cd deploy && docker compose up -d postgres redis

# 2. Backend
cd ../backend
python -m venv .venv && .venv\Scripts\activate     # Windows; use source .venv/bin/activate on Linux/macOS
pip install -r requirements.txt
copy .env.dev .env                                   # cp on Linux/macOS
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd ../frontend
npm install
npm run dev                                          # http://localhost:5173
```

### Option C — Staging / Production

```bash
export SECRET_KEY=$(openssl rand -hex 32)
export POSTGRES_PASSWORD=$(openssl rand -hex 16)
export EXTERNAL_COLLECTOR_TOKEN=$(openssl rand -hex 32)

docker compose -f docker-compose.yml -f deploy/docker-compose.staging.yml up -d
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d
```

> Production startup is blocked by `app/core/secret_check.py` if `SECRET_KEY` is shorter than 16 chars or default admin credentials are used. `.env*` files are git-ignored; only `.env.example` is committed.

---

## Architecture (layers)

```
api/v1/endpoints  →  services  →  crud  →  models
      ↓                ↓          ↓
   schemas (DTO)   cache/Redis  db/session (SQLAlchemy)
```

* Upper layers depend only on lower layers; responses are serialized with Pydantic `schemas`.
* 28+ business domains are aggregated in `app/api/v1/router.py` and mounted at `/api`.
* Auth: JWT Bearer (`POST /api/auth/login`, refresh on 401) + RBAC (`admin` / `operator` / `viewer`); external collectors use a separate `X-Collector-Token`.
* Time series: `metric_raws` hypertable — compression after 7 days, 90-day retention, 5min/1h continuous aggregates.
* Observability: Prometheus `/metrics`, structured loguru JSON logs, Loki/Promtail, Grafana dashboards, 12 alert rules.
* Deployment: separate `docker-compose.{dev,staging,prod}.yml` overlays, pg_dump backup/restore scripts, Locust load tests.

---

## API overview

All endpoints live under `/api`; Swagger UI is at `/docs`. Representative groups:

| Group | Endpoints |
|---|---|
| auth | `POST /api/auth/login`, `/refresh`, `/change-password`, `/users`, `/register` (feature-flagged) |
| dashboard | `GET /api/dashboard/overview`, `/campuses`, `/campus-comparison`, `/overview/trends` (30s cache) |
| equipment / hvac / power / security | 11-domain ledger, cooling, power, physical security |
| alarms / alarm-rules / alarm-history | alarm center, rule engine, history |
| tickets / ops | ticket state machine + SLA, inspection, maintenance, shift, drills, risk, capacity What-if |
| external | `POST /api/external/device/register`, `/metrics/upload` (collector token) |
| thing-models / idc | thing model CRUD, multi-datacenter CRUD / switch / compare / unified alarms |
| notifications | channel CRUD, delivery records, test send |
| graphic-config / refuel-records | scene overlay editor, real refuel records |

The full endpoint list (method / path / auth) is generated into `backend/api_endpoints.md` by `gen_api.py`; the machine-readable contract is `frontend/openapi.json` (see [docs/IMPLEMENTATION_PLAN.md](./docs/IMPLEMENTATION_PLAN.md) for the full-contract migration).

---

## Configuration

| File | Purpose |
|---|---|
| `backend/.env.example` | All supported variables (template, committed) |
| `backend/.env.dev` / `.env.staging` / `.env.prod` | Per-environment defaults (git-ignored) |

Key variables: `APP_ENV`, `SECRET_KEY`, `POSTGRES_*`, `REDIS_HOST`, `DB_POOL_SIZE`, `EXTERNAL_COLLECTOR_TOKEN`, `ALLOW_SELF_REGISTER`, `UPLOAD_DIR` / `UPLOAD_MAX_BYTES`, `ALARM_AUTO_TICKET_MIN_LEVEL`, `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` / `LLM_MODELS`, `BACKUP_DIR` / `RETENTION_DAYS` / `BACKUP_ALERT_WEBHOOK`.

The AI assistant works fully offline (local knowledge base retrieval). When `LLM_API_KEY` is set, an OpenAI-compatible `/chat/completions` endpoint is used for polishing; any failure falls back to retrieval. Multiple models can be hot-swapped at runtime via `/api/ops/assistant/models*`.

> Changing `.env` requires **recreating** the container (`docker compose ... up -d backend`); `docker compose restart` does not re-read `.env`.

---

## Quality, tests & docs

```bash
# Backend
cd backend && ruff check app/ && pytest ../tests/ -q --cov=app

# Frontend
cd frontend && npx vue-tsc --noEmit && npm run test:run && npm run build

# i18n parity gate (zh/en)
python scripts/check_i18n_keys.py --json

# End-to-end smoke (independent package, see frontend/e2e/README.md)
cd frontend/e2e && npm install && npx playwright install chromium && npm test
```

* CI: `.github/workflows/ci.yml` — backend lint / bandit / safety / pytest+coverage gate / SQL-injection guard; frontend typecheck / lint / vitest / build; Docker build + Trivy on `main`.
* Load tests: `tests/load/locustfile.py` (9 endpoints, headless CI mode).
* Backup: `deploy/backup.sh` (pg_dump + gzip + 14-day retention + optional webhook), `deploy/scripts/restore.sh`.

---

## Contributing & license

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the branch/commit convention, the **four-piece checklist for adding a page** (route + nav + icon + i18n), Alembic dual-track migrations, and the pre-commit setup. Architecture decisions are recorded in [docs/adr](./docs/adr/README.md).

License: see the repository's LICENSE file. Referenced upstream projects (`django-idcops`, `idc_assest`) are Apache-2.0 / their respective licenses and are used for design reference only.
