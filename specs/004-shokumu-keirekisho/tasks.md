---
description: "Task list for 職務経歴書 Generator implementation"
---

# Tasks: 職務経歴書 Generator

**Input**: Design documents from `/specs/004-shokumu-keirekisho/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml), [quickstart.md](./quickstart.md)

**Tests**: Included. Every document test asserts on text extracted back out of a
generated document rather than on bytes — a PDF of hollow boxes is the right
size and passes any weaker check.

**Organization**: Grouped by user story so each can be implemented and tested
independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are given in every task

## Changes to shipped code

Phase 2 moves working, tested code out of `app/rirekisho/` into a shared
`app/documents/`. It is listed as its own phase because the diff to software
that already ships should be deliberate and reviewable on its own. The existing
履歴書 suite is the safety net: it must pass unchanged after every task in that
phase, and any test edit there that is not a pure import change is a signal the
refactor went wrong.

---

## Phase 1: Setup

**Purpose**: Nothing to install. This feature reuses what feature 003 brought in.

- [ ] T001 Confirm the PDF library and the font are already runtime dependencies in `apps/api/pyproject.toml`, and record that no dependency is added
- [ ] T002 Create `apps/api/app/shokumu/__init__.py` and `apps/api/tests/unit/`, `tests/integration/`, `tests/contract/` placements for this feature's tests

---

## Phase 2: Foundational — the shared document module

**Purpose**: One font, one era table, one page-flow class, shared by both
documents. This is how FR-018 holds structurally rather than by two
implementations agreeing by luck (research.md R-001).

**⚠️ CRITICAL**: No user story work begins until this phase is complete and the
履歴書 suite passes unchanged.

- [ ] T003 Create `apps/api/app/documents/` and move the font directory there from `apps/api/app/rirekisho/fonts/`, keeping the licence file beside it
- [ ] T004 Move font registration, `FontUnavailable`, `PAGE_SIZES` and `page_size()` into `apps/api/app/documents/typography.py`, still registering at import so a missing font stops the application rather than one request
- [ ] T005 Move the `_Page` class, which knows when a page is full, into `apps/api/app/documents/typography.py` as a public `Page`
- [ ] T006 Point `apps/api/app/rirekisho/render.py` at `app/documents/typography.py` and delete the moved code, changing imports only
- [ ] T007 Run the full 履歴書 suite in `apps/api/tests/` and confirm it passes with no test edited except for import paths — the refactor's only acceptance criterion
- [ ] T008 Add a unit test in `apps/api/tests/unit/test_documents_typography.py` asserting the font registers once and `page_size` rejects an unknown name

**Checkpoint**: both documents can draw from one typographic base.

---

## Phase 3: User Story 1 — Turn my profile into a 職務経歴書 (Priority: P1) 🎯 MVP

**Goal**: A profile becomes a career history document an employer could read.

**Independent test**: record two employers and a career story, generate, and
read the result. Every employer appears, every recorded achievement appears, and
nothing appears the profile does not hold.

### Tests for User Story 1

- [ ] T009 [P] [US1] Unit tests for the section projection in `apps/api/tests/unit/test_shokumu_sections.py` — one section per employer, achievements under the employer they belong to, undated entries last rather than dropped, overlapping employment unreconciled
- [ ] T010 [P] [US1] Unit tests for 職務要約 in `apps/api/tests/unit/test_shokumu_summary.py` — span, employer count and latest role are computed from entries; a thin profile yields a shorter summary; **no adjective characterising the applicant appears in any case**
- [ ] T011 [P] [US1] Integration test for quickstart Scenario 0 in `apps/api/tests/integration/test_shokumu_font.py`, extracting 職務経歴書 as text and asserting `/FontFile2` is present
- [ ] T012 [P] [US1] Integration test for quickstart Scenario 1 in `apps/api/tests/integration/test_shokumu_generate.py`, asserting employers, periods, titles, descriptions and achievements appear and a snapshot id is returned. Also assert the document is not retained (FR-005) — feature 003's `test_nothing_in_the_schema_can_hold_a_generated_document` iterates every table in `Base.metadata` and so already covers this feature, but reference it here so the guarantee is stated rather than accidental
- [ ] T013 [P] [US1] Integration test for quickstart Scenario 10 in `apps/api/tests/integration/test_shokumu_generate.py`, asserting a profile with no name and a profile with no work history are each refused with the missing thing named
- [ ] T014 [P] [US1] Contract tests for the document route in `apps/api/tests/contract/test_shokumu.py`, including that the documented response headers are exposed to a cross-origin caller

### Implementation for User Story 1

- [ ] T015 [US1] Implement the section projection in `apps/api/app/shokumu/sections.py` as a pure function from entries to `CareerHistory`, with no knowledge of documents, per data-model.md
- [ ] T016 [US1] Carry `source_entry_id` through every section and achievement in `apps/api/app/shokumu/sections.py`, so any statement traces to the entry behind it (FR-016)
- [ ] T017 [US1] Implement 職務要約 in `apps/api/app/shokumu/summary.py` from countable facts only — span, employer count, latest role and employer — per research.md R-003
- [ ] T018 [US1] Define the request and report shapes in `apps/api/app/shokumu/schemas.py` as enums, matching the contract
- [ ] T019 [US1] Implement the layout in `apps/api/app/shokumu/render.py`, drawing the summary, the employer sections and their achievements at A4
- [ ] T020 [US1] Implement generation and snapshot capture in `apps/api/app/shokumu/service.py`, capturing in the render's transaction with the identity leading the captured ids, per research.md R-006
- [ ] T021 [US1] Implement the generate route in `apps/api/app/shokumu/router.py`, streaming the document and returning the snapshot id and page count as headers
- [ ] T022 [US1] Register the router in `apps/api/app/main.py` and add the document headers to the CORS allow-list if they are not already there
- [ ] T023 [US1] Remove `/profile/documents/shokumu-keirekisho` from `DEFERRED` in `apps/api/tests/contract/test_contracts.py`, now that it is implemented
- [ ] T024 [US1] Regenerate the typed clients into `packages/api-client/src/`

**Checkpoint**: a profile produces a readable career history.

---

## Phase 4: User Story 2 — Arrange it the way this employer expects (Priority: P2)

**Goal**: Two arrangements and the same conventions the 履歴書 offers, with the
content identical and only the presentation different.

**Independent test**: generate the same profile both ways and confirm each
contains the identical set of entries in a different order.

### Tests for User Story 2

- [ ] T025 [P] [US2] Integration test for quickstart Scenario 2 in `apps/api/tests/integration/test_shokumu_arrangement.py`, asserting the two orders carry **the identical set of entries** with none gained, lost, merged or shortened, and that an unknown arrangement is refused
- [ ] T026 [P] [US2] Integration test for quickstart Scenario 3 in `apps/api/tests/integration/test_shokumu_conventions.py`, asserting a 和暦 document has **no four-digit Western year anywhere** and a 西暦 document has no era name, and that both paper sizes carry the same content

### Implementation for User Story 2

- [ ] T027 [US2] Apply the chosen arrangement in `apps/api/app/shokumu/sections.py`, with undated entries last in both directions
- [ ] T028 [US2] Apply the date convention throughout `apps/api/app/shokumu/render.py` using the shared era rendering, never mixing the two in one document
- [ ] T029 [US2] Support B5 alongside A4 in `apps/api/app/shokumu/render.py`, with the same content at either size
- [ ] T030 [US2] Support preview in `apps/api/app/shokumu/router.py`, returning the identical document with a different disposition
- [ ] T031 [P] [US2] Integration test asserting a preview and a download are the same document in `apps/api/tests/integration/test_shokumu_preview.py`, comparing what is drawn rather than only the extracted text

**Checkpoint**: the conventions are the user's to choose, and the preview is honest.

---

## Phase 5: User Story 3 — Say only what I have said (Priority: P3)

**Goal**: A thin profile produces a thin document. Nothing is invented, and the
sections the product does not write are labelled and left empty.

**Independent test**: record an employer with a name and dates and nothing else,
generate, and confirm the document says exactly that much about it.

### Tests for User Story 3

- [ ] T032 [P] [US3] Integration test for quickstart Scenario 5 in `apps/api/tests/integration/test_shokumu_blanks.py` — an employer with no description gets no invented narrative, and an empty section has no placeholder. Assert the whole document against an expected set of lines rather than searching for known placeholders, which only catches the ones someone thought of
- [ ] T033 [P] [US3] Integration test asserting 自己PR is present, labelled and empty in every document whatever the profile holds, in `apps/api/tests/integration/test_shokumu_blanks.py`
- [ ] T034 [P] [US3] Integration test for quickstart Scenario 6 in `apps/api/tests/integration/test_shokumu_unattached.py` — count the recorded stories going in and out; a story with no employer appears in the closing section; a profile whose stories are all unattached has empty employer sections and a full closing one
- [ ] T035 [P] [US3] Integration test for quickstart Scenario 7 in `apps/api/tests/integration/test_shokumu_traceability.py`, asserting a snapshot still shows what a document used after its entries are edited
- [ ] T036 [P] [US3] Integration test asserting no Japan-specific field appears in the document regardless of its disclosure flag, in `apps/api/tests/integration/test_shokumu_blanks.py` — gate G5 holds here by exclusion, and this is what proves it

### Implementation for User Story 3

- [ ] T037 [US3] Produce empty sections empty in `apps/api/app/shokumu/render.py` — no placeholder, no sample, no inferred content (FR-013)
- [ ] T038 [US3] Render 自己PR as a labelled, empty section in `apps/api/app/shokumu/render.py`, per research.md R-007
- [ ] T039 [US3] Render the closing achievements section for stories attached to no employer in `apps/api/app/shokumu/render.py`, per research.md R-005
- [ ] T040 [P] [US3] Add the English and Japanese strings for this feature to `apps/web/messages/en.json` and `apps/web/messages/ja.json`
- [ ] T054 [P] [US3] Integration test for quickstart Scenario 11 in `apps/api/tests/integration/test_shokumu_english.py`, asserting entries recorded in English appear in English exactly as written and that nothing in the document is Japanese the user did not write (FR-015). Subtract the user's own values, the document's fixed vocabulary and the dates, then assert no Japanese remains — a blocklist of known translations only catches the ones someone thought of. Include a guard case confirming the subtraction does see a planted translation

**Checkpoint**: the document says what the profile says, and no more.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T041 Implement the readiness report in `apps/api/app/shokumu/readiness.py`, separating what cannot be left out from what will simply be blank, and naming achievements recorded against no employer
- [ ] T042 Implement the readiness route in `apps/api/app/shokumu/router.py`
- [ ] T043 Remove `/profile/documents/shokumu-keirekisho/readiness` from `DEFERRED` in `apps/api/tests/contract/test_contracts.py` **and from `UNVALIDATED` in `apps/api/tests/contract/test_response_schemas.py`** — both lists, together, or the second silently stops covering it
- [ ] T044 [P] Integration test for the readiness report in `apps/api/tests/integration/test_shokumu_readiness.py`
- [ ] T045 Support a career longer than the conventional pages in `apps/api/app/shokumu/render.py`, producing every entry across as many pages as needed and reporting the count (FR-011)
- [ ] T046 [P] Integration test for quickstart Scenario 9 in `apps/api/tests/integration/test_shokumu_long_history.py`, counting entries in and out so none is dropped or truncated
- [ ] T047 Integration test for quickstart Scenario 8 in `apps/api/tests/integration/test_document_agreement.py`, asserting a 履歴書 and a 職務経歴書 from the same profile agree on every employer, period and title that both carry (FR-018)
- [ ] T048 Regenerate the typed clients into `packages/api-client/src/`
- [ ] T049 [P] Build the document page in `apps/web/app/[locale]/profile/documents/shokumu-keirekisho/page.tsx`
- [ ] T050 [P] Build the generate control in `apps/web/components/profile/shokumu-form.tsx`, with the arrangement, convention and paper choices and a preview
- [ ] T051 [P] Add a link to the new page from `apps/web/app/[locale]/profile/page.tsx` with strings in both languages — a page nobody can reach is not shipped
- [ ] T052 [P] Add structured logging across `apps/api/app/shokumu/`, recording outcomes and never document content, following the existing allow-list formatter
- [ ] T053 Run the full walkthrough in `specs/004-shokumu-keirekisho/quickstart.md` against a fresh environment and record the result

---

## Dependencies & Execution Order

### Phase dependencies

```
Phase 1 (setup)
   └── Phase 2 (shared module)  ← blocks everything; 履歴書 suite must stay green
          ├── Phase 3 (US1)     ← the MVP
          │      ├── Phase 4 (US2)
          │      └── Phase 5 (US3)
          └── Phase 6 (polish)  ← needs US1; readiness needs the service
```

### User story dependencies

- **US1** depends only on Phase 2. It is the MVP and ships alone.
- **US2** depends on US1's projection and renderer.
- **US3** depends on US1's renderer. **It does not depend on US2**, so the two
  can be built in either order or in parallel.
- Phase 6's readiness report depends on US1's service; the web page depends on
  the route existing.

### Within each user story

Tests before implementation. The projection and the summary are pure functions
and are tested without producing a document, which is the point of separating
them (research.md R-002).

### Parallel opportunities

All six US1 test tasks (T009 to T014) are independent files and run together:

```
T009 sections   T010 summary   T011 font
T012 generate   T013 refusals  T014 contract
```

The implementation chain is sequential, because each step builds on the last:

```
T015 → T016 → T017 → T018 → T019 → T020 → T021 → T022 → T023 → T024
```

US3's five test tasks (T032 to T036) are likewise independent of each other.

---

## Implementation strategy

**MVP is Phase 1 + Phase 2 + Phase 3.** That produces a 職務経歴書 from a
profile, which is the whole feature in its smallest honest form. US2 and US3
refine how it reads and what it withholds; neither is needed for the document to
exist.

**Phase 2 is the risk, not the work.** Moving tested code is where a feature
like this breaks something that already ships. It is sequenced first, kept to
import changes on the 履歴書 side, and gated on that suite passing unchanged
(T007). If a 履歴書 test needs editing beyond an import path, the refactor is
wrong and should be reconsidered rather than the test adjusted.

**T054 is appended rather than inserted.** `/speckit-analyze` found FR-015 had
no task after the list was written. Appending keeps every existing task id
stable, which matters once work is in flight; the phase heading places it, not
its number.

**The deferral lists shrink as routes land** (T023, T043), not at the end. T043
names both lists deliberately: feature 004's own planning found that
`test_response_schemas.py` covered only a hardcoded set of features, so a list
updated in one place and not the other silently stops checking.
