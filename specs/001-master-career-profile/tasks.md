---
description: "Task list for Master Career Profile implementation"
---

# Tasks: Master Career Profile

**Input**: Design documents from `/specs/001-master-career-profile/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml), [quickstart.md](./quickstart.md)

**Tests**: Test tasks are included. Constitution §3 requires that every pull
request pass the project's checks and forbids claiming a suite passed when none
exists, so an automated suite is a governance requirement rather than an optional
extra. Contract tests are grouped per resource rather than per endpoint; each
[quickstart.md](./quickstart.md) scenario becomes one integration test.

**Organization**: Tasks are grouped by user story so each story can be
implemented, tested and delivered independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are given in every task

## Path Conventions

Paths follow the monorepo established in [plan.md](./plan.md): `apps/api/` for
business logic, `apps/web/` for the interface, `apps/worker/` for scheduled work,
`packages/` for shared configuration and the generated client.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the monorepo. This feature is the first in the repository,
so Phase 1 creates the structure every later feature extends.

- [X] T001 Create the workspace root with `pnpm-workspace.yaml` and `package.json` declaring `apps/*` and `packages/*`
- [X] T002 [P] Add `docker-compose.yml` at the repository root with PostgreSQL and Redis services
- [X] T003 [P] Initialise the API project in `apps/api/pyproject.toml` with FastAPI, Pydantic, SQLAlchemy, Alembic and pytest
- [X] T004 [P] Initialise the worker project in `apps/worker/pyproject.toml` with Dramatiq, Redis and pytest, depending on the API package for shared models
- [X] T005 [P] Initialise the Next.js App Router project in `apps/web/package.json` with TypeScript, Tailwind, shadcn/ui, TanStack Query, React Hook Form, Zod and next-intl
- [X] T006 [P] Add shared lint, format and TypeScript configuration in `packages/config/`
- [X] T007 Add the client generation script `pnpm gen:api` in `packages/api-client/package.json`, generating from `specs/001-master-career-profile/contracts/openapi.yaml`
- [X] T008 Add the continuous integration workflow in `.github/workflows/ci.yml` running the API, worker and web suites plus a check that the generated client is up to date
- [X] T009 [P] Add `apps/api/.env.example` and `apps/web/.env.example` documenting required configuration

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Cross-story primitives. Several of these exist to make constitution
gates structurally true rather than conventions each endpoint must remember.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T010 Implement settings and environment loading in `apps/api/app/core/settings.py`
- [X] T011 Implement the verified-identity dependency in `apps/api/app/core/identity.py`, deriving the profile owner from the session and never from the request path or body, per research.md R-006
- [X] T012 [P] Implement the error shape and handlers in `apps/api/app/core/errors.py`, matching the `Error` and `ValidationError` schemas in `contracts/openapi.yaml`
- [X] T013 Implement the database session and engine in `apps/api/app/db/session.py`
- [X] T014 Implement the declarative base in `apps/api/app/db/base.py` with a UUID primary key mixin and created/updated timestamps, satisfying gate G3
- [X] T015 Implement the soft-delete query filter in `apps/api/app/db/soft_delete.py` so soft-deleted profiles are excluded from every read at the data-access layer, satisfying FR-027 and gate G6 structurally
- [X] T016 Create the `CareerProfile` model in `apps/api/app/career/models.py` with `interface_locale`, `deleted_at` and `purge_after` per data-model.md
- [X] T017 [P] Create the `EntrySnapshot` model in `apps/api/app/career/models.py` as an insert-only entity, per research.md R-001
- [X] T018 Initialise Alembic in `apps/api/migrations/` and generate the first migration covering `CareerProfile` and `EntrySnapshot`
- [X] T019 Wire the application entrypoint and router registration in `apps/api/app/main.py`
- [X] T020 [P] Create the locale-segmented routing skeleton in `apps/web/app/[locale]/layout.tsx` with next-intl, per research.md R-003
- [X] T021 [P] Create the message catalogue shells in `apps/web/messages/en.json` and `apps/web/messages/ja.json`
- [X] T022 [P] Add test fixtures providing an authenticated identity and a clean database in `apps/api/tests/conftest.py`

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Describe my career once (Priority: P1) 🎯 MVP

**Goal**: A user records their identity, work history, education, certifications,
skills, languages, preferences and Japan-specific circumstances, edits any of it
freely, and finds it unchanged when they return. They can export or delete
everything they hold.

**Independent Test**: complete a profile with at least one work experience, one
education entry, and skills and languages; sign out and back in; every value is
present and unchanged. Covers quickstart.md Scenario 1.

### Tests for User Story 1

- [X] T023 [P] [US1] Contract tests for the profile and section routes in `apps/api/tests/contract/test_profile_sections.py`, generated against `contracts/openapi.yaml`
- [X] T024 [P] [US1] Integration test for quickstart Scenario 1, recording a career and reading it back, in `apps/api/tests/integration/test_record_career.py`
- [X] T025 [P] [US1] Integration test for quickstart Scenario 5, the split deletion and restore behaviour, in `apps/api/tests/integration/test_profile_deletion.py`
- [X] T026 [P] [US1] Unit tests for date-range validation in `apps/api/tests/unit/test_validation.py`

### Implementation for User Story 1

- [X] T027 [P] [US1] Create the `Identity` model in `apps/api/app/career/models.py`, storing one name string so single-part names are valid
- [X] T028 [P] [US1] Create the `JapanProfile` model in `apps/api/app/career/models.py` with every disclosure flag defaulting to false in the schema, satisfying gate G5
- [X] T029 [P] [US1] Create the `WorkExperience` model in `apps/api/app/career/models.py` including `employer_name_normalised` and a nullable `ended_on` meaning ongoing
- [X] T030 [P] [US1] Create the `Education` and `Certification` models in `apps/api/app/career/models.py`
- [X] T031 [P] [US1] Create the `Skill` model and its many-to-many link to `WorkExperience` in `apps/api/app/career/models.py`
- [X] T032 [P] [US1] Create the `Language` model in `apps/api/app/career/models.py` with a typed proficiency enumeration, satisfying gate G9
- [X] T033 [P] [US1] Create the `CareerPreference` model in `apps/api/app/career/models.py`
- [X] T034 [US1] Add `source_language` to every content-bearing model in `apps/api/app/career/models.py`, satisfying FR-009 and gate G2
- [X] T035 [US1] Generate the Alembic migration for all User Story 1 entities in `apps/api/migrations/`
- [X] T036 [P] [US1] Define the request and response schemas in `apps/api/app/career/schemas.py`, matching `contracts/openapi.yaml`
- [X] T037 [US1] Implement date-range and salary-range validation in `apps/api/app/career/validation.py`, rejecting an end date before its start with a field-level reason per FR-014, and permitting overlapping experiences without warning
- [X] T038 [US1] Implement profile and section create, read, update and delete in `apps/api/app/career/service.py`
- [X] T039 [US1] Implement the reference warning in `apps/api/app/career/service.py`, returning what depends on an entry before deletion proceeds per FR-013
- [X] T040 [US1] Implement split deletion and restore in `apps/api/app/career/deletion.py`, hard deleting residence, nationality, visa type and visa expiry inside the same transaction and soft deleting the remainder — including career stories and any pending proposed entries — with a 30-day purge date, per research.md R-002
- [X] T041 [US1] Implement profile export in `apps/api/app/career/export.py`, producing one archive holding a complete structured file and a readable document, including Japan-specific fields regardless of disclosure settings per FR-037, retaining nothing server-side
- [X] T042 [US1] Implement the section completeness report in `apps/api/app/career/service.py` per FR-015
- [X] T043 [US1] Implement the profile and section routes in `apps/api/app/career/router.py`, including `/profile`, `/profile/completeness`, `/profile/restore`, `/profile/export` and each section resource
- [X] T044 [US1] Regenerate the typed client into `packages/api-client/` from the contract
- [ ] T045 [P] [US1] Build the profile overview page in `apps/web/app/[locale]/profile/page.tsx`
- [ ] T046 [P] [US1] Build the identity and Japan-specific section forms in `apps/web/components/profile/identity-form.tsx` and `apps/web/components/profile/japan-form.tsx`, with disclosure controls per field
- [ ] T047 [P] [US1] Build the work experience form and list in `apps/web/components/profile/experience-form.tsx`
- [ ] T048 [P] [US1] Build the education, certification, skill and language section forms in `apps/web/components/profile/`
- [ ] T048a [P] [US1] Build the career preferences form in `apps/web/components/profile/preference-form.tsx`, covering desired roles, locations, working arrangement and salary expectations per FR-004
- [ ] T048b [P] [US1] Build the interface language switcher in `apps/web/components/locale-switcher.tsx`, persisting the choice through `PATCH /profile` so it applies on every device per FR-021 and research.md R-003
- [ ] T049 [US1] Surface field-level validation messages from the API in `apps/web/components/profile/`, showing the reason rather than a generic failure
- [ ] T050 [US1] Build the deletion and export flow in `apps/web/app/[locale]/profile/settings/page.tsx`, stating what is erased immediately and when the recovery window ends per FR-026
- [ ] T051 [P] [US1] Add the English and Japanese strings for every User Story 1 screen to `apps/web/messages/en.json` and `apps/web/messages/ja.json`

**Checkpoint**: User Story 1 is fully functional and independently testable — a usable product on its own

---

## Phase 4: User Story 2 - Keep my accomplishments so I can reuse them (Priority: P2)

**Goal**: A user records accomplishments as structured stories linked to the role
where they happened, and finds them again months later.

**Independent Test**: create a story against an existing work experience, sign out
and back in, retrieve it in full with its link intact, and find it by keyword.
Covers quickstart.md Scenario 2.

### Tests for User Story 2

- [ ] T052 [P] [US2] Contract tests for the story routes in `apps/api/tests/contract/test_stories.py`
- [ ] T053 [P] [US2] Integration test for quickstart Scenario 2, storing and retrieving an accomplishment, in `apps/api/tests/integration/test_career_stories.py`

### Implementation for User Story 2

- [ ] T054 [P] [US2] Create the `CareerStory` model in `apps/api/app/career/models.py` with a nullable link to `WorkExperience`
- [ ] T055 [US2] Generate the Alembic migration for `CareerStory` in `apps/api/migrations/`
- [ ] T056 [US2] Implement story create, read, update and delete plus keyword search across title, challenge, action and result in `apps/api/app/career/stories.py`
- [ ] T057 [US2] Extend the reference warning in `apps/api/app/career/service.py` so deleting a work experience reports the stories that link to it
- [ ] T058 [US2] Include linked stories in the work experience detail response in `apps/api/app/career/router.py`
- [ ] T059 [US2] Implement the story routes in `apps/api/app/career/router.py`
- [ ] T060 [US2] Regenerate the typed client into `packages/api-client/` from the contract
- [ ] T061 [P] [US2] Build the story form and list in `apps/web/components/profile/story-form.tsx`
- [ ] T062 [P] [US2] Show linked stories alongside their work experience in `apps/web/components/profile/experience-form.tsx`
- [ ] T063 [P] [US2] Build story keyword search in `apps/web/app/[locale]/profile/stories/page.tsx`
- [ ] T064 [P] [US2] Add the English and Japanese strings for every User Story 2 screen to `apps/web/messages/en.json` and `apps/web/messages/ja.json`

**Checkpoint**: User Stories 1 and 2 both work independently

---

## Phase 5: User Story 3 - Review what was extracted before it becomes mine (Priority: P3)

**Goal**: Entries proposed by an outside source wait in a review queue. The user
edits, accepts, rejects or merges each one. Only accepted entries enter the
profile.

**Independent Test**: submit proposals from a test fixture, confirm they are
absent from every profile read, then edit and accept one and confirm the corrected
version is what lands. Covers quickstart.md Scenario 3.

### Tests for User Story 3

- [ ] T065 [P] [US3] Contract tests for the proposal routes in `apps/api/tests/contract/test_proposals.py`
- [ ] T066 [P] [US3] Integration test for quickstart Scenario 3, including the check that a pending proposal is invisible to profile reads, in `apps/api/tests/integration/test_proposal_review.py`
- [ ] T067 [P] [US3] Unit tests for duplicate matching in `apps/api/tests/unit/test_duplicates.py`, covering employer name normalisation, overlapping ranges, an ongoing role with no end date, and a non-overlapping promotion that must not match

### Implementation for User Story 3

- [ ] T068 [P] [US3] Create the `ProposedEntry` model in `apps/api/app/career/models.py` with a typed status enumeration and a recorded source, in its own table so it is never joined into profile reads
- [ ] T069 [US3] Generate the Alembic migration for `ProposedEntry` in `apps/api/migrations/`
- [ ] T070 [US3] Implement employer name normalisation and date-overlap matching in `apps/api/app/career/duplicates.py` per research.md R-004, treating a missing end date as ongoing
- [ ] T071 [US3] Implement proposal intake in `apps/api/app/career/proposals.py`, flagging possible duplicates as suggestions only
- [ ] T072 [US3] Implement accept, reject and merge in `apps/api/app/career/proposals.py`, writing the user's corrected payload rather than the original proposal content per FR-019, and rejecting a second review with a conflict since both outcomes are terminal
- [ ] T073 [US3] Implement the merge rule in `apps/api/app/career/proposals.py` so career stories follow the surviving work experience rather than being orphaned
- [ ] T074 [US3] Implement the proposal routes in `apps/api/app/career/router.py`, including accept, reject and merge
- [ ] T075 [US3] Regenerate the typed client into `packages/api-client/` from the contract
- [ ] T076 [P] [US3] Build the review queue in `apps/web/app/[locale]/profile/review/page.tsx`, showing each proposal with its source
- [ ] T077 [P] [US3] Build the proposal edit, accept, reject and merge controls in `apps/web/components/profile/proposal-review.tsx`, making "keep both" available wherever a merge is offered
- [ ] T078 [P] [US3] Add the English and Japanese strings for every User Story 3 screen to `apps/web/messages/en.json` and `apps/web/messages/ja.json`

**Checkpoint**: All three user stories are independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Work that spans stories, plus the scheduled job and the traceability
surface that later features consume.

- [ ] T079 Implement the 30-day purge actor in `apps/worker/app/purge.py`, permanently erasing profiles past their purge date together with their snapshots and any pending proposed entries, written to be idempotent so a retry is a no-op per research.md R-002
- [ ] T080 Schedule the purge actor in `apps/worker/app/main.py`
- [ ] T081 [P] Add worker tests for the purge, including the idempotency case, in `apps/worker/tests/test_purge.py`
- [ ] T082 Implement snapshot capture and read in `apps/api/app/career/snapshots.py`, insert-only and returning captured content unchanged after the source entries are edited or deleted, per FR-028 to FR-030
- [ ] T083 Implement the snapshot routes in `apps/api/app/career/router.py`
- [ ] T084 [P] Integration test for quickstart Scenario 4, proving a snapshot survives an edit of its source entry, in `apps/api/tests/integration/test_snapshot_traceability.py`
- [ ] T085 [P] Playwright test for quickstart Scenario 6, switching the interface between English and Japanese and confirming stored content is untouched, in `apps/web/tests/e2e/locale-switch.spec.ts`
- [ ] T086 Audit `apps/web/messages/ja.json` for completeness against `en.json` so no interface text is left untranslated per FR-022, and fail the build on a missing key
- [ ] T087 [P] Add structured logging across the career module in `apps/api/app/career/`
- [ ] T088 Run the full [quickstart.md](./quickstart.md) walkthrough against a fresh environment and record the result

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; start immediately
- **Foundational (Phase 2)**: depends on Setup; **blocks every user story**
- **User Stories (Phases 3 to 5)**: all depend on Foundational. They may then run
  in parallel if staffed, or sequentially in priority order
- **Polish (Phase 6)**: depends on the user stories it touches. T079 to T081 depend
  only on T040's deletion model, so the purge can be built as soon as User Story 1
  lands

### User Story Dependencies

- **User Story 1 (P1)**: depends only on Foundational. No dependency on US2 or US3
- **User Story 2 (P2)**: depends on Foundational. Links to `WorkExperience` from
  US1, so deliver after US1 unless a fixture supplies experiences. Independently
  testable either way
- **User Story 3 (P3)**: depends on Foundational. Duplicate detection compares
  against US1's `WorkExperience`, and T073 touches US2's stories, so deliver last

### Within Each User Story

- Tests are written before the implementation they cover
- Models precede services; services precede routes; routes precede the interface
- The client is regenerated after the routes change and before the interface
  consumes them
- A story is complete before the next priority starts

### Parallel Opportunities

- T002 to T006 and T009 run in parallel once T001 creates the workspace
- T012, T017, T020, T021 and T022 run in parallel within Foundational
- All four US1 test tasks (T023 to T026) run in parallel
- All seven US1 model tasks (T027 to T033) run in parallel — one file, but
  independent entities; serialise only if the team prefers to avoid merge conflicts
- Web component tasks within a story (T045 to T048, T061 to T063, T076 to T077)
  run in parallel
- Once Foundational completes, the three stories can be staffed in parallel

## Parallel Example: User Story 1

```text
# After Foundational completes, launch the four test tasks together:
T023  Contract tests for profile and section routes
T024  Integration test — record a career and read it back
T025  Integration test — split deletion and restore
T026  Unit tests — date-range validation

# Then the seven model tasks together:
T027 Identity    T028 JapanProfile   T029 WorkExperience   T030 Education/Certification
T031 Skill       T032 Language       T033 CareerPreference

# Then serially: T034 → T035 → T036 → T037 → T038 → T039 → T040 → T041 → T042 → T043 → T044

# Then the interface tasks together:
T045 Overview   T046 Identity/Japan forms   T047 Experience form   T048 Remaining sections
```

## Implementation Strategy

**MVP is User Story 1 alone.** Phases 1, 2 and 3 deliver a working product: a
structured, durable career record a user can fill in, correct, export and delete,
in either language. That is useful before a single document is generated from it,
and it is the foundation every later feature reads.

**Increment from there.** User Story 2 adds accomplishments worth reusing. User
Story 3 removes the barrier to a complete profile by accepting proposals from
outside sources — and defines the contract the separate import feature delivers
into.

**Phase 6 is not optional polish.** T079 to T081 discharge the deletion promise
made in FR-025, and T082 to T084 are what keep Principle IV's traceability true
once documents are generated from this data. Treat them as required before the
feature is considered complete, even though no user story depends on them.

**Suggested delivery order**: Phase 1 → Phase 2 → Phase 3 (ship the MVP) →
T079 to T081 → Phase 4 → Phase 5 → remaining Phase 6.
