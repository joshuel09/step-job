# Research: 職務経歴書 Generator

**Feature**: [spec.md](./spec.md) · **Date**: 2026-10-08

Decisions this feature has to make before code. Each records what was chosen,
why, and what was rejected. Where feature 003 already settled something, that is
said rather than re-argued.

## R-001: What this feature reuses rather than rebuilds

**Decision.** Reuse, unchanged, from `apps/api/app/rirekisho/`:

| What | Where | Used how |
|---|---|---|
| IPAex Gothic, registered at import | `render.py` | A missing font stops the application, not one request |
| `format_japanese_date`, `format_year_month` | `app/imports/dates.py` | 和暦/西暦 for every date in the document |
| `PAGE_SIZES`, `page_size()` | `render.py` | A4 and B5 |
| `snapshots.capture` | `app/career/snapshots.py` | The record of what a document drew on |
| `_Page` (knows when it is full) | `render.py` | Flowing across pages |

**Rationale.** Two documents drawing on one profile should not disagree about
what 平成31年 means or which font renders it. Shared code is how FR-018 — the
two documents never contradicting each other — is held structurally rather than
by two implementations happening to agree.

**Alternatives rejected.** A separate renderer per document type: it would
duplicate the font handling and the era table, and the first divergence would be
a bug nobody notices until an employer holds both documents side by side.

**Consequence for structure.** What is shared moves out of `rirekisho/` into a
`documents/` module both features import. The 履歴書 keeps its own layout; only
the machinery is common. This is a refactor of working, tested code, so it is
sequenced first and covered by the existing suite.

## R-002: The 職務経歴書 is prose, and that changes the projection

**Decision.** Where the 履歴書 projects entries into a flat table of dated rows
(`rows.py`), this projects them into nested sections: one per employer, each
holding a period, a role, a description and a list of achievements.

**Rationale.** The two documents have genuinely different shapes. A 履歴書 row is
a date and one event. A 職務経歴書 section is an employer with structure
underneath it. Forcing the second through the first's model would flatten what
the document exists to show.

**Alternatives rejected.** Extending `Row` with optional nesting: it would make
the 履歴書's exhaustively tested projection carry fields it never uses, for the
benefit of a different document.

**What carries over** is the discipline, not the code: a pure function from
entries to an ordered structure, no knowledge of PDFs, so the conventions can be
tested exhaustively without producing a document. `rows.py` is the model.

## R-003: Assembling 職務要約 without characterising anyone

**Decision.** 職務要約 is built from facts the profile already holds: the span
from the earliest start to the latest end, the number of employers, and the most
recent role and employer. Nothing else.

**Rationale.** The clarification (#82) settled that this feature calls no model.
A summary assembled only from countable facts is traceable by construction —
every clause points at an entry — which is what makes Principle IV hold here
without the evidence machinery feature 002 needed.

**Alternatives rejected.** Characterising phrases drawn from skills or stories
("experienced in...", "strong background in..."). They read better and are
exactly what Principle IV forbids: the profile records that someone listed a
skill, not that they are strong in it.

**Consequence.** A profile too thin to summarise produces a shorter 職務要約, or
none. Saying less is correct; reaching is not.

## R-004: Ordering, and what is deliberately not offered

**Decision.** Two arrangements, reverse-chronological (default) and
chronological, applied to the employer sections. Undated entries sort last, as
in `rows.py`, rather than being dropped.

**Rationale.** Settled by the clarification. Project grouping needs a project
entity the profile does not have, and a career story is an achievement
narrative with no client, period or role, so grouping by it would produce a
section missing most of what a project listing needs.

**Alternatives rejected.** Inferring projects from story titles — invention
wearing a structure.

## R-005: Where an unattached achievement goes

**Decision.** Career stories with no `work_experience_id` are collected into a
closing section after the employer sections.

**Rationale.** The clarification settled that nothing recorded is dropped. A
closing 実績 section is an established convention, so it reads as the document's
own shape rather than as a workaround.

**Alternatives rejected.** Attaching them to the nearest employer by date —
inventing a relationship the user did not record, which is the precise failure
Principle IV names.

## R-006: Snapshot capture, and the relationship to the 履歴書

**Decision.** Capture in the same transaction as the render, exactly as
`rirekisho/service.py` does: the identity leads the captured ids, then every
entry a section drew on, then certifications.

**Rationale.** A render that fails must leave no record of a document nobody
received. Feature 003 found that the identity has to lead the list, because
`snapshots.capture` rejects an empty one and a first-time applicant would
otherwise be refused. The same applies here.

**On FR-018.** The two documents agreeing is not enforced by comparing them at
generation time. It follows from both being assembled from the same entries by
shared date and ordering code. The quickstart checks it by generating both and
comparing the facts they share — a test, not a mechanism.

## R-007: What the user fills in, and how that is shown

**Decision.** 自己PR is a labelled, empty section, as 志望の動機 is in the 履歴書.

**Rationale.** Settled by the clarification: it is a claim about what kind of
worker someone is, which no set of dates and titles evidences. Feature 003
established that a deliberately empty section is labelled rather than omitted,
so the blank reads as a decision instead of a defect (FR-022c of 003).

## Resolved unknowns

Every `[NEEDS CLARIFICATION]` in the spec was resolved in #82 before planning
began. No unknowns remain.

| Question | Resolution |
|---|---|
| Who writes 職務要約 and 自己PR | Split: 職務要約 assembled from facts (R-003); 自己PR left to the user (R-007) |
| What "grouped by project" means | Not offered; two chronological arrangements (R-004) |
| Where an unattached career story goes | A closing achievements section (R-005) |
