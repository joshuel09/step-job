---
description: "Task list for 履歴書 Generator implementation"
---

# Tasks: 履歴書 Generator

**Input**: Design documents from `/specs/003-rirekisho-generator/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml), [quickstart.md](./quickstart.md)

**Tests**: Included. Constitution §3 requires every pull request to pass the
project's checks. Every test here asserts on text extracted back out of a
generated document rather than on bytes or on a file existing — a PDF full of
hollow boxes is the right size and passes any weaker check.

**Organization**: Grouped by user story so each can be implemented and tested
independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are given in every task

## Changes to earlier features

Five tasks modify shipped code: T004 to T008 add two fields to feature 001's
identity record and extend feature 002's date module. They are listed separately
so the diff to working software is deliberate.

---

## Phase 1: Setup

**Purpose**: The PDF dependency and the font, which is the quiet failure in this
feature.

- [X] T001 Promote the PDF library in `apps/api/pyproject.toml` from a development dependency to a runtime one, per research.md R-002
- [X] T002 Add one open-licensed Japanese font and its licence text to `apps/api/app/rirekisho/fonts/`, choosing a font whose licence permits redistribution
- [X] T003 Register the font at application start in `apps/api/app/rirekisho/render.py`, failing loudly at startup if it cannot be loaded rather than at render time

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The change to feature 001, and the era rendering this feature needs
from feature 002.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Changes to feature 001 — four touch points

- [X] T004 Add `date_of_birth` and `address` as nullable columns on `Identity` in `apps/api/app/career/models.py`, both optional so existing profiles stay valid
- [X] T005 Generate the Alembic migration for those two columns in `apps/api/migrations/`
- [X] T006 [P] Add the two fields to `IdentityIn` and `IdentityOut` in `apps/api/app/career/schemas.py`
- [X] T007 [P] Document the two fields on the `Identity` schema in `specs/001-master-career-profile/contracts/openapi.yaml`
- [X] T008 [P] Add the two fields to the identity form in `apps/web/components/profile/identity-form.tsx` — without this the generator has fields no user can fill in

### Change to feature 002

- [X] T009 Add calendar-date-to-era rendering beside the existing era parsing in `apps/api/app/imports/dates.py`, sharing the one era table so the two directions cannot drift, per research.md R-005
- [X] T010 [P] Unit tests for era rendering in `apps/api/tests/unit/test_dates.py`, covering each era, the 平成 to 令和 boundary, and that rendering then parsing returns the original date

### This feature's foundation

- [X] T011 Define the request and response models in `apps/api/app/rirekisho/schemas.py`, matching `contracts/openapi.yaml`
- [X] T012 [P] Add a fixture profile with invented content in `apps/api/tests/conftest.py` — identity, education and two work experiences, one ongoing

**Checkpoint**: the profile holds what a 履歴書 needs and dates render both ways

---

## Phase 3: User Story 1 - Turn my profile into a 履歴書 (Priority: P1) 🎯 MVP

**Goal**: A complete profile produces a correctly laid out 履歴書, and the
document records what it was based on.

**Independent Test**: generate from a complete profile; every 学歴・職歴 row
corresponds to a profile entry, in the right order, with the right conventions.
Covers quickstart Scenarios 0 and 1.

### Tests for User Story 1

- [X] T013 [P] [US1] Unit tests for the 学歴・職歴 projection in `apps/api/tests/unit/test_rirekisho_rows.py` — education before employment, oldest first within each block, two rows per entry, 現在に至る for an unfinished role, 以上 last, overlapping entries both present and unreconciled
- [X] T014 [P] [US1] Integration test for quickstart Scenario 0, extracting text from a generated document and asserting 履歴書 appears as text — the check that fails loudly when the font is missing. Landed as `apps/api/tests/unit/test_rirekisho_font.py` (registration) plus `test_the_japanese_is_readable` and `test_the_glyphs_are_embedded` in `apps/api/tests/integration/test_rirekisho_generate.py` (a real document), rather than at the single path named here
- [X] T015 [P] [US1] Integration test for quickstart Scenario 1 in `apps/api/tests/integration/test_rirekisho_generate.py`, asserting the table contents and that a snapshot id is returned
- [X] T016 [P] [US1] Integration test asserting a snapshot still shows what a document used after its entries are edited, in `apps/api/tests/integration/test_rirekisho_traceability.py`
- [X] T017 [P] [US1] Contract tests for the document routes in `apps/api/tests/contract/test_rirekisho.py`

### Implementation for User Story 1

- [X] T018 [US1] Implement the 学歴・職歴 projection in `apps/api/app/rirekisho/rows.py` as a pure function from entries to ordered rows, with no knowledge of PDFs, per research.md R-006
- [X] T019 [US1] Carry the id of the entry that produced each row through the projection in `apps/api/app/rirekisho/rows.py`, so any line in the document can be traced to what it came from per FR-012
- [X] T020 [US1] Implement the document layout in `apps/api/app/rirekisho/render.py`, drawing the conventional form at A4
- [X] T021 [US1] Implement generation and snapshot capture in `apps/api/app/rirekisho/service.py`, capturing in the same transaction as the render so a failed render leaves no record of a document that never existed, per research.md R-003
- [X] T022 [US1] Implement the generate route in `apps/api/app/rirekisho/router.py`, streaming the document and returning the snapshot id and page count as headers
- [X] T023 [US1] Register the router in `apps/api/app/main.py`
- [X] T024 [US1] Remove `/profile/documents/rirekisho` from the deferred list in `apps/api/tests/contract/test_contracts.py`, now that it is implemented
- [X] T025 [US1] Regenerate all three typed clients into `packages/api-client/src/`
- [X] T026 [P] [US1] Build the document page in `apps/web/app/[locale]/profile/documents/rirekisho/page.tsx`
- [X] T027 [P] [US1] Build the generate control in `apps/web/components/profile/rirekisho-form.tsx`
- [X] T028 [P] [US1] Add the English and Japanese strings for User Story 1 to `apps/web/messages/en.json` and `apps/web/messages/ja.json`

**Checkpoint**: a 履歴書 is produced, readable, and traceable

---

## Phase 4: User Story 2 - Produce it the way this employer expects (Priority: P2)

**Goal**: The user chooses the date convention and page size, and sees the
document before downloading it.

**Independent Test**: generate the same profile in each convention and size;
content identical, presentation different. Covers quickstart Scenario 2.

### Tests for User Story 2

- [X] T029 [P] [US2] Integration test for quickstart Scenario 2 in `apps/api/tests/integration/test_rirekisho_conventions.py`, asserting each document matches its own convention and neither matches the other's
- [X] T030 [P] [US2] Integration test asserting a preview and a download contain identical text, in `apps/api/tests/integration/test_rirekisho_preview.py` — a user must never preview one document and download another — compares what is drawn, not only the text, and at every date convention and paper size

### Implementation for User Story 2

- [X] T031 [US2] Apply the chosen date convention throughout a document in `apps/api/app/rirekisho/render.py`, using the era rendering from T009 and never mixing the two within one document per FR-019 — the table already followed it; the date of birth did not, and T029 found it
- [X] T032 [US2] Support B5 alongside A4 in `apps/api/app/rirekisho/render.py`, with the same content at either size — already in place; proven by T030's paper-size tests
- [X] T033 [US2] Support preview in `apps/api/app/rirekisho/router.py`, returning the identical document with a different disposition — already in place; proven by T030's parity tests
- [X] T034 [US2] Regenerate all three typed clients into `packages/api-client/src/` — already current; regenerating produces no diff
- [X] T035 [P] [US2] Add convention and paper-size controls, and a preview, to `apps/web/components/profile/rirekisho-form.tsx` — shipped with User Story 1 in #56
- [X] T036 [P] [US2] Add the English and Japanese strings for User Story 2 to `apps/web/messages/en.json` and `apps/web/messages/ja.json` — shipped with User Story 1 in #56

**Checkpoint**: conventions are the user's to choose, and the preview is honest

---

## Phase 5: User Story 3 - Leave blank what I have not said (Priority: P3)

**Goal**: An incomplete profile produces a document with those fields empty, and
nothing a user did not enter appears anywhere.

**Independent Test**: generate from a deliberately incomplete profile; every
absent field is blank, with nothing filled in on the user's behalf. Covers
quickstart Scenarios 3, 4, 5 and 7.

### Tests for User Story 3

- [ ] T037 [P] [US3] Integration test for quickstart Scenario 3 in `apps/api/tests/integration/test_rirekisho_blanks.py` — an empty section has no rows and no placeholder, and a profile with no name is refused with the field named
- [ ] T038 [P] [US3] Integration test for quickstart Scenario 4 in `apps/api/tests/integration/test_rirekisho_disclosure.py`, with one case per disclosure flag: undisclosed means absent from the extracted text, disclosed means present
- [ ] T039 [P] [US3] Integration test for quickstart Scenario 5 in `apps/api/tests/integration/test_rirekisho_english.py`, asserting English entries appear as written and that nothing in the document is Japanese the user did not write
- [ ] T040 [P] [US3] Integration test for quickstart Scenario 7 asserting no 性別 field appears anywhere, in `apps/api/tests/integration/test_rirekisho_blanks.py`
- [ ] T041 [P] [US3] Unit tests for disclosure filtering in `apps/api/tests/unit/test_rirekisho_disclosure.py`, one case per flag

### Implementation for User Story 3

- [ ] T042 [US3] Implement disclosure filtering in `apps/api/app/rirekisho/disclosure.py`, applied before rendering so an undisclosed value never reaches the renderer at all, per data-model.md and gate G5
- [ ] T043 [US3] Render a disclosed Japan-specific field in 本人希望記入欄 in `apps/api/app/rirekisho/render.py`
- [ ] T044 [US3] Produce empty sections empty in `apps/api/app/rirekisho/render.py` — no placeholder, no sample, no inferred content, per FR-013
- [ ] T045 [US3] Label every deliberately empty section in `apps/api/app/rirekisho/render.py`, including the photograph frame, 志望の動機 and 本人希望記入欄, per FR-022a to FR-022c
- [ ] T046 [US3] Refuse generation when the profile lacks a name, naming the missing field in `apps/api/app/rirekisho/service.py`, per FR-015
- [ ] T047 [P] [US3] Add the English and Japanese strings for User Story 3 to `apps/web/messages/en.json` and `apps/web/messages/ja.json`

**Checkpoint**: all three stories work independently, and nothing is invented

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: The readiness report, the long-history case, and the checks that
confirm the whole thing.

- [ ] T048 Implement the readiness report in `apps/api/app/rirekisho/readiness.py`, separating what cannot be left out from what will simply be blank, and naming the entries written in English
- [ ] T049 Implement the readiness route in `apps/api/app/rirekisho/router.py`
- [ ] T050 Remove `/profile/documents/rirekisho/readiness` from the deferred list in `apps/api/tests/contract/test_contracts.py`, leaving feature 003 with an empty deferral set
- [ ] T051 [P] Integration test for the readiness report in `apps/api/tests/integration/test_rirekisho_readiness.py`, asserting it names missing required fields, blank optional ones, and English entries
- [ ] T052 Support a history longer than the conventional two pages in `apps/api/app/rirekisho/render.py`, producing every entry across as many pages as needed and reporting the count, per FR-018a
- [ ] T053 [P] Integration test for quickstart Scenario 6 in `apps/api/tests/integration/test_rirekisho_long_history.py`, asserting no entry is dropped or shortened to fit
- [ ] T054 Regenerate all three typed clients into `packages/api-client/src/`
- [ ] T055 [P] Build the readiness view in `apps/web/components/profile/rirekisho-readiness.tsx`, showing what is missing and which entries have no Japanese version
- [ ] T056 [P] Add structured logging across `apps/api/app/rirekisho/`, recording outcomes and never document content, following the existing allow-list formatter
- [ ] T057 [P] Add a link to the document page from `apps/web/app/[locale]/profile/page.tsx`, with strings in both languages
- [ ] T058 Run the full [quickstart.md](./quickstart.md) walkthrough against a fresh environment and record the result

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T003 depends on T002 — there is no font
  to register until one is present
- **Foundational (Phase 2)**: depends on Setup; **blocks every user story**
- **User Stories (Phases 3 to 5)**: all depend on Foundational
- **Polish (Phase 6)**: depends on the stories it touches

### User Story Dependencies

- **User Story 1 (P1)**: depends only on Foundational. It is the whole pipeline,
  so the others extend it
- **User Story 2 (P2)**: adds conventions to US1's renderer. Independently
  testable once a document can be produced
- **User Story 3 (P3)**: adds filtering and blank handling to US1's renderer.
  Deliver last, since its tests assert on what a produced document omits

### Within Each User Story

- Tests are written before the implementation they cover
- The projection precedes the renderer; the renderer precedes the route
- Clients are regenerated after routes change and before the interface uses them
- The deferral list shrinks as paths land (T024, T050), rather than at the end

### Parallel Opportunities

- T006, T007 and T008 run in parallel once T004 and T005 land — three different
  files expressing the same change
- T010 and T012 run in parallel with the feature 001 changes
- All five US1 test tasks (T013 to T017) run in parallel
- Web tasks within a story run in parallel

## Parallel Example: User Story 1

```text
# After Foundational completes, the five test tasks together:
T013 the projection   T014 the font   T015 generation
T016 traceability     T017 contract

# Then serially through the pipeline:
T018 → T019 → T020 → T021 → T022 → T023 → T024 → T025

# Then the interface together:
T026 page   T027 form   T028 strings
```

## Implementation Strategy

**MVP is User Story 1.** Phases 1, 2 and 3 produce a correct, readable,
traceable 履歴書 from a complete profile. Conventions and blank handling refine
a document that must first exist.

**T002 and T014 are the pair that matters most in Phase 1.** Without an embedded
Japanese font every character renders as a hollow box — the file is produced, the
right size, and unreadable — and a developer with Japanese system fonts may never
reproduce it. T014 extracts the text back out and fails loudly. Every other test
in this list assumes that one passes.

**T038 and T042 are the pair that matters most for safety.** The disclosure flags
have defaulted closed since feature 001 in a table nothing read. This is the
first feature that reads them, so the first place the rule can be observed to
work and the first place it could be got wrong. One test per flag, asserting on
extracted text, because the failure mode is publishing someone's immigration
status.

**T004 to T008 touch shipped code.** Feature 001 is built and merged. The web
form is listed separately and deliberately: adding the columns without it would
be complete in the API and useless in the product.

**Suggested delivery order**: Phase 1 → Phase 2 → Phase 3 (ship the MVP) →
Phase 5 → Phase 4 → Phase 6. User Story 3 before User Story 2 deliberately —
getting the disclosure filtering right matters more than the date conventions,
and shipping a document that could leak a visa status while waiting on 和暦
support would be the wrong order.
