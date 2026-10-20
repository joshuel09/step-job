# step-job
AI-powered career management platform for job seekers in Japan — create resumes, manage applications and recruiters, track interviews, discover jobs, and prepare for interviews.

## Working method

Features get specs, chores get issues: the spec-driven cycle in `specs/` is for work with user-visible behaviour and open questions worth settling before code, while a chore — a config default, a dependency bump, a rename — goes straight from its issue to a pull request.

## Running it locally

What works today: the API, end to end, and the web app with a development session in place of sign-in (#119). Sign-in itself is not built yet.

You need Docker, [uv](https://docs.astral.sh/uv/), Python 3.12+ and Node 22. pnpm comes through corepack, so `corepack pnpm` works where `pnpm` is not on your PATH.

### 1. Check two ports first

| Port | Used by | If it is taken |
|---|---|---|
| 5432 | Postgres | Set `POSTGRES_PORT` (e.g. `5433`), and use the same port in `DATABASE_URL` |
| 3000 | Web app | Run the web app on another port, and add that origin to `WEB_ORIGINS` |

Both fail quietly. With another Postgres already on 5432, the API's default `DATABASE_URL` connects to **that** database instead of this project's. With the web app on a port `WEB_ORIGINS` does not list, the browser blocks every API call on CORS.

### 2. Start Postgres and Redis

```sh
cp apps/api/.env.example apps/api/.env      # edit the ports here if step 1 said so
POSTGRES_PORT=5432 docker compose up -d     # same port as in apps/api/.env
```

Redis is only needed by the worker.

### 3. Run the API

Migrations are not run for you.

```sh
uv sync --all-extras
cd apps/api
uv run alembic upgrade head                 # reads DATABASE_URL from apps/api/.env
uv run uvicorn app.main:app --reload --port 8000
```

The API reads `apps/api/.env` from the directory it is started in, so run it from `apps/api`. Without a web app, call it with any UUID as the bearer token:

```sh
curl -X POST localhost:8000/api/v1/profile -H "Authorization: Bearer $(uuidgen)"
```

### 4. Run the web app

```sh
cp apps/web/.env.example apps/web/.env.local   # sets NEXT_PUBLIC_DEV_SESSION=1
corepack pnpm install
corepack pnpm dev                              # http://localhost:3000
```

On another port: `corepack pnpm --filter web dev -p 3001`, with `WEB_ORIGINS=http://localhost:3001` in `apps/api/.env` and the API restarted.

`NEXT_PUBLIC_DEV_SESSION=1` gives each browser a random user id in a cookie. Without it every API call is a 401. It is for local development only: whoever holds the cookie is that user.

### 5. The worker (optional)

Slow imports and the deletion purge run here. Everything else works without it.

The worker uses the API's database code, but reads `.env` from `apps/worker`. If you moved Postgres off 5432, copy `apps/api/.env` there too, or it connects to the default port.

```sh
cd apps/worker
uv run dramatiq worker.main       # the actors
uv run python -m worker.main      # the scheduler, in a second terminal
```

### Tests

```sh
# API, from apps/api. Creates stepjob_test on first run. The live tests call a
# real model provider and need a key, so leave them out.
TEST_DATABASE_URL=postgresql+psycopg://stepjob:stepjob@localhost:5432/stepjob_test \
  uv run pytest -m "not live"

# Worker, from apps/worker
TEST_DATABASE_URL=postgresql+psycopg://stepjob:stepjob@localhost:5432/stepjob_worker_test \
  uv run pytest

# Web
corepack pnpm --filter web test
```

Change `5432` in those URLs if you moved Postgres in step 1. `ruff check .` from `apps/api` and `corepack pnpm --filter web build` are what CI runs on top of the tests.
