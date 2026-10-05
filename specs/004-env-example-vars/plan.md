# Implementation Plan: Document the missing API settings in .env.example

**Branch**: `004-env-example-vars` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-env-example-vars/spec.md`

## Summary

Add `AI_PROVIDER`, `OPENAI_API_KEY` and `WEB_ORIGINS` to `apps/api/.env.example`.
Each gets a comment, and each value matches its default in
`apps/api/app/core/settings.py`. That way copying the file to `.env` changes no
behaviour, and it now names every setting a fresh clone needs to run the API
against the web app.

The change touches one file and no code. The settings already exist and already
read from the environment. The only design choices are the wording of the
comments, and which settings stay out (research.md R-001).

## Technical Context

**Language/Version**: Python 3.12 (API). Not affected; no code changes.

**Primary Dependencies**: pydantic-settings, which already loads `.env` into
`Settings`. No change.

**Storage**: N/A

**Testing**: Static verification. The example file is loaded through `Settings`
and each value compared with its code default (quickstart.md). No new automated
test (research.md R-003).

**Target Platform**: Local development (macOS/Linux) and CI. CI sets its own
environment and never reads `.env`.

**Project Type**: Web service (FastAPI API + Next.js web app in a pnpm/uv monorepo)

**Performance Goals**: N/A

**Constraints**: The example must stay secret-free. `fake` must stay the default
provider, so a copied `.env` never reaches the network (research.md R-004 of
feature 002).

**Scale/Scope**: One file, three variables

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / gate | Assessment |
|---|---|
| I. Capture Once, Generate Everywhere | Not touched. |
| II. Zero-Input Application Tracking | Not touched. |
| III. Always Surface the Next Step | Not touched. |
| IV. Truthful AI | Not weakened. The default stays `fake`, so no model call happens unless a developer opts in. No prompt or output schema changes. |
| V. User Authority Over External Actions | Not touched. |
| AI is provider-independent | Pass. Provider choice stays a setting read by the single gateway in `app/ai/__init__.py`. |
| Specification precedes implementation | Pass. spec.md exists and this plan comes before any change. |
| Every change is tracked | Pass. Issue #58 is on the board and In progress, on branch `004-env-example-vars`. The PR will say `Closes #58`. |
| Every PR is verified | Pass. No suite covers the example file, so the PR body will record the static verification actually performed. |
| Secrets MUST NOT be committed | Pass. `OPENAI_API_KEY` is left empty (FR-009). |
| Schema changes ship with a migration | N/A. No schema change. |

**Result**: Pass. Nothing to justify; Complexity Tracking is empty.

**Post-design re-check**: Unchanged. Pass.

## Project Structure

### Documentation (this feature)

```text
specs/004-env-example-vars/
├── plan.md              # This file
├── research.md          # Phase 0: scope and wording decisions
├── quickstart.md        # Phase 1: how to verify the change
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks)
```

No `data-model.md` or `contracts/`. The feature adds no entities and changes no
interface.

### Source Code (repository root)

```text
apps/api/
├── .env.example          # CHANGED: three variables added, with comments
└── app/
    ├── core/settings.py  # read only: source of the defaults
    ├── ai/__init__.py    # read only: accepted AI_PROVIDER values
    └── main.py           # read only: WEB_ORIGINS is comma-separated
```

**Structure Decision**: Change only `apps/api/.env.example`. The other files are
read to confirm the defaults and formats the comments describe.

## Complexity Tracking

None.
