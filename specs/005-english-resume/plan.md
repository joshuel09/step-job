# Implementation Plan: English Resume Generator

**Branch**: `95-plan-english-resume` | **Date**: 2026-10-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-english-resume/spec.md`

## Summary

Produce a US-style English resume from the Master Career Profile — name and
contact details, experience newest first, then education, skills and
certifications — carrying none of the personal details a 履歴書 requires.

Two things make this feature unlike the two document features before it.

**It changes the schema.** FR-017 requires an English version stored per entry,
and Principle I puts that on the profile rather than inside the generator. One
new table and four new columns, in one migration.

**It calls a model.** Not while generating — generation stays deterministic and
reads only English the user approved — but to draft a translation the user then
confirms, edits or discards. That is the thinnest part of Principle IV in the
whole product, and the design answer is to make the generator structurally
incapable of reaching a provider, and to make the drafter return the ambiguity
rather than resolve it.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: FastAPI (pinned `>=0.115,<0.116`), SQLAlchemy 2.0,
Alembic, reportlab, pypdf (tests)

**Storage**: PostgreSQL. One new table (`entry_translation`), four new nullable
columns on existing entities, one row written to `entry_snapshot` per document.

**Testing**: pytest. Document assertions extract text with pypdf rather than
comparing bytes.

**Target Platform**: Linux server; the document is streamed to a browser.

**Project Type**: Web application — FastAPI API, Next.js web app, both in the
existing monorepo.

**Performance Goals**: A document generated within one request, no worker
handoff — it performs no model call, so it is the same order as the 履歴書.
Drafting a translation is a single synchronous model call on one field, and is
a separate request for that reason.

**Constraints**: Generation and snapshot capture share one transaction.
Nothing is retained server-side. Generation must succeed with every provider
call failing (quickstart Scenario 18).

**Scale/Scope**: One new API module, five routes, one new table, two web pages.
Larger than feature 004 by the translation surface, which is most of it.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Gate derived from the constitution | Pre-Phase 0 | Post-Phase 1 |
|---|---|---|---|
| G1 | **I.** The document derives from the profile; nothing is asked for twice | PASS | PASS — an approved translation is saved to the profile and reused by every later document (SC-012); nothing is re-translated |
| G2 | **I / FR-009 of 001.** One authored source language per entry; nothing translated behind the user | **Needs design** — this feature translates | **PASS.** An entry keeps its `source_language` unchanged. The English is a *second authored version*, authored by the user when they approve it. Nothing is translated into a document without that approval (R-003, FR-018) |
| G3 | **IV / FR-010 of 001.** Every entry individually addressable | PASS | PASS — every rendered line carries its `source_entry_id`; every stored translation names the entry and field it renders |
| G4 | **IV / FR-028 of 001.** Generated claims stay traceable after their entries change | PASS | PASS — snapshot captured in the render's transaction, and its payload holds the approved English actually used, not only entry ids (R-010) |
| G5 | **V / FR-006 of 001.** Sensitive Japan-specific fields withheld unless opted in | PASS | **PASS — by exclusion, twice over.** The projection never fetches `JapanProfile`, and the dataclasses the renderer receives have no attribute that could hold one. FR-010 goes further than the gate: these fields stay out *even when disclosed* |
| G6 | **V / FR-018 of 001.** Proposals invisible until accepted | **Applicable** — a draft is a proposal | **PASS.** A draft is returned in one response and stored nowhere. There is no `translation_draft` table, so "unapproved text in a document" is not a state the schema can represent (SC-010) |
| G7 | **§2.** Business logic in the API, not the web app | PASS | PASS — projection, ordering, readiness and staleness are API-side |
| G8 | **§2.** API types generated from OpenAPI | PASS | PASS — a fifth contract joins the existing generation |
| G9 | **§2.** Typed enumerations rather than free-text state | PASS | PASS — `TranslatableEntry`, `NamedEntry`, `Locale` and `PaperSize` are enums. The first two are separate on purpose: a rendering and a supplied name are different kinds of fact (R-002) |
| G10 | **§2.** Modular monolith; no new service | PASS | PASS |
| G11 | **§2 / workflow.** Schema changes ship with a migration | **Applicable** — first document feature to change the schema | **PASS** — one Alembic migration: one table, four columns, one unique constraint, two indexes (data-model.md) |
| G12 | **§2.** All model access behind the abstraction; no provider SDK in feature code | **Applicable** — first feature since 002 to call a model | **PASS.** The new operation is added to the `AIProvider` protocol, not beside it. `app/translations/` imports `app.ai` and nothing else; the AST walker from feature 002 fails the build on any import of `openai_provider` outside `app/ai/` |
| G13 | **§2 quality gate.** Prompt or schema changes must state how Principle IV holds | **Applicable** | **PASS — argued below, not asserted** |
| G14 | **§3.** Secrets not committed | PASS | PASS — no new configuration; the existing `ai_provider` setting selects the provider |
| G15 | **II / III.** Application event sourcing and next-action computation | Not applicable | Not applicable |

No gate fails. **Complexity Tracking is empty.**

### G13 — how Principle IV holds for the translation step

The constitution permits this: *"Rewriting, translating and reformatting
verified facts is permitted; introducing scope, seniority, duration, headcount
or outcomes that the profile does not support is not."* Permitted is not the
same as safe, and translation is where the line is thinnest, so the argument is
written out rather than cited.

**Four structural guarantees, in the order they bite:**

1. **A model's words cannot reach a document.** Generation reads
   `entry_translation` and nothing else. There is no code path from the render
   to a provider, and quickstart Scenario 18 proves it by making every provider
   call raise and watching a document generate anyway. This is not a rule the
   implementation follows; it is a shape it has.

2. **A draft is not stored.** `POST /profile/translations/drafts` returns a
   draft and writes nothing. An unapproved translation has nowhere to live, so
   "a draft leaked into a document" is not a bug that can be introduced by
   forgetting a status check — there is no status to check.

3. **Approval is authorship.** The user's text is stored exactly as submitted
   (FR-019), whether they wrote it, edited a draft, or accepted one unchanged.
   The product does not record which, because after approval it makes no
   difference to who is accountable for the words: the person sending the
   document.

4. **The ambiguity is returned, not resolved.** 課長 renders as "Manager",
   "Section Chief" or "Department Head", and those are three different claims
   about seniority. A single confident draft would make the product's word
   choice into a claim about the user's career. `TranslationDraft.alternatives`
   hands that choice back to the person who knows the answer (R-004), which is
   what makes FR-013 and SC-006 something the interface serves rather than
   hopes for.

**What is not claimed.** No mechanical check can verify that approved English
does not overstate the original — the question is semantic, and the only party
who can answer it is the user. The design does not pretend otherwise. It makes
the user's judgement *required* rather than *assumed*, and surfaces the places
where judgement is actually needed. That is a weaker guarantee than feature
002's source-quote verifier, and it is the strongest one available here. Saying
so is part of satisfying this gate.

**Prompt changes.** The drafting prompt instructs a rendering of the given text
and nothing beyond it, and the structured output schema has no field for
anything but the rendering and its alternatives — there is no `summary`, no
`seniority`, no `achievements`. A provider cannot return an embellishment
through this schema, only through the rendering itself, where the user sees it
beside the source (`TranslationDraft.source_text`).

## Project Structure

### Documentation (this feature)

```text
specs/005-english-resume/
├── plan.md              # This file
├── research.md          # Phase 0 — 10 decisions
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1 — 21 scenarios
├── contracts/
│   └── openapi.yaml     # Phase 1 — 5 paths, 13 schemas
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md             # Phase 2 — /speckit-tasks, not this command
```

### Source code

```text
apps/api/app/
├── ai/
│   ├── provider.py             # + draft_translation on the protocol
│   ├── schemas.py              # + TranslationDraft, RenderingAlternative
│   ├── fake.py                 # + the fake's drafting behaviours
│   └── openai_provider.py      # + the real implementation
├── documents/                  # created by feature 004 Phase 2
│   ├── typography.py           # font, page sizes, Page — reused as-is
│   └── dates.py                # NEW — Western formatting beside the era table
├── translations/               # NEW — a profile concern, not a resume one
│   ├── models.py               # EntryTranslation
│   ├── fingerprint.py          # digest of a source text
│   ├── service.py              # approve, delete, draft, staleness
│   ├── schemas.py
│   └── router.py
├── career/
│   └── models.py               # + four English-name columns
└── resume/                     # NEW
    ├── sections.py             # the projection: entries -> frozen dataclasses
    ├── render.py               # layout
    ├── readiness.py            # the readiness report
    ├── schemas.py
    ├── service.py              # generation + snapshot capture
    └── router.py

apps/api/migrations/versions/
└── <rev>_entry_translation_and_english_names.py   # NEW

apps/api/tests/
├── contract/test_resume.py, test_translations.py
├── integration/test_resume_*.py, test_translation_flow.py,
│              test_document_agreement.py
└── unit/test_resume_sections.py, test_dates.py, test_fingerprint.py

apps/web/
├── app/[locale]/profile/documents/resume/page.tsx
├── app/[locale]/profile/translations/page.tsx
└── components/profile/translation-review.tsx
```

**Structure Decision**: translation lives in its own `app/translations/`
module, not inside `app/resume/`.

It is a profile concern. The English version of an entry belongs to the entry,
not to the document that first needed it — Principle I says so, and the
practical test is that the 職務経歴書 and the platform profile generator will
both want it. Putting it under `app/resume/` would mean feature 006 importing
another document feature's internals, which is exactly the coupling feature
004's `app/documents/` extraction was created to undo.

It also keeps the model boundary visible: `app/resume/` imports no provider and
never will, and that is apparent from the directory listing rather than from
reading the code.

## Sequencing

Two dependencies outside this feature. Neither blocks planning; both constrain
the order tasks run in, and both belong in the task list rather than being
discovered during implementation.

**1. `app/documents/typography.py` must exist** (research.md R-007). This
document embeds the CJK font, because an employer with no supplied English name
renders in Japanese. That module is created by **feature 004's Phase 2**, which
extracts it from `app/rirekisho/render.py`, and that phase waits on Michelle's
open **#66** — page-overflow work on the same `_Page` class the extraction
moves.

Until it lands, `app/resume/render.py` has nothing to import. The alternative —
importing from `app/rirekisho/` — is the coupling 004's plan already rejected,
and doing it temporarily would mean doing the extraction twice.

**2. The readiness report is one mechanism, not two.** US2-1 and FR-020 need
"tell me what is missing before generating", which is the same question
Michelle's open **#65** answers for the 履歴書 and feature 004 answers for the
職務経歴書. Three features asking it means it belongs beside them in
`app/documents/`, generalised once rather than written a third time.

This plan deliberately does **not** pre-empt that generalisation: #65 is open
and unmerged, and designing against unwritten code is how two mechanisms get
built. The task list should sequence 005's readiness after #65 lands and reuse
its shape, and `app/resume/readiness.py` in the tree above is where that reuse
lands, not a third implementation.

**Implementation order**: #66 → feature 004 Phase 2 → #65 → this feature's
Phase 1. Everything before `app/resume/render.py` — the migration, the
translation module, the provider operation — has no such dependency and can be
built first.

## Phase 0 and Phase 1 outputs

| Artefact | Status |
|---|---|
| [research.md](./research.md) | 10 decisions, no unknowns remaining |
| [data-model.md](./data-model.md) | 1 new table, 4 new columns, 1 migration; reads 5 entities, never `JapanProfile` |
| [contracts/openapi.yaml](./contracts/openapi.yaml) | 5 routes, 14 schemas |
| [quickstart.md](./quickstart.md) | 21 scenarios |

## Consequences for existing code

Adding a contract is not inert, and this one changes more than feature 004's
did. All of it belongs in the first tasks rather than being found later:

1. **`tests/contract/test_contracts.py`** discovers contracts by glob, so all
   five new paths must be listed in `DEFERRED` until they are implemented, or
   the suite fails the moment this plan merges.

2. **`tests/contract/test_response_schemas.py`** iterates a **hardcoded tuple
   of four features**. A fifth contract would not be covered at all — the exact
   "silently stops checking" failure that file exists to prevent, and the
   second time it has nearly happened. It should discover features the way
   `test_contracts.py` and `generate.mjs` already do, rather than gain a fifth
   constant and wait for a sixth.

3. **`packages/api-client`** globs the same contracts and will emit
   `schema-005.ts`. CI fails if the committed client is stale, so it is
   regenerated and committed with the plan.

4. **Feature 001's contract gains four properties.** `employer_name_english`,
   `institution_english`, `name_english` and `issuer_english` are profile fields
   set through the existing section routes (data-model.md). They belong on 001's
   `WorkExperienceIn/Out`, `EducationIn/Out` and `CertificationIn/Out`, not on
   a route of this feature's own — a second way to edit an entry is what
   Principle I rules out. That edit lands with the implementation, not with
   this plan, because a documented property the API does not serve fails the
   contract suite.

5. **The `AIProvider` protocol gains a method**, so `FakeAIProvider` and
   `OpenAIProvider` both stop satisfying it until they implement it. The
   protocol is `runtime_checkable` and feature 002's tests assert conformance;
   those tests go red the moment the protocol changes and stay red until both
   providers are updated. That is the intended order, not a breakage.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No violations. The feature adds no service and no new abstraction: the model
boundary already exists and gains an operation, the snapshot machinery already
exists and gains a `document_ref` value, and the typography module is feature
004's.

The one genuinely new thing is `entry_translation`, and it is new because
FR-017 requires storage that does not exist. Research R-001 records the two
simpler shapes that were rejected and why.
