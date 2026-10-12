---
description: "Task list for English Resume Generator implementation"
---

# Tasks: English Resume Generator

**Input**: Design documents from `/specs/005-english-resume/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml), [quickstart.md](./quickstart.md)

**Tests**: Included. Every document task asserts on text extracted back out of
the generated PDF rather than on bytes. It is stated per task and not only
here, because the note at the top of a file is the one nobody reads.

**Organization**: Grouped by user story so each can be implemented and tested
independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths are given in every task

## What is different about this feature

**It changes the schema and it calls a model**, and neither was true of the two
document features before it. Two consequences shape the order below.

**Phases 2 and 3 have no external dependency and come first.** The migration,
the translation module and the provider operation can all be built while
feature 004's Phase 2 and issues #65 and #66 are still open. Only the renderer
waits.

**Phase 3 turns the suite red on purpose.** Adding `draft_translation` to the
`AIProvider` protocol breaks conformance for both providers until each
implements it, and feature 002's tests assert conformance. A red suite between
T014 and T017 is the intended state, not a mistake to revert.

## Blocked on work outside this feature

| Needs | From | Blocked until |
|---|---|---|
| `app/documents/typography.py` | feature 004 Phase 2 | #66 lands, then 004 T003–T008 |
| The readiness report's shape | the 履歴書's own report | #65 lands |

Phases 1–3 and the whole of US2's storage are unaffected. **T026 is the first
task that cannot start**, and the table above is why.

---

## Phase 1: Setup

**Purpose**: Nothing to install. This feature reuses what features 003 and 004
brought in.

- [ ] T001 Confirm reportlab, pypdf and the embedded font are already runtime dependencies in `apps/api/pyproject.toml`, and record in the PR that this feature adds none
- [ ] T002 Create `apps/api/app/translations/__init__.py` and `apps/api/app/resume/__init__.py`

---

## Phase 2: Foundational — storage for an approved English version

**Purpose**: FR-017 needs somewhere to put approved English, and Principle I
puts it on the profile. One migration (constitution gate G11).

**No external dependency.** This phase can be built immediately.

- [ ] T003 Create `apps/api/app/translations/models.py` with `EntryTranslation` (`Entity`, `ProfileOwned`) carrying `entry_type`, `entry_id`, `field`, `language`, `approved_text`, `approved_at`, `source_fingerprint`, per data-model.md
- [ ] T004 [P] Add the `TranslatableEntry` enum (`work_experience`, `education`, `career_story`, `skill`) to `apps/api/app/translations/models.py` — **not** `certification`, which has only proper nouns (research.md R-002)
- [ ] T005 [P] Add the `NamedEntry` enum (`work_experience`, `education`, `certification`) to `apps/api/app/translations/models.py`, separate from `TranslatableEntry` because a supplied name and an approved rendering are different kinds of fact
- [ ] T006 Add `employer_name_english` to `WorkExperience`, `institution_english` to `Education`, and `name_english` and `issuer_english` to `Certification` in `apps/api/app/career/models.py`, all nullable with no default
- [ ] T007 Generate one Alembic migration in `apps/api/migrations/versions/` creating `entry_translation` with its unique constraint on `(profile_id, entry_type, entry_id, field, language)` and its `(profile_id, language)` index, plus the four columns from T006. No backfill — a guessed English name is the transliteration FR-021 forbids
- [ ] T008 Run `alembic upgrade head`, then `downgrade -1`, then `upgrade head` again against a real database for the migration in `apps/api/migrations/versions/`, confirming the schema returns to the same state each time — a downgrade nobody runs is a downgrade that does not work
- [ ] T009 [P] Create `apps/api/app/translations/fingerprint.py` with a digest of a source string, stable across processes — a salted or address-based hash would mark every approval stale on restart
- [ ] T010 [P] Unit tests in `apps/api/tests/unit/test_fingerprint.py` — the same text digests the same twice, different text differs, and whitespace-only changes are **not** treated as equal, since a user may have fixed spacing deliberately
- [ ] T011 Add `employer_name_english`, `institution_english`, `name_english` and `issuer_english` to `WorkExperienceIn/Out`, `EducationIn/Out` and `CertificationIn/Out` in `apps/api/app/career/schemas.py`, all optional
- [ ] T012 Document the same four properties on `specs/001-master-career-profile/contracts/openapi.yaml`. They are profile fields set through the existing section routes — a route of this feature's own would be a second way to edit an entry, which Principle I rules out
- [ ] T013 Regenerate the typed client (`pnpm gen:api`) and commit `packages/api-client/src/`; CI fails on a stale client

**Checkpoint**: an approved English version has somewhere to live, and an
organisation has somewhere to carry its English name.

---

## Phase 3: Foundational — the model boundary gains one operation

**Purpose**: US2 needs a drafted translation. Constitution gate G12 requires it
go through the single `AIProvider` abstraction, not beside it.

**⚠️ The suite is red from T015 until T017 completes.** The protocol is
`runtime_checkable` and feature 002 asserts conformance, so both providers stop
satisfying it the moment the method is added. That is the order working.

- [ ] T014 [P] Add `TranslationDraft` and `RenderingAlternative` to `apps/api/app/ai/schemas.py` — `text`, `source_text` and `alternatives`, and **no field for a summary, a seniority or an outcome**, so a provider cannot return an embellishment through the schema (plan.md G13)
- [ ] T015 Add `draft_translation(text, source_language, target_language) -> TranslationDraft` to the `AIProvider` protocol in `apps/api/app/ai/provider.py`, with a docstring saying why a second operation does not breach "one operation, deliberately" — it is still given text and nothing else (research.md R-003)
- [ ] T016 [P] Implement `draft_translation` on `FakeAIProvider` in `apps/api/app/ai/fake.py`, including behaviours for a confident rendering, a rendering with alternatives, unavailability and an unusable response
- [ ] T017 Implement `draft_translation` on `OpenAIProvider` in `apps/api/app/ai/openai_provider.py`, requesting structured output against the `TranslationDraft` schema, with a prompt that asks for a rendering of the given text and nothing beyond it
- [ ] T018 Run feature 002's provider conformance tests in `apps/api/tests/unit/test_ai_boundary.py` and confirm they pass again — the red introduced at T015 is now resolved
- [ ] T019 [P] Confirm the G12 AST walker still passes: nothing under `app/translations/` or `app/resume/` imports `openai_provider`, and `app/resume/` imports nothing from `app.ai` at all
- [ ] T020 [P] Unit tests in `apps/api/tests/unit/test_translation_drafts.py` for each fake behaviour, including that a draft carrying alternatives names at least two options per phrase

**Checkpoint**: a draft can be produced. Nothing stores one yet, and nothing
renders one.

---

## Phase 4: User Story 1 — Turn my profile into an English resume (Priority: P1) 🎯 MVP

**Goal**: A profile becomes a resume a user could send today.

**Independent test**: record two employers and generate. Both appear newest
first, dates are Western, and nothing appears the profile does not hold.

**⚠️ T026 onward needs `app/documents/typography.py`** — see *Blocked on work
outside this feature*. T021–T025 do not.

### Tests for User Story 1

- [ ] T021 [P] [US1] Unit tests for the projection in `apps/api/tests/unit/test_resume_sections.py` — reverse-chronological order, an ongoing role, an employer with no description, and **that the frozen dataclasses have no attribute for a date of birth, an address or any `JapanProfile` field** (data-model.md)
- [ ] T022 [P] [US1] Unit tests for Western date formatting in `apps/api/tests/unit/test_resume_dates.py` — `Mar 2021 – Present`, month precision, and that no era name can appear in any output
- [ ] T023 [P] [US1] Integration test for quickstart Scenario 0 in `apps/api/tests/integration/test_resume_font.py`, asserting `/FontFile2` is present and an employer recorded only as 株式会社サンプル is extractable as that text — the check a page of hollow boxes fails
- [ ] T024 [P] [US1] Integration tests for quickstart Scenarios 1, 2 and 13 in `apps/api/tests/integration/test_resume_generate.py`, asserting from text extracted with pypdf that name, email and telephone appear, both employers appear newest first with title and period, education and skills appear, a snapshot id is returned, and a profile with no certifications produces **no certifications heading** (FR-011)
- [ ] T025 [P] [US1] Integration tests for quickstart Scenarios 3 and 4 in `apps/api/tests/integration/test_resume_generate.py` — periods read `Mar 2021 – Present`, none of 令和/平成/昭和 appears anywhere in the extracted text, and a profile with no career history is refused 422 naming what is missing

### Implementation for User Story 1

- [ ] T026 [US1] Create `apps/api/app/documents/dates.py` with the Western formatter. It imports nothing from `app/imports/dates.py`: the guarantee that no era can leak into this document is that the module holding the era table is not reachable from this one (research.md R-006)
- [ ] T027 [US1] Create `apps/api/app/resume/sections.py` projecting the profile into frozen dataclasses — `Contact`, `ExperienceEntry`, `EducationEntry`, `SkillEntry`, `CertificationEntry` — each carrying its `source_entry_id` (FR-014). The dataclasses define no field for a date of birth, an address, a photograph or anything from `JapanProfile`, which is how FR-009 and FR-010 hold structurally rather than by filtering
- [ ] T028 [US1] Resolve each displayed string in `apps/api/app/resume/sections.py`: an employer's `employer_name_english` where supplied and `employer_name` otherwise, and an approved `EntryTranslation` for a translatable field where one exists and the recorded text otherwise. **No provider call** — a missing English version renders as recorded and is reported by readiness (FR-017)
- [ ] T029 [US1] Create `apps/api/app/resume/render.py` laying out a US-style resume from the dataclasses, importing the font and page machinery from `app/documents/typography.py` and the formatter from `app/documents/dates.py`
- [ ] T030 [US1] Omit any section whose dataclass list is empty in `apps/api/app/resume/render.py` — absent, not a heading with nothing under it (FR-011)
- [ ] T031 [US1] Let the document run to further pages rather than dropping or truncating entries in `apps/api/app/resume/render.py`, and return the page count (FR-007). Shortening is the user's choice through `include_skills`, never the renderer's
- [ ] T032 [US1] Create `apps/api/app/resume/schemas.py` with `ResumeRequest` and `PaperSize` (`letter` default, `a4` offered) per the contract
- [ ] T033 [US1] Create `apps/api/app/resume/service.py` generating the document and capturing one `EntrySnapshot` with `document_ref="english-resume"` in the same transaction, `captured_entry_ids` led by the identity, and a payload holding the approved English actually used (research.md R-010)
- [ ] T034 [US1] Refuse generation with 422 naming what is missing when the profile has no name or no career history in `apps/api/app/resume/service.py` (FR-006). A missing English version is **not** a refusal here
- [ ] T035 [US1] Create `apps/api/app/resume/router.py` serving `POST /profile/documents/resume`, streaming the PDF with `Content-Disposition`, `X-Document-Pages` and `X-Snapshot-Id`, and register it in `apps/api/app/main.py`
- [ ] T036 [P] [US1] Contract tests in `apps/api/tests/contract/test_resume.py`, including that the three documented response headers reach a cross-origin caller — they are useless to a browser otherwise
- [ ] T037 [US1] Remove `/profile/documents/resume` from `DEFERRED` in `apps/api/tests/contract/test_contracts.py`
- [ ] T038 [P] [US1] Create `apps/web/app/[locale]/profile/documents/resume/page.tsx` with generate and preview, using the generated client types

**Checkpoint**: a user with an English profile has a complete, sendable resume.

---

## Phase 5: User Story 2 — Get my Japanese career into English (Priority: P2)

**Goal**: A user whose profile is Japanese is told what is missing, offered a
draft for each entry, and keeps the words they approve.

**Independent test**: record an entry in Japanese, draft, approve a corrected
version, and confirm the approved English is in the profile and appears in the
next document without being translated again.

**⚠️ T046 needs #65** — the readiness report is one mechanism, not two.

### Tests for User Story 2

- [ ] T039 [P] [US2] Integration tests for quickstart Scenarios 6 and 7 in `apps/api/tests/integration/test_translation_flow.py` — a draft is returned with its source beside it, **querying stored versions afterwards returns nothing**, and a 課長 title comes back with at least two options (the second assertion is the one that matters: the request that drafts must store nothing)
- [ ] T040 [P] [US2] Integration tests for quickstart Scenarios 8, 9 and 10 in `apps/api/tests/integration/test_translation_flow.py` — an approval is stored and reused, the user's wording appears character for character and the draft's does not, and a blank or whitespace approval is refused 422
- [ ] T041 [P] [US2] Integration test for quickstart Scenario 11 in `apps/api/tests/integration/test_translation_staleness.py` — editing the source marks the approval stale, **leaves it stored**, and does not block generation
- [ ] T042 [P] [US2] Integration test for quickstart Scenario 19 in `apps/api/tests/integration/test_translation_flow.py` — deleting an entry of each of the four translatable types leaves no orphan row. `entry_id` cannot be a foreign key across four tables, so this test is the foreign key
- [ ] T043 [P] [US2] Contract tests in `apps/api/tests/contract/test_translations.py` for all four translation routes, including 502 and 503 on the drafts route

### Implementation for User Story 2

- [ ] T044 [US2] Create `apps/api/app/translations/service.py` with approve (upsert on the natural key, storing the text exactly as given and recording the fingerprint), delete, and list with staleness computed by comparing a fresh digest against the stored one
- [ ] T045 [US2] Refuse an empty or whitespace-only approval with 422 in `apps/api/app/translations/service.py` — an approved blank is not an English version, it is an entry that vanishes from a document silently
- [ ] T046 [US2] Delete an entry's translations when the entry is deleted, in `apps/api/app/career/service.py`, for each of the four translatable types
- [ ] T047 [US2] Create `apps/api/app/translations/schemas.py` with `TranslationApproval`, `StoredTranslation`, `TranslationDraftRequest` and the draft response per the contract
- [ ] T048 [US2] Add drafting to `apps/api/app/translations/service.py`, calling `get_provider().draft_translation(...)` and returning the result **without storing it**. Map `ProviderUnavailable` to 503 and `ProviderResponseInvalid` to 502, because a user needs to know whether trying again is worth their time
- [ ] T049 [US2] Create `apps/api/app/translations/router.py` serving `GET`/`PUT /profile/translations`, `DELETE /profile/translations/{translation_id}` and `POST /profile/translations/drafts`, and register it in `apps/api/app/main.py`
- [ ] T050 [US2] Create `apps/api/app/resume/readiness.py` reporting `needs_english`, `untranslated_names` and `stale_translations`, reusing the shape #65 establishes for the 履歴書 rather than writing a third one
- [ ] T051 [US2] Serve `GET /profile/documents/resume/readiness` from `apps/api/app/resume/router.py` (FR-020 — before a document is produced, not after)
- [ ] T052 [US2] Remove the four translation and readiness paths from `DEFERRED` in `apps/api/tests/contract/test_contracts.py` and their four entries from `UNVALIDATED` in `apps/api/tests/contract/test_response_schemas.py`
- [ ] T053 [P] [US2] Create `apps/web/app/[locale]/profile/translations/page.tsx` and `apps/web/components/profile/translation-review.tsx` showing the source beside the draft, the alternatives as choices, and an editable field — the user must be able to compare, not just accept
- [ ] T054 [P] [US2] Add the English and Japanese interface strings for the translation review to `apps/web/messages/`; `pnpm --filter web check:messages` fails on a gap

**Checkpoint**: a user whose profile is Japanese can produce a readable resume,
and never translates the same entry twice.

---

## Phase 6: User Story 3 — Leave out what does not belong (Priority: P3)

**Goal**: A user is protected from the 履歴書's conventions without having to
know what they are.

**Independent test**: populate every personal field the profile can hold,
generate, and confirm none appears.

Most of this story is already structural after T027 — the dataclasses have
nowhere to put these fields. These tasks prove it and keep it true.

- [ ] T055 [P] [US3] Integration test for quickstart Scenario 12 in `apps/api/tests/integration/test_resume_excludes_personal.py` — populate the date of birth, the full address and **every `JapanProfile` field with every disclosure flag set to `true`**, generate, and assert from extracted text that none of them, no age derived from the date of birth, and no 写真貼付欄 appears
- [ ] T056 [P] [US3] Add a test to `apps/api/tests/unit/test_resume_sections.py` asserting the projection issues no query against `japan_profile`, so the exclusion is by never fetching rather than by filtering after
- [ ] T057 [US3] Confirm `apps/api/app/resume/sections.py` reads only `full_name_latin`, `email` and `phone` from `Identity`, and add a comment naming FR-009 beside the field list so a later addition is a visible diff

---

## Phase 7: User Story 4 — Say only what I have said (Priority: P4)

**Goal**: The constitutional constraint, made testable.

**Independent test**: record an employer with a title and dates and nothing
else, generate, and confirm the document says exactly that much.

- [ ] T058 [P] [US4] Integration test for quickstart Scenario 14 in `apps/api/tests/integration/test_resume_truthfulness.py` — an employer with no description appears with title and period and nothing else, with no invented summary and no adjective characterising the applicant
- [ ] T059 [P] [US4] Integration test for quickstart Scenario 18 in `apps/api/tests/integration/test_resume_truthfulness.py` — with a provider that raises on every call, a resume still generates. The strongest available proof that the render path cannot reach a model (FR-017)
- [ ] T060 [P] [US4] Integration test for quickstart Scenario 15 in `apps/api/tests/integration/test_document_agreement.py` — generate a 履歴書 and an English resume from one profile and assert they carry the **same employers over the same periods**. Compared as entries and periods, never as strings: the Japanese document says 課長 and the English one says the user's approved wording, and that is the product working (research.md R-008)
- [ ] T061 [P] [US4] Integration test for quickstart Scenario 16 in `apps/api/tests/integration/test_resume_traceability.py` — a snapshot still shows the English the document carried after the underlying entry is edited
- [ ] T062 [P] [US4] Integration test for quickstart Scenario 20 in `apps/api/tests/integration/test_resume_traceability.py` — no column in `Base.metadata` could hold a generated document (FR-005), asserted against the schema rather than a count of rows
- [ ] T063 [P] [US4] Integration test for quickstart Scenario 17 in `apps/api/tests/integration/test_resume_proper_nouns.py` — an employer recorded only in Japanese and a certification issuer recorded only in Japanese both appear exactly as recorded, a supplied `employer_name_english` is used, both are named under `untranslated_names`, and **requesting a draft for a certification is refused** because it is not a translatable entry type

---

## Phase 8: Polish & cross-cutting

- [ ] T064 Confirm `DEFERRED` in `apps/api/tests/contract/test_contracts.py` and `UNVALIDATED` in `apps/api/tests/contract/test_response_schemas.py` hold no remaining `005-english-resume` entry, and that the coverage test passes with every documented 2xx JSON response actually validated
- [ ] T065 [P] Run every scenario in `specs/005-english-resume/quickstart.md` end to end and record the result in the pull request
- [ ] T066 Verify each new test under `apps/api/tests/` can fail: reintroduce the bug it guards, watch it go red, restore. A test that has never failed has not been shown to test anything

---

## Requirement coverage

Built before implementation starts, not after. `/speckit-analyze` on feature
004 found a requirement with zero task coverage after fifty-three tasks had
been written, and the cheapest place to find the next one is here.

| Requirement | Tasks |
|---|---|
| FR-001 produce from the profile | T024, T027, T035 |
| FR-002 reverse-chronological | T021, T024 |
| FR-003 name, contact, experience, education, skills, certifications | T024, T027 |
| FR-004 Western dates, no era | T022, T025, T026 |
| FR-005 not retained | T062 |
| FR-006 refuse with no history | T025, T034 |
| FR-007 no truncation | T031 |
| FR-008 no photograph | T055 |
| FR-009 no personal characteristics | T021, T055, T057 |
| FR-010 no Japan-specific, even disclosed | T021, T055, T056 |
| FR-011 empty section absent | T024, T030 |
| FR-012 no unsupported claims | T058 |
| FR-013 approved English claims no more | T014, T020, T039 |
| FR-014 every statement traceable | T027 |
| FR-015 record what it drew on | T033, T061 |
| FR-016 agrees with the 履歴書 | T060 |
| FR-017 stored English, no model at generation | T003, T028, T059 |
| FR-018 draft offered, never placed unapproved | T039, T048 |
| FR-019 approved wording used exactly | T040, T044 |
| FR-020 told before generating | T050, T051 |
| FR-021 supplied name or as recorded, never guessed | T006, T023, T028, T063 |
| FR-022 US-style convention | T029, T032 |
| SC-001 no re-entry | T024 |
| SC-002 zero personal fields | T055 |
| SC-003 no era anywhere | T025 |
| SC-004 nothing unattributable | T027 |
| SC-005 unfilled section produces nothing | T024, T030 |
| SC-006 no increase in claimed seniority | T020, T039 |
| SC-007 two documents agree | T060 |
| SC-008 snapshot survives edits | T061 |
| SC-009 never handed an unreadable document | T050, T051 |
| SC-010 no unapproved draft reaches a document | T039, T048 |
| SC-011 approved wording character for character | T040 |
| SC-012 approving once is enough | T040 |
| SC-013 no proper noun the user did not supply | T063 |

All 22 functional requirements and all 13 success criteria have at least one
task. Two are worth naming because they are held by shape rather than by a
check: **FR-009 and FR-010** are satisfied at T027, where the dataclasses are
defined without a field that could hold the data. T055 and T056 prove it rather
than create it.

### The other direction

Twenty-three tasks map to no numbered requirement. Checking that way round is
worth the minute it takes, because a task with no reason to exist is as much a
defect as a requirement with no task — and one group below turned out not to be
scaffolding at all.

- **Infrastructure and delivery** — T001, T002, T007, T008, T011, T012, T013,
  T036, T037, T038, T043, T047, T049, T052, T053, T054, T064, T065. Routers,
  schemas, migrations, the web pages, the contract bookkeeping.
- **Constitution gates, not requirements** — T019 (G12: no provider SDK in
  feature code).
- **Spec edge cases that were never given FR numbers** — T041 (an approval goes
  stale when its source is edited), T042 and T046 (deleting an entry takes its
  translations with it), T045 (an approved blank is not an English version).

That last group is the useful finding. Three real behaviours, each with a test
and an implementation task, sit in the spec's *Edge Cases* prose and in
research.md R-009 rather than in a numbered requirement — so nothing that
counts requirements would ever report them missing. They are listed here so
that deleting one is a decision rather than an accident. Promoting them to
numbered requirements is a change to spec.md and belongs in its own issue, not
in a task list.

---

## Dependencies & execution order

### Phase dependencies

- **Phase 1 Setup** — no dependencies
- **Phase 2 Storage** — after Setup. No external dependency; start here
- **Phase 3 Model boundary** — after Setup. Independent of Phase 2, can run beside it
- **Phase 4 US1** — T021–T025 after Phase 2. **T026 onward also needs 004 Phase 2 (#66)**
- **Phase 5 US2** — after Phases 2, 3 and 4. **T050 also needs #65**
- **Phase 6 US3** — after T027. Mostly proves what Phase 4 built
- **Phase 7 US4** — after Phases 4 and 5; T060 also needs the 履歴書 generator, which ships
- **Phase 8 Polish** — after every story

### Within Phase 3

T015 breaks provider conformance; T016 and T017 restore it. T018 is the
checkpoint that says so. Do not reorder T015 after T016 to keep the suite green
— the protocol is the contract, and writing an implementation against a
protocol that does not yet require it is how the two drift.

### Parallel opportunities

- T004, T005 — different enums, same new file, so sequential with T003 but trivial
- T009, T010 — fingerprint and its tests, independent of the migration
- Phase 3's T014, T016 and T020 are independent of Phase 2 entirely
- T021–T025 are five independent test files
- T055, T056 and every task in Phase 7 are independent of each other

### Suggested MVP

Phases 1, 2 and 4. That is a working English resume for a user whose profile is
already in English — which is a real user, not a stepping stone. US2 is what
makes it useful to the majority whose profile is Japanese, and it is the larger
half of the feature.

---

## Notes

- `[P]` means a different file and no dependency on an incomplete task
- Commit after each task or logical group
- Every document assertion extracts text with pypdf; a PDF of hollow boxes is
  the right size and passes any check on bytes
- T066 is not optional. A test that has never been seen to fail is a comment
