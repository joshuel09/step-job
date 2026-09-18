<!--
Sync Impact Report
==================
Version change: none → 1.0.0 (initial ratification)

Principles defined (all new):
  I.   Capture Once, Generate Everywhere
  II.  Zero-Input Application Tracking
  III. Always Surface the Next Step
  IV.  Truthful AI (NON-NEGOTIABLE)
  V.   User Authority Over External Actions

Sections added:
  - Core Principles
  - Architecture & Technology Constraints
  - Development Workflow & Quality Gates
  - Governance

Sections removed: none

Deferred TODOs: none. Every placeholder in the template was resolved.
-->

# Step Job Constitution

Step Job is an AI-powered career management platform for job seekers in Japan,
especially international professionals. This constitution governs how the product
is designed and built. It applies to every specification, plan, task and pull
request in this repository.

## Core Principles

### I. Capture Once, Generate Everywhere

The Master Career Profile is the single place a user describes their career.
Every generated artefact — 履歴書, 職務経歴書, English resume, platform profile,
application answer, interview material — MUST be derived from that profile.

No feature MAY ask the user to re-enter information the profile already holds. A
feature that needs a new kind of career data MUST extend the profile rather than
collect the data privately. Generated documents are outputs, never a second
source of truth: editing a document MUST NOT silently diverge it from the profile.

*Rationale:* the product's core promise is that a user explains their career once.
Every duplicate input field is a breach of that promise and a future
inconsistency between a user's documents.

### II. Zero-Input Application Tracking

Application state MUST be recorded as data, not as user bookkeeping. Every change
to an `Application` MUST emit a corresponding `ApplicationEvent`; no status may be
written without one. The event timeline is append-only and is the audit record of
what happened and when.

Where a stage can be inferred from evidence the system already holds, the system
MUST infer it rather than prompt. Manual editing remains available as a
correction, never as the primary path.

*Rationale:* a tracker that depends on diligent manual updates is abandoned within
weeks. Deriving state from events is also what makes the timeline, follow-up
detection and analytics possible later.

### III. Always Surface the Next Step

Every active `Application` MUST carry a computable `nextActionAt`. The dashboard
MUST be derivable entirely from stored data — applications, events, interviews and
deadlines — and MUST NOT depend on user-authored todo items.

If the system cannot determine a next action for an active application, that is a
modelling gap to be fixed, not a blank space to be shown to the user.

*Rationale:* job searching fails on forgotten follow-ups, not on missing features.
A next step that a user has to maintain by hand is not a next step.

### IV. Truthful AI (NON-NEGOTIABLE)

AI MAY improve the presentation of a user's experience. AI MUST NEVER invent
professional experience.

Every AI-generated claim MUST be traceable to specific entries in the Master
Career Profile, and that provenance MUST be inspectable in the interface. Where
the model produces a claim that cannot be grounded in profile data, the system
MUST surface it for explicit user confirmation and MUST NOT emit it silently.
Rewriting, translating and reformatting verified facts is permitted; introducing
scope, seniority, duration, headcount or outcomes that the profile does not
support is not.

*Rationale:* users submit these documents to real employers under their own name.
An unverifiable claim is not a quality defect, it is a professional risk borne by
the user. This principle outranks output quality and MUST NOT be traded against it.

### V. User Authority Over External Actions

No action that leaves the system MAY occur without explicit user consent for that
action. This includes submitting applications, sending messages to companies,
recruiters or agencies, and writing to any connected third-party account.

Integrations MUST default to read and draft. Any automated classification of a
user's mail or calendar MUST be visible and reversible, and the connection MUST be
revocable with the resulting data removable.

*Rationale:* the system operates on a user's professional reputation and private
correspondence. Convenience never justifies acting on someone's behalf without
their say-so.

## Architecture & Technology Constraints

**Stack.** Next.js with the App Router, TypeScript, Tailwind CSS and shadcn/ui on
the web; Python with FastAPI, Pydantic, SQLAlchemy and Alembic on the backend,
exposed as REST described by OpenAPI; PostgreSQL with pgvector as the database;
Redis with Dramatiq for background work; object storage for user documents.

*Backend language decision:* Go was evaluated and is superseded by Python. The
product's hard problems are document intelligence and structured AI extraction —
parsing 職務経歴書, understanding recruiter mail, grounding generated claims — not
raw request throughput. This decision is settled; plans MUST NOT reopen it without
a constitutional amendment.

**Business logic lives in the API.** FastAPI is the single source of business
logic. The web app renders server-first and MUST NOT reimplement domain rules that
belong behind the API. API types MUST be generated from the OpenAPI definition
rather than maintained by hand in two places.

**PostgreSQL is the source of truth.** A modular monolith is the target
architecture; microservices are out of scope. Introducing a dedicated vector
database is prohibited while pgvector is sufficient.

**The domain model is explicit.** These distinctions MUST be preserved in schema
and in code:

- `Company`, `Job` and `Application` are separate entities and MUST NOT be collapsed.
- `RecruitmentAgency` and `Recruiter` are separate entities; an application may
  have either, both or neither.
- `Application.status` MUST be a typed enumeration, never a free-text string.
- Interviews MUST be separate records carrying type and round. Interview stages
  MUST NOT be encoded as additional application statuses.
- Recruitment sources MUST be modelled as data, not hardcoded.

**AI is provider-independent and structured.** All model access MUST go through a
single `AIProvider` abstraction; no provider SDK may be called directly from
feature code. AI calls MUST request structured output against an explicit schema
rather than free text. AI MUST NOT hold database credentials or issue writes: it
proposes structured data, and deterministic application code validates and
persists it. Deterministic logic and model calls MUST remain separable and
separately testable.

**Release scope.** The first release is the eight-item cut: Master Career Profile;
AI resume import; 履歴書 generator; 職務経歴書 generator; English resume generator;
platform copy-paste profile generator; job import with personalized application
answers; interview preparation with the application tracker. The twenty-two STEP
modules are the module inventory, not the first release. Mail and calendar
synchronisation, job aggregation, auto-apply, browser extensions and voice
interview practice are explicitly deferred to later phases.

## Development Workflow & Quality Gates

**Specification precedes implementation.** Work follows the spec-driven cycle:
constitution → specify → plan → tasks → implement. Implementation MUST NOT begin
before a written specification exists for the feature.

**Every change is tracked.** Each unit of work MUST have a tracking issue on the
project board before work starts, a branch named for that issue, and a pull
request that references the issue with `Closes #N`. Board status MUST reflect
reality: in progress while the branch is active, in review once the pull request
is open.

**Every pull request is verified before merge.** The project's checks MUST pass.
Where no automated suite yet covers the change, the static verification actually
performed MUST be recorded in the pull request body. Claiming that a suite passed
when none exists is prohibited. A failing or unrun check blocks the merge.

**Quality gates.** Secrets MUST NOT be committed. Database schema changes MUST ship
with an Alembic migration. Changes to AI prompts or output schemas MUST state how
Principle IV remains satisfied.

## Governance

This constitution supersedes other practices and conventions in this repository.
Where a plan, specification or review conflicts with it, this document wins.

**Amendment procedure.** Amendments MUST be proposed in a pull request that
changes this file, states the rationale, and updates the version and the Sync
Impact Report at the top. An amendment that weakens Principle IV MUST say so
explicitly in its rationale.

**Versioning policy.** This document is versioned with semantic versioning:

- MAJOR — a principle is removed or redefined in a backward-incompatible way.
- MINOR — a principle or section is added, or guidance is materially expanded.
- PATCH — clarifications, wording and typo fixes that do not change meaning.

**Compliance review.** Every pull request MUST be checked against these
principles. Complexity that appears to violate a constraint MUST be justified in
the pull request, or the change MUST be simplified. Specifications and plans that
contradict this document MUST be corrected before implementation proceeds.

**Version**: 1.0.0 | **Ratified**: 2026-09-18 | **Last Amended**: 2026-09-18
