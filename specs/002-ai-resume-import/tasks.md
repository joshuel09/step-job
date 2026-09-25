---
description: "Task list for AI Resume Import implementation"
---

# Tasks: AI Resume Import

**Input**: Design documents from `/specs/002-ai-resume-import/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml), [quickstart.md](./quickstart.md)

**Tests**: Included. Constitution §3 requires every pull request to pass the
project's checks and forbids claiming a suite passed when none exists. Every
automated test uses the fake provider — nothing in continuous integration calls
a real model, because a test whose outcome depends on a model's mood tests
nothing.

**Organization**: Grouped by user story so each can be implemented and tested
independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are given in every task

## Changes to feature 001

Four tasks modify working, tested code from the Master Career Profile: T014,
T015, T016 and T017. They are listed separately rather than folded into new work
so the diff to a shipped feature is deliberate and reviewable.

---

## Phase 1: Setup

**Purpose**: Configuration and the two mechanisms that currently protect only one
contract and would silently stop protecting anything once a second appeared.

- [X] T001 Add the document and provider dependencies to `apps/api/pyproject.toml` — PDF and DOCX text extraction, and the provider client used only behind the abstraction
- [X] T002 [P] Add provider settings to `apps/api/app/core/settings.py` — which provider to use, its key, and the in-request deadline from research.md R-002, defaulting to the fake provider
- [ ] T003 [P] Document the provider key and deadline in `apps/api/.env.example`, without a value
- [X] T004 Rename the generated client to `packages/api-client/src/schema-001.ts` and re-export from `packages/api-client/src/index.ts`
- [X] T005 Extend the generation script in `packages/api-client/package.json` to produce one module per contract file, including `schema-002.ts`
- [X] T006 Update the staleness check in `.github/workflows/ci.yml` to diff the whole `packages/api-client/src/` directory rather than one named file
- [X] T007 Add a `live` pytest marker in `apps/api/pyproject.toml` so the one test that calls a real provider can be excluded by default

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The model boundary, the verifier that makes Principle IV
enforceable, and the schema both stories write into.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### The model boundary (constitution gate G12)

- [X] T008 Define the extraction output schema in `apps/api/app/ai/schemas.py` — the structured shape a provider must return, with a quoted source passage required for every field it fills
- [X] T009 Define the `AIProvider` protocol in `apps/api/app/ai/provider.py`, the only thing feature code may import, with the three failure classes from research.md R-004 as distinct exceptions
- [X] T010 [P] Implement `apps/api/app/ai/fake.py` — scripted results with no network access, including behaviours for unavailable, unparseable, and a field whose quote is absent from the source
- [X] T011 [P] Implement `apps/api/app/ai/openai_provider.py` against the protocol, requesting structured output and translating provider errors into the protocol's failure classes
- [X] T012 Wire provider selection in `apps/api/app/ai/__init__.py` so the fake is the default and no feature module ever imports a provider directly

### The verifier

- [X] T013 Implement the evidence verifier in `apps/api/app/imports/evidence.py` — a field survives only if its quoted passage is found in the source text, whitespace-normalised and otherwise exact, per research.md R-001

### Changes to feature 001

- [X] T014 Add `evidence`, `conflicts` and `import_id` as nullable columns on `ProposedEntry` in `apps/api/app/career/models.py`, keeping proposals created by other means valid without them
- [X] T015 Clear `evidence` when a proposal is accepted or rejected in `apps/api/app/career/proposals.py`, inside the same transaction that records the decision, so FR-015a survives a process dying immediately afterwards
- [X] T016 Expose `evidence` and `conflicts` on the proposal response in `apps/api/app/career/schemas.py`
- [X] T017 [P] Extend the contract test in `apps/api/tests/contract/test_profile_sections.py` to read every contract file rather than one named path, per research.md R-006

### This feature's own foundation

- [X] T018 Create the `Import` model in `apps/api/app/imports/models.py` with typed status and source-kind enumerations and a typed failure reason, and deliberately no filename column per FR-019b
- [X] T019 Generate the Alembic migration in `apps/api/migrations/` covering the new import table and the three columns added to `proposed_entry`
- [X] T020 [P] Add fixtures to `apps/api/tests/conftest.py` providing a fake provider and a source text fixture

**Checkpoint**: the boundary and the verifier exist — user story work can begin

---

## Phase 3: User Story 1 - Paste my career and let the system structure it (Priority: P1) 🎯 MVP

**Goal**: A user pastes career text and receives structured proposals in the
review queue, each value showing the words it came from. Nothing reaches the
profile.

**Independent Test**: paste text containing two roles and some skills; proposals
appear with evidence; the profile is unchanged. Covers quickstart Scenarios 1
and 2.

### Tests for User Story 1

- [ ] T021 [P] [US1] Unit tests for the evidence verifier in `apps/api/tests/unit/test_evidence.py` — a present quote survives, an absent quote is dropped, a missing quote is dropped, whitespace differences are tolerated, a near-miss is dropped
- [ ] T022 [P] [US1] Integration test for quickstart Scenario 2 in `apps/api/tests/integration/test_extraction_truthfulness.py`, proving a fabricated field never becomes a proposal
- [ ] T023 [P] [US1] Integration test for quickstart Scenario 1 in `apps/api/tests/integration/test_import_pasted_text.py`, including the check that proposals are invisible to the profile
- [ ] T024 [P] [US1] Integration test for quickstart Scenario 7 in `apps/api/tests/integration/test_evidence_lifecycle.py`, proving evidence is discarded at review and the accepted entry is unchanged
- [ ] T025 [P] [US1] Contract tests for the import routes in `apps/api/tests/contract/test_imports.py`

### Implementation for User Story 1

- [ ] T026 [US1] Write the extraction prompt in `apps/api/app/imports/prompts.py`, with a docstring naming the verifier as the enforcement so constitution gate G13 has a defined place to check
- [ ] T027 [US1] Implement conflict detection in `apps/api/app/imports/conflicts.py` — flag fields that disagree, never resolve them, per FR-012a and FR-012b
- [ ] T028 [US1] Implement extraction orchestration in `apps/api/app/imports/extraction.py`: source text in, verified entries out, with unverifiable fields dropped before anything is built
- [ ] T029 [US1] Implement within-document deduplication in `apps/api/app/imports/extraction.py` so a role described twice is proposed once, per FR-012
- [ ] T030 [US1] Implement the import lifecycle in `apps/api/app/imports/service.py` — states, the in-request deadline, and the outcome record from FR-016
- [ ] T031 [US1] Implement proposal creation from verified entries in `apps/api/app/imports/service.py`, writing only to the proposal table and never to the profile
- [ ] T032 [US1] Define request and response models in `apps/api/app/imports/schemas.py` matching `contracts/openapi.yaml`
- [ ] T033 [US1] Implement the paste and read routes in `apps/api/app/imports/router.py` — create from text, list, and follow one to its outcome
- [ ] T034 [US1] Register the import router in `apps/api/app/main.py`
- [ ] T035 [US1] Regenerate both typed clients into `packages/api-client/src/`
- [ ] T036 [P] [US1] Build the paste form in `apps/web/components/profile/import-form.tsx`
- [ ] T037 [P] [US1] Build the import page in `apps/web/app/[locale]/profile/import/page.tsx`
- [ ] T038 [US1] Show evidence and conflicts beside each proposed value in `apps/web/components/profile/proposal-review.tsx`, so a user can see what a value was based on before accepting it
- [ ] T039 [P] [US1] Add the English and Japanese strings for User Story 1 to `apps/web/messages/en.json` and `apps/web/messages/ja.json`

**Checkpoint**: pasting works end to end, and a fabricated field cannot reach a proposal

---

## Phase 4: User Story 2 - Import the resume file I already have (Priority: P2)

**Goal**: A user uploads a PDF or DOCX, gets the same proposals, and the file is
never written anywhere.

**Independent Test**: upload a PDF and a DOCX with the same content; both produce
equivalent proposals; nothing was persisted. Covers quickstart Scenarios 3 and 6.

### Tests for User Story 2

- [ ] T040 [P] [US2] Unit tests for document text extraction in `apps/api/tests/unit/test_documents.py`, including the no-text-layer threshold that distinguishes a scanned page from a readable one
- [ ] T041 [P] [US2] Integration test for quickstart Scenario 3 in `apps/api/tests/integration/test_import_upload.py`, asserting nothing was written to disk
- [ ] T042 [P] [US2] Integration test for quickstart Scenario 6 in `apps/api/tests/integration/test_import_failures.py`, proving a service outage is reported as unavailable rather than as an unreadable document, with retries bounded and nothing left behind
- [ ] T043 [P] [US2] Add invented-content test fixtures in `apps/api/tests/fixtures/` — a readable PDF, a DOCX, and a PDF with no text layer

### Implementation for User Story 2

- [ ] T044 [US2] Implement PDF and DOCX text extraction in `apps/api/app/imports/documents.py`, reading bytes from the upload and releasing them without writing, per research.md R-005
- [ ] T045 [US2] Implement unreadable and unsupported detection in `apps/api/app/imports/documents.py`, returning the distinct failure reasons from data-model.md
- [ ] T046 [US2] Implement bounded retry in `apps/api/app/imports/service.py`, separating an unavailable service from an unusable response, per FR-017a to FR-017c
- [ ] T047 [US2] Implement the upload route in `apps/api/app/imports/router.py`, the project's first multipart endpoint, with a size limit
- [ ] T048 [US2] Regenerate both typed clients into `packages/api-client/src/`
- [ ] T049 [P] [US2] Add file upload to `apps/web/components/profile/import-form.tsx` with the accepted formats stated before the user tries, per FR-003
- [ ] T050 [P] [US2] Add the English and Japanese strings for User Story 2 to `apps/web/messages/en.json` and `apps/web/messages/ja.json`

**Checkpoint**: file import works, and no document is ever at rest

---

## Phase 5: User Story 3 - Import my 職務経歴書 as it is written (Priority: P3)

**Goal**: A Japanese resume is read as the structure it is, and its entries stay
in Japanese.

**Independent Test**: import a 職務経歴書 with a 職務要約 and two roles; entries
carry their Japanese text and record Japanese as their language. Covers
quickstart Scenario 8.

### Tests for User Story 3

- [ ] T051 [P] [US3] Unit tests for era-year conversion in `apps/api/tests/unit/test_dates.py`, covering each era, a boundary year, and an unrecognised era failing visibly rather than producing a confident wrong year
- [ ] T052 [P] [US3] Integration test for quickstart Scenario 8 in `apps/api/tests/integration/test_import_japanese.py`, asserting the converted date, the original text as evidence, and that nothing was translated
- [ ] T053 [P] [US3] Add an invented 職務経歴書 fixture in `apps/api/tests/fixtures/`

### Implementation for User Story 3

- [ ] T054 [US3] Implement deterministic era-year conversion in `apps/api/app/imports/dates.py`, per research.md R-007, with the original text preserved as the evidence for the converted value
- [ ] T055 [US3] Implement source-language detection per entry in `apps/api/app/imports/extraction.py`, with no translation step, per FR-010
- [ ] T056 [US3] Extend the extraction prompt in `apps/api/app/imports/prompts.py` to read Japanese resume conventions as structure, restating in its docstring how Principle IV is preserved, per gate G13
- [ ] T057 [P] [US3] Add the English and Japanese strings for User Story 3 to `apps/web/messages/en.json` and `apps/web/messages/ja.json`

**Checkpoint**: all three stories work independently

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: The handoff, cancellation, the history record, and the checks that
confirm the whole thing.

- [ ] T058 Implement the handed-off extraction actor in `apps/worker/worker/extraction.py`, reaching the same outcomes as an in-request import, per FR-005c
- [ ] T059 Register the extraction actor in `apps/worker/worker/main.py`
- [ ] T060 [P] Worker tests for the handoff in `apps/worker/tests/test_extraction.py`, including that a background failure still creates no proposals
- [ ] T061 Integration test for quickstart Scenario 4 in `apps/api/tests/integration/test_import_handoff.py`, proving an import survives the user leaving and produces the same result as one completed in place
- [ ] T062 Implement import cancellation in `apps/api/app/imports/service.py` and `router.py`, per FR-018
- [ ] T063 [P] Build import status polling in `apps/web/components/profile/import-status.tsx`, so a handed-off import is visible and its result announced
- [ ] T064 [P] Build the import history view in `apps/web/app/[locale]/profile/import/page.tsx`, showing source kind and time and never a filename, per FR-019a and FR-019b
- [ ] T065 [P] Integration test for quickstart Scenario 5 in `apps/api/tests/integration/test_import_conflicts.py`, proving a self-contradictory source is flagged with its dates as written
- [ ] T066 [P] Add structured logging across `apps/api/app/imports/`, recording outcomes and never document content, following the existing allow-list formatter
- [ ] T067 Add the live provider smoke test in `apps/api/tests/live/test_live_extraction.py`, marked `live` and skipped without a key, asserting every proposed field carries verified evidence
- [ ] T068 Run the full [quickstart.md](./quickstart.md) walkthrough against a fresh environment and record the result

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup; **blocks every user story**
- **User Stories (Phases 3 to 5)**: all depend on Foundational
- **Polish (Phase 6)**: T058 to T061 depend on User Story 1's service; the rest
  depend on the stories they touch

### User Story Dependencies

- **User Story 1 (P1)**: depends only on Foundational. It is the whole extraction
  path, so the others build on it
- **User Story 2 (P2)**: adds document handling in front of US1's extraction.
  Independently testable once US1's path exists
- **User Story 3 (P3)**: adds date conversion and language detection to US1's
  extraction. Deliver last

### Within Each User Story

- Tests are written before the implementation they cover
- The verifier precedes anything that produces proposals
- Models precede services; services precede routes; routes precede the interface
- Clients are regenerated after routes change and before the interface uses them

### Parallel Opportunities

- T002, T003 and T007 run in parallel once T001 lands
- T010 and T011 run in parallel — two implementations of one protocol
- T014 to T017, the feature 001 changes, are independent of this feature's
  foundation and can run alongside T018 to T020
- All five US1 test tasks run in parallel
- Web tasks within a story run in parallel

## Parallel Example: User Story 1

```text
# After Foundational completes, the five test tasks together:
T021 evidence verifier   T022 truthfulness   T023 paste end to end
T024 evidence lifecycle  T025 contract

# Then serially through the extraction path:
T026 → T027 → T028 → T029 → T030 → T031 → T032 → T033 → T034 → T035

# Then the interface together:
T036 paste form   T037 import page   T039 translations
# T038 follows, since it changes a component US1's tests exercise
```

## Implementation Strategy

**MVP is User Story 1.** Phases 1, 2 and 3 deliver the feature's actual value: a
user pastes their career and gets structured, evidenced proposals. File handling
and Japanese conventions widen who can use it, but the extraction path is the
feature.

**T013 and T021 are the load-bearing tasks.** The verifier and its tests are what
make Principle IV enforceable rather than instructed. If they are weakened —
fuzzy matching, a warning instead of a drop, a field allowed through unverified —
the guarantee in SC-003 is gone and nothing else in this list restores it.

**T014 to T017 touch shipped code.** Feature 001 is built, tested and merged.
These four tasks should be reviewed as changes to working software, not as new
work that happens to live in old files.

**Suggested delivery order**: Phase 1 → Phase 2 → Phase 3 (ship the MVP) →
Phase 4 → T058 to T061 → Phase 5 → remaining Phase 6.
