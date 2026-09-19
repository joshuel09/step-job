# Quickstart: Master Career Profile

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/openapi.yaml](./contracts/openapi.yaml)

How to bring the stack up and prove the feature works, by walking the acceptance
scenarios from the specification. This is a validation guide: it describes what to
run and what to expect, not how anything is built.

## Prerequisites

- Docker and Docker Compose, for PostgreSQL and Redis
- Python 3.12 with `uv`, for the API and worker
- Node 22 with `pnpm`, for the web application

## Bring up the stack

```bash
# Backing services
docker compose up -d postgres redis

# API
cd apps/api
uv sync
uv run alembic upgrade head          # schema must be current before anything else
uv run uvicorn app.main:app --reload # http://localhost:8000

# Web
cd apps/web
pnpm install
pnpm gen:api                         # regenerate the typed client from openapi.yaml
pnpm dev                             # http://localhost:3000

# Worker — only needed for the purge scenario below
cd apps/worker
uv run dramatiq app.purge
```

`pnpm gen:api` regenerates `packages/api-client` from
[contracts/openapi.yaml](./contracts/openapi.yaml). Run it after any contract
change; the constitution requires API types be generated rather than hand-written,
so a hand-edited client is a defect.

## Health check

```bash
curl -s localhost:8000/api/v1/profile -H "Authorization: Bearer $TOKEN" | jq .
```

Expect `404` for a user with no profile yet, or the profile document. A `401`
means the session token is missing or unverified — see research.md R-006 for the
identity boundary.

Throughout, `$TOKEN` is a verified session from the web layer. No request carries
a user or profile identifier: every route operates on the caller's own profile.

---

## Scenario 1 — Record a career and have it survive (User Story 1, P1)

Proves SC-007 and the core of Principle I.

```bash
# Add a work experience
curl -s -X POST localhost:8000/api/v1/profile/experiences \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
        "employer_name": "Example Corp",
        "job_title": "Software Engineer",
        "employment_type": "permanent",
        "started_on": "2021-04-01",
        "ended_on": null,
        "description": "Built and maintained internal services.",
        "source_language": "en"
      }' | jq .
```

**Expect** `201` and an entry with a UUID `id`. A null `ended_on` is accepted and
means ongoing.

```bash
# Read it back in the full profile
curl -s localhost:8000/api/v1/profile -H "Authorization: Bearer $TOKEN" \
  | jq '.experiences[] | {id, employer_name, job_title, ended_on}'
```

**Expect** the entry exactly as submitted. Restart the API and repeat — values must
be unchanged.

### Rejected: an end date before the start date

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/api/v1/profile/experiences \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"employer_name":"Example Corp","job_title":"Engineer",
       "started_on":"2024-01-01","ended_on":"2023-01-01","source_language":"en"}'
```

**Expect** `422`, with a body naming `ended_on` and explaining why (FR-014). A
generic failure message is a defect — the interface must be able to show the
reason.

### Accepted: overlapping and concurrent roles

Post a second experience whose dates overlap the first. **Expect** `201` and no
warning. Concurrent roles are legitimate.

### Deleting tells you what depends on it

```bash
curl -s -X DELETE "localhost:8000/api/v1/profile/experiences/$EXPERIENCE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Expect** `409` and a body listing what references the entry (FR-013). Repeat with
`?confirm=true` to get `204`.

---

## Scenario 2 — Keep an accomplishment and find it later (User Story 2, P2)

Proves SC-006.

```bash
curl -s -X POST localhost:8000/api/v1/profile/stories \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
        "work_experience_id": "'"$EXPERIENCE_ID"'",
        "title": "Cut order processing errors",
        "challenge": "Manual steps caused frequent mistakes.",
        "action": "Reworked the update flow and added validation.",
        "result": "Operational errors fell substantially.",
        "source_language": "en"
      }' | jq .
```

**Expect** `201`. Then:

```bash
# The story appears alongside its experience
curl -s "localhost:8000/api/v1/profile/experiences/$EXPERIENCE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.stories | length'

# And is findable by keyword
curl -s "localhost:8000/api/v1/profile/stories?q=order" \
  -H "Authorization: Bearer $TOKEN" | jq 'length'
```

**Expect** at least `1` from both. Deleting the linked experience must warn that
stories reference it before proceeding.

---

## Scenario 3 — Nothing enters the profile unreviewed (User Story 3, P3)

Proves SC-004 and constitution gate G6.

```bash
# Submit a proposal that duplicates the experience from Scenario 1:
# same employer, overlapping dates, different job title wording
curl -s -X POST localhost:8000/api/v1/profile/proposals \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '[{
        "entry_type": "work_experience",
        "source": "manual-test-fixture",
        "payload": {
          "employer_name": "Example Corp.",
          "job_title": "Backend Engineer",
          "started_on": "2021-04-01",
          "source_language": "en"
        }
      }]' | jq '.[] | {id, status, possible_duplicate_of}'
```

**Expect** `201`, `status: "pending"`, and `possible_duplicate_of` set to the
Scenario 1 experience — the trailing `.` in the employer name must not prevent the
match, and the differing title must not prevent it either (FR-032, research.md
R-004).

**The critical check** — the proposal must be invisible to the profile:

```bash
curl -s localhost:8000/api/v1/profile -H "Authorization: Bearer $TOKEN" \
  | jq '[.experiences[] | select(.job_title == "Backend Engineer")] | length'
```

**Expect** `0`. Any other answer is a gate G6 failure, not a cosmetic bug.

```bash
# Accept with a correction: the corrected version is what enters the profile
curl -s -X POST "localhost:8000/api/v1/profile/proposals/$PROPOSAL_ID/accept" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"payload": {"job_title": "Senior Backend Engineer"}}' | jq .
```

**Expect** `201`, and the profile now holds `Senior Backend Engineer` — never the
uncorrected proposed title (FR-019). Accepting again must return `409`: accepted
and rejected are terminal.

### A promotion is not a duplicate

Propose a second role at the same employer whose dates do **not** overlap the
first. **Expect** `possible_duplicate_of: null` (FR-033).

---

## Scenario 4 — Traceability survives an edit

Proves FR-028 to FR-030 and constitution gate G4. This is the check most likely to
be quietly broken by a later change.

```bash
# Capture what a document drew on
curl -s -X POST localhost:8000/api/v1/profile/snapshots \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"document_ref":"quickstart-check","entry_ids":["'"$EXPERIENCE_ID"'"]}' \
  | jq '{id, captured_at}'

# Now change the underlying entry
curl -s -X PATCH "localhost:8000/api/v1/profile/experiences/$EXPERIENCE_ID" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"job_title":"Completely Different Title"}' > /dev/null

# The snapshot must still read as it did at capture time
curl -s "localhost:8000/api/v1/profile/snapshots/$SNAPSHOT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.payload'
```

**Expect** the original job title in the snapshot payload, and the new one in the
live entry. If the snapshot changed with the entry, traceability is broken and
Principle IV no longer holds.

---

## Scenario 5 — Deletion splits correctly

Proves FR-024 to FR-027 and SC-009.

```bash
# Given a Japan profile with visa details recorded
curl -s -X DELETE localhost:8000/api/v1/profile \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Expect** `200` and a receipt naming the immediately-erased fields and the
recovery deadline (FR-026).

```bash
# The profile is now invisible
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/v1/profile \
  -H "Authorization: Bearer $TOKEN"
```

**Expect** `404`, not a soft-deleted profile leaking through (FR-027).

```bash
# Restore inside the window
curl -s -X POST localhost:8000/api/v1/profile/restore \
  -H "Authorization: Bearer $TOKEN" | jq '.japan'
```

**Expect** `200`, the profile back, and `residence_status`, `nationality`,
`visa_type` and `visa_expires_on` all null. They were destroyed on the request
path and must not return (FR-024). Anything else is a compliance failure.

### The 30-day purge

With the worker running, set a test profile's `purge_after` to a past timestamp
and trigger the purge job. **Expect** the profile and everything below it —
including its snapshots (FR-031) — permanently gone. Running the job twice must be
a no-op, not an error.

---

## Scenario 6 — The interface works fully in both languages

Proves FR-021 to FR-023.

1. Open `http://localhost:3000/en/profile` and add an experience in English.
2. Switch the interface to Japanese. **Expect** the URL to move to `/ja/profile`,
   every label and validation message to render in Japanese with no untranslated
   text (FR-022), and the experience you typed to be **unchanged and untranslated**
   (FR-023).
3. Sign in from a second browser. **Expect** Japanese, because the setting is
   persisted server-side rather than in the first browser (research.md R-003).
4. Add an entry while in the Japanese interface, typing English prose. **Expect**
   it to save exactly as written, with `source_language` reflecting what you chose
   rather than the interface language.

---

## What "done" looks like

| Check | Proves |
|---|---|
| Scenarios 1–3 pass | The three user stories, independently |
| Scenario 4 passes | Principle IV traceability survives editing |
| Scenario 5 passes | Sensitive data erased immediately; remainder purged on time |
| Scenario 6 passes | Both interface languages, content untouched |
| `pnpm gen:api` produces no diff | The client matches the contract |
| `uv run pytest` and `pnpm test` green | Unit, contract and integration suites |

Contract tests run against [contracts/openapi.yaml](./contracts/openapi.yaml);
field-level rules they assert are defined in [data-model.md](./data-model.md).

---

## Walkthrough record

Run on 2026-09-19 against a fresh PostgreSQL and a locally started API
(T088). Scenarios 2 and 3 are covered by the automated suites rather than by
hand, since the stories they belong to are not yet built.

| Scenario | Result |
|---|---|
| 1 — Record a career and read it back | **Pass.** Experience created and returned unchanged; an end date before its start was rejected `422` with `ended_on: must be on or after started_on` |
| 4 — Traceability survives an edit | **Pass.** After editing the role, the live entry read `Completely Different Title` while the snapshot still read `Software Engineer` |
| 5 — Deletion splits correctly | **Pass.** Receipt named the four immediately-erased fields and a window 30 days out; profile returned `404` while deleted; restore returned everything except the erased fields |
| 5b — The 30-day purge | **Pass.** A backdated profile was found and erased; a second run erased nothing, confirming idempotency; every table was empty afterwards, confirming the cascade |
| 6 — Both interface languages | Covered by the Playwright suite in `apps/web/tests/e2e/locale-switch.spec.ts`; not run here, as it needs the web and API processes up together |
| Export | **Pass.** Archive contained `profile.json` and `profile.md` |

Scenarios 2 and 3 remain outstanding until User Stories 2 and 3 are built.
