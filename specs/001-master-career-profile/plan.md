# Implementation Plan: Master Career Profile

**Branch**: `9-plan-career-profile` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-master-career-profile/spec.md`

## Summary

Build the canonical career record every generated document derives from: typed
profile sections a user maintains directly, career stories linked to the roles
they happened in, and a review queue where entries proposed by an outside source
wait until the user accepts them. The profile is served by the API as the single
source of business logic, persisted in PostgreSQL, and rendered server-first by
the web application in either English or Japanese.

Three design decisions shape the work. Entries stay directly editable with no
revision history, and traceability is preserved instead by immutable snapshots
taken whenever a document is generated. Profile deletion splits into an immediate
hard delete of residence, nationality and visa data and a 30-day soft-deleted
recovery window for everything else, purged by a scheduled job. Duplicate
detection compares employer and overlapping dates only, so two sources describing
one role match while a promotion or a re-hire stays distinct.

This is the first feature in the repository, so the structure below establishes
the monorepo layout that later features extend.

## Technical Context

**Language/Version**: Python 3.12 (API, worker), TypeScript 5.x on Node 22 (web)

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy, Alembic (API);
Dramatiq with Redis (worker); Next.js App Router, React, Tailwind CSS,
shadcn/ui, TanStack Query, React Hook Form, Zod, next-intl (web)

**Storage**: PostgreSQL. No pgvector usage in this feature — embeddings arrive
with the features that search career stories. Object storage is not required
here, because exports are generated on request and streamed rather than retained
(research.md R-005).

**Testing**: pytest for API and worker, including contract tests generated
against the OpenAPI document; Vitest for web unit tests; Playwright for the
acceptance journeys in quickstart.md

**Target Platform**: Linux server for API and worker; modern evergreen browsers
for web, usable at phone width

**Project Type**: Web application — Next.js frontend, FastAPI backend, shared
background worker, in a modular monolith

**Performance Goals**: profile read and section save complete fast enough that
SC-001 holds — a user with their details to hand records a usable profile in under
15 minutes, with no individual save perceptibly delaying them. Export generation
for a profile of the expected size completes within the one-minute bound in
SC-008.

**Constraints**: interface fully usable in English and Japanese with no
untranslated text (FR-022); soft-deleted profiles unreadable by every other
feature (FR-027); sensitive Japan-specific fields withheld from generated
documents by default (FR-006)

**Scale/Scope**: single-user profiles holding dozens of entries across sections,
not thousands (spec Assumptions). Roughly 12 persisted entities, one REST
resource tree, and the profile section of the web application.

All Technical Context values are decided. The constitution fixes the stack and
architecture; the six questions this feature left open are resolved in
[research.md](./research.md). Nothing in Technical Context is left unresolved.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Gate derived from the constitution | Pre-Phase 0 | Post-Phase 1 |
|---|---|---|---|
| G1 | **I.** No feature asks for data the profile already holds; the profile is the only career source | PASS | PASS |
| G2 | **I / FR-009.** Each entry carries one user-authored source language; other languages are generated, never a second editable source | PASS | PASS — `source_language` on every content-bearing entity |
| G3 | **IV / FR-010.** Every entry is individually addressable, so any generated claim can be traced to what supports it | PASS | PASS — stable UUID primary keys; snapshots record entry ids alongside captured content |
| G4 | **IV.** Traceability survives editing of the source entry | PASS | PASS — immutable snapshots (research.md R-001) |
| G5 | **V / FR-006.** Sensitive Japan-specific fields are withheld from generated documents unless opted in, defaulting closed at the data layer rather than only in the interface | PASS | PASS — disclosure flags default false in schema |
| G6 | **V / FR-018.** Proposed entries are invisible to every profile reader until accepted | PASS | PASS — separate table, never joined into profile reads |
| G7 | **§2.** Business logic lives in the API; the web app does not reimplement domain rules | PASS | PASS — validation, duplicate detection and deletion rules are API-side |
| G8 | **§2.** API types are generated from the OpenAPI document, not hand-maintained twice | PASS | PASS — [contracts/openapi.yaml](./contracts/openapi.yaml) is the source |
| G9 | **§2.** Typed enumerations rather than free-text strings for state | PASS | PASS — proposal status and language proficiency are enums |
| G10 | **§2.** Modular monolith; no new service, no dedicated vector database | PASS | PASS |
| G11 | **§2 / workflow.** Schema changes ship with an Alembic migration | PASS | PASS — carried as a task gate |
| G12 | **§2.** All model access goes through the `AIProvider` abstraction; no provider SDK in feature code | PASS — this feature makes no AI calls | PASS — extraction belongs to the separate import feature |
| G13 | **II / III.** Application event sourcing and next-action computation | Not applicable — this feature holds no applications | Not applicable |

No gate fails, before or after design. **Complexity Tracking is empty**: this
feature introduces no deviation requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/001-master-career-profile/
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

This feature establishes the monorepo. Paths marked *new* are created by this
feature's tasks; the worker application is scaffolded but exercises only the
purge job.

```text
apps/
├── api/                              # FastAPI — single source of business logic
│   ├── app/
│   │   ├── main.py                   # new — application entrypoint
│   │   ├── core/                     # new — settings, identity dependency, errors
│   │   ├── db/                       # new — session, base model, soft-delete filter
│   │   ├── career/                   # new — this feature
│   │   │   ├── models.py             # SQLAlchemy entities from data-model.md
│   │   │   ├── schemas.py            # Pydantic request/response models
│   │   │   ├── router.py             # /profile resource tree
│   │   │   ├── service.py            # profile, story and proposal rules
│   │   │   ├── duplicates.py         # employer + date-overlap matching (R-004)
│   │   │   ├── snapshots.py          # immutable capture (R-001)
│   │   │   ├── deletion.py           # split hard/soft delete (R-002)
│   │   │   └── export.py             # structured file + readable document (R-005)
│   │   └── i18n/                     # new — API-side message catalogue
│   ├── migrations/                   # new — Alembic
│   └── tests/
│       ├── contract/                 # new — generated against openapi.yaml
│       ├── integration/              # new — acceptance scenarios
│       └── unit/                     # new — duplicate matching, validation
│
├── web/                              # Next.js App Router — server-first
│   ├── app/
│   │   ├── [locale]/                 # new — en | ja segment (R-003)
│   │   │   └── profile/              # new — profile sections, stories, review queue
│   │   └── layout.tsx                # new
│   ├── components/                   # new — profile forms and section views
│   ├── lib/                          # new — generated API client, locale resolution
│   ├── messages/                     # new — en.json, ja.json
│   └── tests/                        # new — Vitest, Playwright
│
└── worker/                           # Dramatiq — scheduled work
    ├── app/
    │   └── purge.py                  # new — 30-day profile purge (R-002)
    └── tests/                        # new

packages/
├── api-client/                       # new — TypeScript client generated from openapi.yaml
├── config/                           # new — shared lint, tsconfig, formatting
└── ui/                               # deferred — no shared components until a second app needs them

docker-compose.yml                    # new — PostgreSQL and Redis for local development
```

**Structure Decision**: the constitution's modular monolith, realised as a
monorepo with three applications under `apps/` and shared packages under
`packages/`. The API owns all business logic, so `apps/api/app/career/` holds the
rules and the web application consumes them through a generated client — which is
what keeps gates G7 and G8 true rather than aspirational. The career module is
split by concern rather than by layer, so that duplicate detection, snapshots,
deletion and export each stay independently testable, matching how the
clarifications defined them. `apps/worker` exists because R-002 requires a
scheduled purge; it shares the API's models rather than duplicating them, per the
constitution's instruction not to duplicate logic between API and worker.
`packages/ui` is deliberately left unpopulated until a second application needs a
shared component.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Every gate passes before and after design, and this feature
introduces no additional projects, indirection or patterns beyond what the
constitution already prescribes.
