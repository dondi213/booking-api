# Booking API

A REST API to book shared resources (meeting rooms, sports courts, desks) **without double bookings**, deployed to the cloud with a full CI/CD pipeline.

Built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0** and **Alembic**, shipped with **Docker**, **GitHub Actions** and **Render**.

🔗 **Live demo:** `https://<your-service>.onrender.com/docs` *(update after deploying)*

## Features

- JWT authentication, user and admin roles
- Admins create resources; anyone can see resources and their availability per day
- Users create, list and cancel their bookings
- **No double bookings, guaranteed twice:**
  1. The service checks for overlapping bookings before inserting
  2. A PostgreSQL **`EXCLUDE` constraint** (`btree_gist` + `tstzrange`) rejects overlaps even under concurrent requests
- Business rules: bookings must be in the future, 30 min to 4 h long, at most 90 days ahead; past bookings can't be cancelled
- Timezone-safe: the API only accepts datetimes with a timezone and stores everything in UTC
- **Alembic migrations**, tested on PostgreSQL in CI (upgrade → downgrade → upgrade)
- **CI/CD**: lint + tests + migrations on every push; automatic deploy to Render when `main` is green

## Tech stack

Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL 16 · pytest · Docker · GitHub Actions · Render

## Architecture

```
GitHub push ─► GitHub Actions ─┬─ ruff + pytest
                               ├─ alembic on PostgreSQL
                               └─ (main, all green) ─► Render deploy hook
                                                         │
                                       ┌─────────────────┘
                                       ▼
                     Render: Docker container (alembic upgrade head → uvicorn)
                                       │
                                       ▼
                              Render PostgreSQL
```

Code layout:

```
app/
├── main.py              # FastAPI app and health check
├── models.py            # User, Resource, Booking
├── schemas.py           # Pydantic validation
├── services/bookings.py # Business rules (overlaps, durations, cancellation)
├── routers/             # auth, resources, bookings
└── create_admin.py      # CLI to create an admin user
migrations/              # Alembic (includes the EXCLUDE constraint)
```

## Getting started

### Docker

```bash
docker compose up --build
docker compose exec api python -m app.create_admin admin@example.com "admin12345"
```

Open http://localhost:8000/docs

### Local (SQLite)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
python -m app.create_admin admin@example.com "admin12345"
uvicorn app.main:app --reload
```

## Tests

```bash
pytest --cov=app
ruff check .
```

## Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Create a user |
| POST | `/auth/login` | No | Get a JWT |
| GET | `/auth/me` | User | Current user |
| GET | `/resources` | No | Active resources |
| POST | `/resources` | Admin | Create a resource |
| GET | `/resources/{id}/availability?date=YYYY-MM-DD` | No | Booked slots for a day (UTC) |
| POST | `/bookings` | User | Create a booking |
| GET | `/bookings/me?upcoming=true` | User | My bookings |
| GET | `/bookings/{id}` | Owner/Admin | Booking detail |
| POST | `/bookings/{id}/cancel` | Owner/Admin | Cancel a booking |
| GET | `/health` | No | Health check (includes DB) |

### Example

```bash
curl -X POST http://localhost:8000/bookings \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"resource_id": 1, "start_at": "2026-12-01T16:00:00-06:00", "end_at": "2026-12-01T17:00:00-06:00"}'
```

## Deployment (Render)

1. Push this repository to GitHub.
2. In Render: **New → Blueprint** and select the repo. `render.yaml` creates the web service and the database.
3. In the Render service settings, copy the **Deploy Hook** URL.
4. In GitHub: **Settings → Secrets and variables → Actions → New secret** named `RENDER_DEPLOY_HOOK_URL`.
5. Every push to `main` now runs the tests and, if they pass, deploys automatically.
6. Create the first admin from the Render **Shell**: `python -m app.create_admin you@example.com "password"`.

## Design decisions

- **Two layers against double bookings.** The application check gives a clear error message; the database constraint covers the race condition when two requests arrive at the same time.
- **Half-open intervals `[start, end)`**: a booking ending at 11:00 doesn't block one starting at 11:00.
- **Migrations instead of `create_all`**, so the production schema evolves safely and is versioned with the code.
- **Deploy only after CI passes**: Render's auto-deploy is off; GitHub Actions triggers it with a deploy hook.
- **12-factor config**: everything comes from environment variables; `postgres://` URLs from cloud providers are normalized automatically.
