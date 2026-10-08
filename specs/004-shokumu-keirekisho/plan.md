# Implementation Plan: 職務経歴書 Generator

**Branch**: `87-plan-shokumu` | **Date**: 2026-10-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-shokumu-keirekisho/spec.md`

## Summary

Produce a Japanese career history document from the Master Career Profile:
employer by employer, with periods, roles, descriptions and the achievements
the user recorded, opened by a 職務要約 assembled from countable facts and
closed by a 自己PR the user writes themselves.

The approach is deterministic throughout. No model is called, which the
clarification (#82) settled and which makes Principle IV hold by construction
rather than by verification. What feature 003 built — the embedded font, the
和暦/西暦 conversion, the paper sizes, the snapshot machinery — is shared rather
than rebuilt, and sharing it is also how FR-018 holds: two documents cannot
disagree about what 平成31年 means if one function writes both.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: FastAPI (pinned `>=0.115,<0.116`), SQLAlchemy 2.0,
reportlab, pypdf (tests)

**Storage**: PostgreSQL. No new table and no new column — one row written to
`entry_snapshot`, which feature 001 owns.

**Testing**: pytest. Document assertions extract text with pypdf rather than
comparing bytes.

**Target Platform**: Linux server; the document is streamed to a browser.

**Project Type**: Web application — FastAPI API, Next.js web app, both in the
existing monorepo.

**Performance Goals**: A document generated within one request, no worker
handoff. The 履歴書 renders in well under a second for a realistic profile and
this document is of the same order.

**Constraints**: Generation and snapshot capture share one transaction, so a
failed render leaves no record of a document nobody received. Nothing is
retained server-side.

**Scale/Scope**: One new API module, two routes, one web page. Roughly the size
of feature 003's User Story 1, less the font work.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Gate derived from the constitution | Pre-Phase 0 | Post-Phase 1 |
|---|---|---|---|
| G1 | **I.** The document derives from the profile; nothing is asked for twice | PASS | PASS — reads only existing entries; adds no field (data-model.md) |
| G2 | **I / FR-009 of 001.** One authored source language per entry; nothing translated | PASS | PASS — entries render as written; translation belongs to feature 005 |
| G3 | **IV / FR-010 of 001.** Every entry individually addressable | PASS | PASS — every section and achievement carries its `source_entry_id` |
| G4 | **IV / FR-028 of 001.** Generated claims stay traceable after their entries change | PASS | PASS — snapshot captured in the render's transaction (R-006) |
| G5 | **V / FR-006 of 001.** Sensitive Japan-specific fields withheld unless opted in | PASS | **PASS — by exclusion.** This document reads no `JapanProfile` field at all. A disclosure flag is consent for the 履歴書, not a standing permission |
| G6 | **V / FR-018 of 001.** Proposals invisible until accepted | Not applicable — creates no proposals | Not applicable |
| G7 | **§2.** Business logic in the API, not the web app | PASS | PASS — projection, summary assembly and ordering are API-side |
| G8 | **§2.** API types generated from OpenAPI | PASS | PASS — a fourth contract joins the existing generation |
| G9 | **§2.** Typed enumerations rather than free-text state | PASS | PASS — arrangement, date convention and paper size are enums |
| G10 | **§2.** Modular monolith; no new service | PASS | PASS |
| G11 | **§2 / workflow.** Schema changes ship with a migration | Not applicable — no schema change | Not applicable |
| G12 | **§2.** All model access behind the abstraction; no provider SDK in feature code | **Not applicable — this feature makes no model calls** | **Not applicable, and enforced.** The AST walker from feature 002 fails if anything under the new module imports a provider |
| G13 | **§2 quality gate.** Prompt or schema changes must state how Principle IV holds | Not applicable — no prompts | Not applicable |
| G14 | **§3.** Secrets not committed | PASS | PASS — no new configuration |
| G15 | **II / III.** Application event sourcing and next-action computation | Not applicable | Not applicable |

No gate fails. **Complexity Tracking is empty.**

One gate deserves a note rather than a tick. **G5 passes by exclusion**, which
is stronger than passing by filtering: the 履歴書 had to build a disclosure
filter because it may legitimately show those fields. This document never may,
so it reads none of them. A field that is never fetched cannot leak through a
later layout change.

## Project Structure

### Documentation (this feature)

```text
specs/004-shokumu-keirekisho/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── openapi.yaml     # Phase 1
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md             # Phase 2 — /speckit-tasks, not this command
```

### Source code

```text
apps/api/app/
├── documents/                  # NEW — shared by both document features
│   ├── fonts/                  # moved from rirekisho/fonts
│   ├── typography.py           # font registration, _Page, page sizes
│   └── snapshots.py            # thin wrapper over career.snapshots
├── rirekisho/                  # unchanged behaviour; imports from documents/
└── shokumu/                    # NEW
    ├── sections.py             # the projection: entries -> CareerHistory
    ├── summary.py              # 職務要約 from countable facts
    ├── render.py               # layout
    ├── readiness.py            # the readiness report
    ├── schemas.py              # request and report shapes
    ├── service.py              # generation + snapshot capture
    └── router.py

apps/api/tests/
├── contract/test_shokumu.py
├── integration/test_shokumu_*.py, test_document_agreement.py
└── unit/test_shokumu_sections.py, test_shokumu_summary.py

apps/web/
├── app/[locale]/profile/documents/shokumu-keirekisho/page.tsx
└── components/profile/shokumu-form.tsx
```

**Structure Decision**: a new `app/shokumu/` module beside `app/rirekisho/`,
with the machinery both need extracted into `app/documents/`. The extraction is
a refactor of working, tested code and is sequenced first, so the 履歴書 suite
is the safety net for it. The alternative — importing from `rirekisho/` — would
make one document feature depend on another's internals and leave no obvious
home for the third (feature 005).

## Phase 0 and Phase 1 outputs

| Artefact | Status |
|---|---|
| [research.md](./research.md) | 7 decisions, no unknowns remaining |
| [data-model.md](./data-model.md) | Reads 6 entities, writes 1 snapshot row, adds no column |
| [contracts/openapi.yaml](./contracts/openapi.yaml) | 2 routes, 8 schemas |
| [quickstart.md](./quickstart.md) | 11 scenarios |

## Consequences for existing code

Adding a contract is not inert. Three things follow, and all are part of the
first task rather than discoveries made later:

1. **`tests/contract/test_contracts.py`** discovers contracts by glob, so both
   new paths must be listed in `DEFERRED` until they are implemented, or the
   suite fails the moment this plan merges.
2. **`tests/contract/test_response_schemas.py`** iterates a hardcoded tuple of
   three features. A fourth contract would not be covered at all — the exact
   "silently stops checking" failure that file exists to prevent. It must gain
   the feature and name its unimplemented responses in `UNVALIDATED`.
3. **`packages/api-client`** globs the same contracts and will emit
   `schema-004.ts`. CI fails if the committed client is stale, so it is
   regenerated and committed with the plan.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No violations. This feature adds no service, no table, no column and no
abstraction the constitution does not already require. The one new shared
module is an extraction of existing code, not a new layer.
