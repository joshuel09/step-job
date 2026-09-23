# Quickstart: AI Resume Import

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/openapi.yaml](./contracts/openapi.yaml)

How to bring the stack up and prove this feature works. A validation guide: what
to run and what to expect, not how anything is built.

## Prerequisites

Everything from [feature 001's quickstart](../001-master-career-profile/quickstart.md),
plus one thing.

```bash
# In apps/api/.env — only needed for the live smoke test at the end.
# Every automated test uses the fake provider and never reaches the network.
AI_PROVIDER=fake          # fake | openai
OPENAI_API_KEY=           # leave empty unless running the live check
```

`AI_PROVIDER=fake` is the default for local work and for continuous integration.
A test whose outcome depends on a model's mood is not a test.

## Bring up the stack

```bash
docker compose up -d postgres redis

cd apps/api
uv run alembic upgrade head          # adds the import table and the proposal columns
uv run uvicorn app.main:app --reload

cd apps/worker
uv run dramatiq worker.main          # needed only for the handoff scenario

cd apps/web
pnpm gen:api                         # regenerates clients for BOTH contracts
pnpm dev
```

`pnpm gen:api` now produces one typed module per contract file. If it produces a
diff, commit it — continuous integration fails on a stale client.

Throughout, `$TOKEN` is a verified session and `$A=localhost:8000/api/v1`.

---

## Scenario 1 — Paste a career and get proposals with evidence (User Story 1, P1)

Proves the core of the feature and SC-002.

```bash
curl -s -X POST $A/profile/imports \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"text": "Software Engineer, Example Corp (Apr 2021 - Mar 2024). Built and maintained internal services. Skills: Ruby, PostgreSQL."}' | jq .
```

**Expect** `201`, and a `status` of `completed` for text this short.

```bash
curl -s "$A/profile/proposals" -H "Authorization: Bearer $TOKEN" \
  | jq '.[0] | {entry_type, source, payload, evidence}'
```

**Expect** a work experience proposal whose `evidence` names each populated field
and quotes the passage it came from. The quote must be text that appears in what
you pasted.

**The critical check** — proposals must not reach the profile:

```bash
curl -s $A/profile -H "Authorization: Bearer $TOKEN" | jq '.experiences | length'
```

**Expect** `0`. Anything else is a gate G6 failure, not a cosmetic bug.

---

## Scenario 2 — A fabricated field never becomes a proposal

Proves R-001 and SC-003. **This is the scenario that makes Principle IV real**,
and the one most likely to be quietly broken by a later change.

Run with the fake provider scripted to return a field whose quote does not appear
in the source — the behaviour of a model that has invented something:

```bash
cd apps/api
uv run pytest tests/unit/test_evidence.py -v
uv run pytest tests/integration/test_extraction_truthfulness.py -v
```

**Expect** every case to pass, and specifically:

- A field whose quote appears in the source → proposed, with evidence.
- A field whose quote does **not** appear → **dropped**. Not proposed with a
  warning, not proposed unverified. Absent.
- A field the model returned with no quote at all → dropped.
- A quote differing from the source only in whitespace or line breaks → accepted,
  because extracted document text routinely differs that way.
- A quote that is a near-miss but not present → dropped. There is no fuzzy
  matching; that would reopen the gap this closes.

If a field ever reaches a proposal without a verified quote, the guarantee in
SC-003 is gone and no amount of prompt wording restores it.

---

## Scenario 3 — Import a PDF, and confirm the file is not kept (User Story 2, P2)

```bash
curl -s -X POST $A/profile/imports/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@tests/fixtures/example-resume.pdf" | jq '{id, source_kind, status}'
```

**Expect** `201` and proposals created from the document's contents.

```bash
# Nothing should have been written anywhere
find /tmp /var/tmp -name '*example-resume*' 2>/dev/null
docker compose exec -T postgres psql -U stepjob -d stepjob \
  -c "SELECT count(*) FROM import WHERE outcome::text LIKE '%example-resume%';"
```

**Expect** no files and a count of `0`. The bytes were read into memory and
released; nothing persisted them, which is why FR-004 needs no cleanup step.

### A scanned PDF with no text layer

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST $A/profile/imports/upload \
  -H "Authorization: Bearer $TOKEN" -F "file=@tests/fixtures/scanned-no-text.pdf"
```

**Expect** the import to reach `failed` with `failure_reason: unreadable_document`
— not `service_unavailable`. The user needs to know their document is the
problem, because trying again will never help.

---

## Scenario 4 — A slow import hands off and still lands (FR-005a to FR-005c)

With the worker running, and the in-request deadline lowered so the handoff can
be forced:

```bash
IMPORT_DEADLINE_SECONDS=0.1 uv run uvicorn app.main:app &

ID=$(curl -s -X POST $A/profile/imports -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"text": "..."}' | jq -r .id)

curl -s "$A/profile/imports/$ID" -H "Authorization: Bearer $TOKEN" | jq .status
```

**Expect** `running` immediately, then `completed` on a later poll. The proposals
must be identical to those Scenario 1 produced in the request — being slow
changes nothing about what is produced.

**Then kill the client mid-import and poll again.** The outcome must still be
waiting. An import that depends on the user staying on the page fails SC-007a.

---

## Scenario 5 — A self-contradictory document is flagged, not fixed (FR-012a)

```bash
curl -s -X POST $A/profile/imports \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"text": "Engineer, Example Corp. March 2024 to January 2021."}' > /dev/null

curl -s "$A/profile/proposals" -H "Authorization: Bearer $TOKEN" | jq '.[0].conflicts'
```

**Expect** a conflict naming `started_on` and `ended_on`, and the dates proposed
**as the document states them** — not silently swapped into a sensible order.
Correcting them is the user's call; the system does not know which is wrong, and
guessing would be deciding what someone's career was.

---

## Scenario 6 — The service being down is said plainly (FR-017a to FR-017d)

With the fake provider scripted to be unavailable:

```bash
AI_PROVIDER=fake FAKE_AI_BEHAVIOUR=unavailable uv run pytest \
  tests/integration/test_import_failures.py -v
```

**Expect**: a bounded number of retries, then `failed` with
`failure_reason: service_unavailable` — distinguishable from
`unreadable_document`, because one is worth trying again and the other never
will be. And **no proposals created**, and no partial set.

---

## Scenario 7 — Evidence is discarded at review (FR-015a, FR-015b)

```bash
PROPOSAL=$(curl -s "$A/profile/proposals" -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')

curl -s "$A/profile/proposals" -H "Authorization: Bearer $TOKEN" | jq '.[0].evidence != null'
# expect true — evidence is present while the decision is pending

curl -s -X POST "$A/profile/proposals/$PROPOSAL/accept" -H "Authorization: Bearer $TOKEN" > /dev/null

curl -s "$A/profile/proposals?status=accepted" -H "Authorization: Bearer $TOKEN" \
  | jq '.[0].evidence'
```

**Expect** `null`. The evidence did its job — it let the user judge the value —
and holding resume fragments afterwards serves no remaining purpose. Confirm the
accepted entry itself is unchanged.

---

## Scenario 8 — Japanese era dates convert, with the original visible (FR-011)

```bash
curl -s -X POST $A/profile/imports \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"text": "エンジニア、サンプル株式会社。令和3年4月から令和6年3月まで。"}' > /dev/null

curl -s "$A/profile/proposals" -H "Authorization: Bearer $TOKEN" \
  | jq '.[0] | {started: .payload.started_on, evidence: .evidence.started_on.quote, lang: .payload.source_language}'
```

**Expect** `started_on` of `2021-04-01`, evidence quoting `令和3年4月`, and a
source language of `ja`. The user sees the document's own words beside the
converted date, so they can confirm the conversion rather than trust it. Nothing
is translated.

---

## The live check (optional, never in continuous integration)

One smoke test against a real provider, skipped unless a key is present:

```bash
AI_PROVIDER=openai OPENAI_API_KEY=... uv run pytest -m live -v
```

**Expect** it to extract a real fixture and, critically, for every proposed field
to carry verified evidence. If the real model fabricates, the verifier drops the
field — that is the system working, not failing.

---

## What "done" looks like

| Check | Proves |
|---|---|
| Scenario 1 | Extraction produces proposals with evidence, and reaches no profile |
| **Scenario 2** | **A fabricated field cannot become a proposal — Principle IV** |
| Scenario 3 | Files are read and released; unreadable documents say so |
| Scenario 4 | A slow import hands off and still lands |
| Scenario 5 | Contradictions are flagged, never resolved |
| Scenario 6 | Service failure is distinguishable and leaves nothing behind |
| Scenario 7 | Evidence discarded at review; accepted entry unchanged |
| Scenario 8 | Era dates converted, original kept as evidence |
| `pnpm gen:api` produces no diff | Both clients match their contracts |
| `uv run pytest` and `pnpm test` green | The suites, with no network access |

Field-level rules these assert are defined in [data-model.md](./data-model.md);
the routes in [contracts/openapi.yaml](./contracts/openapi.yaml).
