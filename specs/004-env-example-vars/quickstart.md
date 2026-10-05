# Quickstart: Verify the .env.example settings

All commands run from `apps/api` unless noted.

## 1. The example matches the code defaults

```sh
uv run python - <<'EOF'
from app.core.settings import Settings
example = Settings(_env_file=".env.example")
defaults = Settings(_env_file=None)
for name in ("ai_provider", "openai_api_key", "web_origins"):
    assert getattr(example, name) == getattr(defaults, name), name
    print(f"{name}: {getattr(example, name)!r} OK")
EOF
```

Expected: three `OK` lines. Run it with no `AI_PROVIDER`, `OPENAI_API_KEY` or
`WEB_ORIGINS` exported in the shell, because real environment variables override
both.

## 2. Every ticket variable is present and commented

```sh
grep -nB2 -E '^(AI_PROVIDER|OPENAI_API_KEY|WEB_ORIGINS)=' .env.example
```

Expected: each variable has at least one `#` comment line directly above it.

## 3. No secrets

```sh
grep -E '^OPENAI_API_KEY=.+' .env.example && echo "FAIL: key has a value" || echo OK
```

## 4. Fresh clone runs the API against the web app

```sh
cp .env.example .env
docker compose up -d          # from the repo root: Postgres and Redis
uv run alembic upgrade head
uv run uvicorn app.main:app --port 8000
# in another terminal, from apps/web:
pnpm dev                      # serves http://localhost:3000
```

Open `http://localhost:3000` and use a page that calls the API. Expected: no
CORS errors in the browser console. Any AI-backed action returns the fake
provider's output and makes no network call.
