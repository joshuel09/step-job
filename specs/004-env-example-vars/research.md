# Research: Document the missing API settings in .env.example

## R-001: Which settings to add

**Decision**: Only the three named in #58: `AI_PROVIDER`, `OPENAI_API_KEY` and
`WEB_ORIGINS`.

**Rationale**: These are the ones a fresh clone has to know about to run the API
against the web app, or to switch to a real provider. If `WEB_ORIGINS` is wrong,
the browser refuses the API. The other `Settings` fields (`AI_MODEL`,
`REDIS_URL`, `IMPORT_DEADLINE_SECONDS`, `AI_MAX_RETRIES`,
`DELETION_RECOVERY_DAYS`) have working local defaults, and `settings.py` says
some exist only so tests can adjust them. `DELETION_RECOVERY_DAYS` is fixed by
FR-025 of feature 001 and deliberately not meant to be tuned per deployment.
Listing it in a file people copy and edit would invite exactly that.

**Alternatives considered**: Listing every field. Rejected as outside the
ticket's scope, and because it would advertise settings that are not meant to
be changed.

## R-002: Values and comment wording

**Decision**:

- `AI_PROVIDER=fake`. The comment names the accepted values (`fake`, `openai`,
  from `get_provider()`) and says `fake` keeps local work and CI off the network.
- `OPENAI_API_KEY=` (empty). The comment says it is only read when
  `AI_PROVIDER=openai`.
- `WEB_ORIGINS=http://localhost:3000`. The comment says what it is for, that a
  wrong value means the browser is refused, and that it takes comma-separated
  addresses (`main.py` splits on `,` and trims whitespace).

Comments go above each variable as `#` lines, matching the existing
`POSTGRES_PORT` block. The AI pair is grouped together.

**Rationale**: Each value matches its code default, so copying the file changes
nothing (FR-008). The wording follows the ticket's table and the existing
comments in `settings.py`.

**Alternatives considered**: Setting `AI_PROVIDER=openai` with a placeholder
key. Rejected: that breaks offline-by-default and invites committing a key.

## R-003: Verification

**Decision**: Static verification, recorded in the PR body. Load the example
through `Settings(_env_file=...)` and compare each value with a `Settings()`
built with no env file. Then confirm by hand that the web app reaches the API
with the copied file.

**Rationale**: The constitution lets a PR record the static verification it
actually performed when no suite covers the change. A permanent test that the
example matches the code defaults would be useful, but it goes beyond the
ticket. It is noted as a possible follow-up, not added here.

**Alternatives considered**: A unit test asserting every `Settings` field
appears in `.env.example`. Rejected for now: it conflicts with R-001's decision
to leave some fields out.
