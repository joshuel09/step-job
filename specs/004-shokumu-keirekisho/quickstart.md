# Quickstart: 職務経歴書 Generator

**Feature**: [spec.md](./spec.md) · **Date**: 2026-10-08

Runnable scenarios that prove the feature works end to end. Each names the
requirement it exercises. Every assertion reads text back out of the produced
document: a page of hollow boxes is the right size and passes any check on
bytes, so asserting on the file proves nothing about what an employer sees.

## Prerequisites

```bash
docker compose up -d db                 # PostgreSQL
cd apps/api && uv sync --all-extras
uv run alembic upgrade head
```

No new environment variable. This feature calls no model, so `AI_PROVIDER` is
irrelevant to it.

## Scenario 0 — the Japanese is readable (FR-002)

The check that fails loudly when the font is missing. Everything below assumes
it passes.

```bash
uv run pytest tests/integration/test_shokumu_font.py -q
```

**Expect**: 職務経歴書 extracts as text, and the document carries `/FontFile2`
so an employer printing it sees glyphs rather than boxes.

## Scenario 1 — a profile becomes a career history (FR-001, FR-003, FR-004)

Record two employers, one with achievements, and generate.

```bash
uv run pytest tests/integration/test_shokumu_generate.py -q
```

**Expect**: both employers appear with period, title and description; the
recorded career stories appear as achievements under the employer they belong
to, in the user's own words; skills and certifications have their own sections.

## Scenario 2 — the arrangement changes the order, nothing else (FR-007, FR-008)

```bash
uv run pytest tests/integration/test_shokumu_arrangement.py -q
```

**Expect**: reverse-chronological puts the newest employer first, chronological
the oldest, and the two documents contain **the identical set of entries** —
none gained, lost, merged or shortened. Project grouping is not offered and the
request is refused if asked for.

## Scenario 3 — one convention throughout (FR-009, FR-010)

```bash
uv run pytest tests/integration/test_shokumu_conventions.py -q
```

**Expect**: a 和暦 document has era years and **no four-digit Western year
anywhere**, not only in the date column; a 西暦 document has no era name. Both
paper sizes carry the same content.

## Scenario 4 — 職務要約 says only what can be counted (FR-019, SC-009)

```bash
uv run pytest tests/integration/test_shokumu_summary.py -q
```

**Expect**: the summary states the career span, the number of employers and the
most recent role, each traceable to entries. It contains **no adjective
characterising the applicant** — no "experienced", "strong", "proven". A profile
with one undated employer produces a shorter summary rather than a reaching one.

## Scenario 5 — 自己PR is labelled and empty (FR-020, SC-010)

```bash
uv run pytest tests/integration/test_shokumu_blanks.py -q
```

**Expect**: 自己PR appears as a heading with nothing under it, in every
document, whatever the profile holds. An employer with no recorded description
gets its period and name and no invented narrative.

## Scenario 6 — nothing recorded is lost (FR-021, SC-011)

```bash
uv run pytest tests/integration/test_shokumu_unattached.py -q
```

**Expect**: a career story with no employer appears in the closing achievements
section. Count the stories going in; the same number comes out. A profile whose
stories are all unattached has empty employer sections and a full closing one —
a true picture of what was recorded.

## Scenario 7 — the document stays traceable after an edit (FR-016, FR-017)

```bash
uv run pytest tests/integration/test_shokumu_traceability.py -q
```

**Expect**: generating returns a snapshot id; renaming the employer afterwards
does not change what the snapshot says; a later document reflects the edit while
the earlier snapshot does not.

## Scenario 8 — the two documents agree (FR-018, SC-007)

The scenario unique to this feature.

```bash
uv run pytest tests/integration/test_document_agreement.py -q
```

**Expect**: a 履歴書 and a 職務経歴書 generated from the same profile carry the
same employers, the same periods and the same titles. Not because they are
compared at generation time, but because both are assembled from the same
entries by shared date and ordering code (research.md R-006). This test is what
would catch that shared code diverging.

## Scenario 9 — a long career keeps every entry (FR-011, SC-008)

```bash
uv run pytest tests/integration/test_shokumu_long_history.py -q
```

**Expect**: a profile with twelve employers produces every one of them across
as many pages as needed. Count in, count out. No entry dropped or truncated to
reach a conventional length.

## Scenario 10 — refused rather than empty (FR-006)

```bash
uv run pytest tests/integration/test_shokumu_generate.py -q -k refused
```

**Expect**: a profile with no name is refused with `identity` named; a profile
with no work history at all is refused saying so. Neither returns a document.

## Full run

```bash
cd apps/api && uv run pytest -m "not live" -q
cd ../.. && corepack pnpm --filter web build
```

**Expect**: the whole suite passes, the generated client is current, and the
contract tests show no documented path left unimplemented for this feature.
