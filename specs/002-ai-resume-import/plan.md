# Implementation Plan: AI Resume Import

**Branch**: `29-plan-resume-import` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-ai-resume-import/spec.md`

## Summary

Read a PDF, a DOCX or pasted text, extract structured career information from it,
and deliver that into the review queue feature 001 already provides. Nothing this
feature produces reaches a profile except by the user accepting it.

The design turns on one decision. Principle IV forbids AI inventing professional
experience, and a prompt cannot enforce that. So the model must return, for every
field it fills, the passage of source text it took the value from, and
deterministic code verifies that passage genuinely appears in the source before
anything becomes a proposal. A field whose evidence does not verify is dropped.
The verifier is the enforcement; the prompt is not (research.md R-001).

Two consequences shape the rest. Extraction runs in the request where it can and
hands off to the existing worker where it cannot, so a long document does not
become a request that never returns. And the uploaded document is never written
anywhere — bytes are read, text is extracted, bytes are released — which makes
"the document is not retained" structural rather than a cleanup step.

This feature modifies feature 001: proposed entries gain evidence and conflict
columns, and accepting or rejecting one must discard its evidence.

## Technical Context

**Language/Version**: Python 3.12 (API, worker), TypeScript 5.x on Node 22 (web)

**Primary Dependencies**: existing stack, plus deterministic document text
extraction for PDF and DOCX, and one model provider client used solely behind the
`AIProvider` abstraction

**Storage**: PostgreSQL. Two structured columns and an import reference added to
the existing `proposed_entry` table; one new `import` table. No object storage —
uploaded documents are never persisted (research.md R-005).

**Testing**: pytest with a fake provider for every automated test; one live smoke
test skipped unless a provider key is present, so continuous integration never
calls a real model. Vitest and Playwright on the web side.

**Target Platform**: Linux server for API and worker; evergreen browsers for web

**Project Type**: Web application in a modular monolith, extending the existing
monorepo

**Performance Goals**: SC-001 requires a reviewable set of proposals within two
minutes of starting an import. Imports that would exceed the in-request deadline
hand off rather than block.

**Constraints**: no proposed field may contain anything absent from the source
(SC-003); uploaded documents never written to disk (FR-004); evidence discarded
at review (FR-015a); a failed import leaves nothing behind (FR-017d)

**Scale/Scope**: ordinary resume length — a handful of pages. One import at a
time per user is the expected pattern, though concurrent imports are permitted.

All Technical Context values are decided. The seven questions this feature left
open are resolved in [research.md](./research.md). Nothing is left unresolved.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Gate derived from the constitution | Pre-Phase 0 | Post-Phase 1 |
|---|---|---|---|
| G1 | **I.** Extraction feeds the Master Career Profile rather than creating a parallel store | PASS | PASS |
| G2 | **I / FR-009 of 001.** Each entry carries one authored source language; nothing is translated on import | PASS | PASS — language detected per entry, no translation step exists |
| G3 | **IV / FR-010 of 001.** Every entry individually addressable | PASS | PASS — proposals become ordinary entries with UUID keys |
| G4 | **IV.** AI may improve presentation but never invent experience | PASS | **PASS — enforced, not instructed.** The model must quote its source; deterministic code verifies the quote appears in the document; unverifiable fields are dropped (R-001) |
| G5 | **V / FR-006 of 001.** Sensitive Japan-specific fields withheld from generated documents by default | PASS | PASS — extracted values enter as proposals and inherit the existing closed defaults on acceptance |
| G6 | **V / FR-018 of 001.** Proposals invisible to every profile reader until accepted | PASS | PASS — this feature writes only to the proposal table |
| G7 | **§2.** Business logic in the API, not the web app | PASS | PASS — extraction, verification and conflict detection are API-side |
| G8 | **§2.** API types generated from OpenAPI, not hand-maintained | PASS | PASS — second contract added to generation and to the staleness check (R-006) |
| G9 | **§2.** Typed enumerations rather than free-text state | PASS | PASS — import status and source kind are enums |
| G10 | **§2.** Modular monolith; no new service | PASS | PASS — reuses the existing worker |
| G11 | **§2 / workflow.** Schema changes ship with a migration | PASS | PASS — one migration covers the new table and the columns added to feature 001 |
| G12 | **§2.** All model access behind the `AIProvider` abstraction; no provider SDK in feature code; structured output against an explicit schema; AI holds no database credentials and issues no writes | **First feature to exercise this.** PASS by design | **PASS** — one protocol, one concrete implementation, one fake; feature code imports the protocol only. The model returns a validated schema object and never touches the database: deterministic code validates and persists (R-004) |
| G13 | **§2 quality gate.** Changes to AI prompts or output schemas must state how Principle IV remains satisfied | — | PASS — the prompt lives in a single named module whose docstring points at the verifier, so a review of any prompt change has a defined place to check |
| G14 | **§3.** Secrets not committed | PASS | PASS — provider key named in `.env.example` only; `.env*` already ignored |
| G15 | **II / III.** Application event sourcing and next-action computation | Not applicable | Not applicable |

No gate fails. **Complexity Tracking is empty.**

The gate worth dwelling on is G12, which every feature so far has passed by
making no model calls at all. It passes here because the model occupies the
narrowest possible role: it proposes structured values with quoted sources, and
every consequential decision after that — does the quote verify, is this a
duplicate, does this become a profile entry — is made by deterministic code or by
the user.

## Project Structure

### Documentation (this feature)

```text
specs/002-ai-resume-import/
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
feature 001 and are modified here — named explicitly so they are built
deliberately rather than discovered mid-implementation.

```text
apps/
├── api/
│   ├── app/
│   │   ├── ai/                        # new — the model boundary (gate G12)
│   │   │   ├── provider.py            # the AIProvider protocol; the only thing feature code imports
│   │   │   ├── openai_provider.py     # the one concrete implementation
│   │   │   ├── fake.py                # scripted provider; every automated test uses this
│   │   │   └── schemas.py             # the structured output schema the model must satisfy
│   │   │
│   │   ├── imports/                   # new — this feature
│   │   │   ├── models.py              # Import
│   │   │   ├── documents.py           # PDF and DOCX text extraction; bytes never persisted (R-005)
│   │   │   ├── prompts.py             # the extraction prompt, docstring pointing at the verifier (G13)
│   │   │   ├── extraction.py          # orchestration: text in, verified entries out
│   │   │   ├── evidence.py            # the verifier — the enforcement of Principle IV (R-001)
│   │   │   ├── conflicts.py           # self-contradiction detection (FR-012a)
│   │   │   ├── dates.py               # deterministic era-year conversion (R-007)
│   │   │   ├── service.py             # import lifecycle, deadline and handoff (R-002)
│   │   │   ├── schemas.py             # request and response models
│   │   │   └── router.py              # /profile/imports
│   │   │
│   │   └── career/
│   │       ├── models.py              # changed — evidence, conflicts, import_id on ProposedEntry
│   │       └── proposals.py           # changed — accept and reject clear evidence (FR-015a)
│   │
│   ├── migrations/versions/           # new revision — import table + proposed_entry columns
│   └── tests/
│       ├── contract/                  # changed — read every contract file, not one named path (R-006)
│       ├── integration/               # new — the quickstart scenarios
│       └── unit/                      # new — evidence verifier, era dates, conflict detection
│
├── worker/worker/
│   ├── extraction.py                  # new — the handed-off import actor (R-002)
│   └── main.py                        # changed — register the actor
│
└── web/
    ├── app/[locale]/profile/import/   # new — start an import, watch it, see what was found
    ├── components/profile/
    │   ├── import-form.tsx            # new
    │   ├── import-status.tsx          # new — polling for a handed-off import
    │   └── proposal-review.tsx        # changed — show evidence and conflicts beside each value
    └── messages/                      # changed — strings for both languages

packages/api-client/
├── src/schema-001.ts                  # changed — renamed from schema.ts
├── src/schema-002.ts                  # new
└── src/index.ts                       # changed — re-export both (R-006)
```

**Structure Decision**: the model boundary lives in its own top-level module
rather than inside this feature, because it is shared infrastructure that later
AI features will use, and because keeping it separate is what makes gate G12
checkable — feature code importing anything but the protocol is visible in a
diff. Within the feature, the verifier, the conflict detector and the date
converter are separate modules from the orchestration that calls them, so each
can be tested without a provider at all. `apps/worker` gains a second actor
alongside the purge, sharing the API's models as before.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. This feature adds one abstraction — the provider protocol — which
the constitution mandates rather than this plan choosing.
