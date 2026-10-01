# Implementation Plan: 履歴書 Generator

**Branch**: `47-plan-rirekisho` | **Date**: 2026-10-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-rirekisho-generator/spec.md`

## Summary

Produce a Japanese 履歴書 from the career profile, laid out as employers expect,
with every line traceable to an entry and nothing invented to fill a
conventional blank.

The feature is deterministic end to end. The 学歴・職歴 table is a pure function
from the profile's education and work entries to an ordered list of rows; the
dates are arithmetic; the layout is drawn directly. No model is involved
anywhere, which is a decision rather than an omission — FR-014b's offer to
suggest a Japanese translation is resolved out of scope (research.md R-001),
because a translation cannot be evidence-checked the way an extraction can and
would amount to shipping unverified AI output into a document the user signs.

Two things make this the first feature of its kind. It is the first consumer of
the snapshot machinery feature 001 built and nothing has used, and the first
real exercise of the disclosure defaults that have protected Japan-specific
fields since the profile was specified. Both become testable here.

It also changes feature 001: the profile gains a date of birth and an address,
and the form a user types them into changes with it.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript 5.x on Node 22 (web)

**Primary Dependencies**: existing stack, plus the PDF library already present
for feature 002's fixtures, promoted to a runtime dependency, and one
open-licensed Japanese font shipped with the application

**Storage**: PostgreSQL. **No new tables.** Two optional columns are added to
feature 001's identity record; the generation record is the existing snapshot
(research.md R-003). Generated documents are not retained (FR-005).

**Testing**: pytest, asserting on text extracted back out of generated PDFs
rather than on bytes — which is also what catches a missing CJK font; Vitest and
Playwright on the web side

**Target Platform**: Linux server for the API; evergreen browsers for the web

**Project Type**: Web application in the existing modular monolith

**Performance Goals**: SC-001 requires a document within a minute of asking.
Generation is in-request: it is layout, not extraction, so there is no handoff.

**Constraints**: no statement may appear that the profile does not support
(SC-002, SC-003); no Japan-specific field may appear undisclosed (SC-005); no
entry may be dropped to fit a page (SC-007a); one date convention per document
(SC-007)

**Scale/Scope**: one document per request, from a profile holding dozens of
entries. Two pages conventionally, more where the history requires it.

All Technical Context values are decided. The six questions this feature left
open are resolved in [research.md](./research.md). Nothing is left unresolved.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Gate derived from the constitution | Pre-Phase 0 | Post-Phase 1 |
|---|---|---|---|
| G1 | **I.** The document derives from the profile; nothing is asked for twice | PASS | PASS — the two fields a 履歴書 needs are added to the profile, not collected per document (R-004) |
| G2 | **I / FR-009 of 001.** One authored source language per entry; nothing translated | PASS | PASS — entries render as written; the translation offer is out of scope (R-001) |
| G3 | **IV / FR-010 of 001.** Every entry individually addressable | PASS | PASS — rows carry the id of the entry that produced them |
| G4 | **IV / FR-028 of 001.** Generated claims stay traceable after their entries change | PASS | **PASS — first real use.** Generation captures a snapshot in the same transaction as the render (R-003) |
| G5 | **V / FR-006 of 001.** Sensitive Japan-specific fields withheld unless opted in | PASS | **PASS — first real exercise.** A flag's effect is now observable in a produced document, and tested per flag against extracted PDF text |
| G6 | **V / FR-018 of 001.** Proposals invisible until accepted | Not applicable — this feature creates no proposals | Not applicable |
| G7 | **§2.** Business logic in the API, not the web app | PASS | PASS — the projection, the date rendering and the disclosure filter are API-side |
| G8 | **§2.** API types generated from OpenAPI | PASS | PASS — a third contract joins the generation the second one established |
| G9 | **§2.** Typed enumerations rather than free-text state | PASS | PASS — date convention and paper size are enums |
| G10 | **§2.** Modular monolith; no new service | PASS | PASS |
| G11 | **§2 / workflow.** Schema changes ship with a migration | PASS | PASS — one revision, for feature 001's two columns |
| G12 | **§2.** All model access behind the abstraction; no provider SDK in feature code | **Not applicable — this feature makes no model calls** | **Not applicable, and enforced.** The AST walker added in feature 002 fails if anything under `app/rirekisho/` imports a provider, so this holds by test rather than by assertion |
| G13 | **§2 quality gate.** Prompt or schema changes must state how Principle IV holds | Not applicable — no prompts | Not applicable |
| G14 | **§3.** Secrets not committed | PASS | PASS — no new configuration |
| G15 | **II / III.** Application event sourcing and next-action computation | Not applicable | Not applicable |

No gate fails. **Complexity Tracking is empty.**

Two gates change character here. G12 has been "not applicable" for two features
by accident of scope; it is not applicable here by decision, and the decision is
enforced by a test that already exists. G5 has been satisfied by schema defaults
since feature 001 — a flag defaulting false in a table nothing read. This is the
first feature that reads it, so it is the first place the flag can be observed
to work, and the first place it could be got wrong.

## Project Structure

### Documentation (this feature)

```text
specs/003-rirekisho-generator/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── openapi.yaml
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

Paths marked *new* are created by this feature. Paths marked *changed* belong to
earlier features and are modified here — named so they are built deliberately
rather than discovered.

```text
apps/
├── api/app/
│   ├── rirekisho/                 # new — this feature. Imports nothing from app.ai,
│   │   │                          #       which test_ai_boundary.py enforces.
│   │   ├── rows.py                # the 学歴・職歴 projection: entries in, ordered rows out (R-006)
│   │   ├── render.py              # drawing the form; the only module that knows about PDFs
│   │   ├── fonts/                 # one open-licensed Japanese font, with its licence
│   │   ├── disclosure.py          # which Japan-specific fields may appear (gate G5)
│   │   ├── readiness.py           # what is missing, and which entries lack Japanese (R-001)
│   │   ├── service.py             # orchestration, and the snapshot capture (R-003)
│   │   ├── schemas.py             # request and response models
│   │   └── router.py              # /profile/documents/rirekisho
│   │
│   ├── imports/dates.py           # changed — gains era rendering beside era parsing (R-005)
│   └── career/
│       ├── models.py              # changed — Identity gains date of birth and address
│       └── schemas.py             # changed — the same two fields
│
├── api/migrations/versions/       # new revision — feature 001's two columns
├── api/tests/{unit,integration,contract}/   # new — rows, disclosure, dates, the document
│
└── web/
    ├── app/[locale]/profile/documents/rirekisho/   # new — choose conventions, preview, download
    ├── components/profile/
    │   ├── rirekisho-form.tsx     # new
    │   ├── rirekisho-readiness.tsx # new — what is missing, and what has no Japanese
    │   └── identity-form.tsx      # changed — the two new fields
    └── messages/                  # changed — strings for both languages

specs/001-master-career-profile/contracts/openapi.yaml   # changed — the two fields
packages/api-client/src/schema-003.ts                    # new — generated
```

**Structure Decision**: the projection, the rendering and the disclosure filter
are separate modules because they fail in different ways and are tested
differently. `rows.py` is a pure function and can be tested exhaustively without
producing a document; `render.py` is the only place that knows a PDF exists, so
a font or layout problem is localised; `disclosure.py` is small and single-
purpose because getting it wrong means publishing someone's visa status, and
that deserves a module whose entire contents can be read in one go.

`fonts/` is in the application rather than fetched at build time because a
missing font fails silently — the document is produced and unreadable — and a
build-time dependency is one more thing that can be unavailable when it matters.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. This feature adds no new service, no new persisted table, and no
abstraction the constitution does not already require.
