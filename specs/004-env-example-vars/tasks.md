---
description: "Task list for documenting the missing API settings in .env.example"
---

# Tasks: Document the missing API settings in .env.example

**Input**: Design documents from `/specs/004-env-example-vars/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [quickstart.md](./quickstart.md)

**Tests**: No new automated tests (research.md R-003). Verification is the
static check in quickstart.md, and the PR body records it as the constitution
requires.

**Organization**: Grouped by user story. Both stories change the same file, so
they run in sequence, not in parallel.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup

None. No dependencies, scaffolding or migrations.

## Phase 2: Foundational

- [X] T001 Confirm the defaults and formats to document: `ai_provider`, `openai_api_key` and `web_origins` in `apps/api/app/core/settings.py`, the accepted provider names in `get_provider()` in `apps/api/app/ai/__init__.py`, and comma splitting of origins in `apps/api/app/main.py`

---

## Phase 3: User Story 1 - A fresh clone runs the API against the web app (Priority: P1) 🎯 MVP

**Goal**: A copied `.env` runs the API against the web app with no edits and no network calls to an AI provider.

**Independent Test**: quickstart.md steps 1 and 4.

- [X] T002 [US1] Add `AI_PROVIDER=fake` and `OPENAI_API_KEY=` (empty) to `apps/api/.env.example`, grouped together (FR-001, FR-002, FR-008, FR-009)
- [X] T003 [US1] Add `WEB_ORIGINS=http://localhost:3000` to `apps/api/.env.example` (FR-003, FR-008)

**Checkpoint**: Copying the example to `.env` changes no behaviour, and the web app's default origin is allowed.

---

## Phase 4: User Story 2 - A developer switches to a real provider or a different web address (Priority: P2)

**Goal**: The example file alone explains how to change each setting.

**Independent Test**: quickstart.md step 2. The comments answer "what values?" and "when is this read?" without opening the code.

- [X] T004 [US2] Above `AI_PROVIDER` in `apps/api/.env.example`, add a comment naming `fake` and `openai` and saying `fake` keeps local work and CI off the network (FR-004, FR-005)
- [X] T005 [US2] Above `OPENAI_API_KEY` in `apps/api/.env.example`, add a comment saying it is only read when `AI_PROVIDER=openai` (FR-004, FR-006)
- [X] T006 [US2] Above `WEB_ORIGINS` in `apps/api/.env.example`, add a comment saying it is where the web app is served from, that a wrong value means the browser is refused, and that several addresses are separated by commas (FR-004, FR-007)

**Checkpoint**: Every added variable has a comment in the file's existing style.

---

## Phase 5: Polish & Verification

- [X] T007 Run quickstart.md steps 1–3 (defaults match, comments present, no secrets) and record the output for the PR body
- [ ] T008 Run quickstart.md step 4 (fresh `.env` copy, API + web app, no CORS errors) and record the result for the PR body — *not run end to end: no Docker, Postgres or pnpm on the implementing machine. An in-process substitute was run instead (see the PR body). Left open for the reviewer.*
- [X] T009 Run `uv run ruff check .` from the repo root to confirm nothing else changed

---

## Dependencies & Execution Order

- T001 → T002, T003 → T004–T006 → T007–T009
- US2 depends on US1: its comments sit above the lines US1 adds.
- No [P] tasks. Every change is in the same file.

## Implementation Strategy

US1 alone already unblocks a fresh clone (the MVP). US2 makes the file
self-explanatory. Both are small enough to ship as one commit and one PR.
