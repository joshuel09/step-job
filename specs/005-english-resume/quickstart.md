# Quickstart: English Resume Generator

**Feature**: 005-english-resume | **Date**: 2026-10-11

Scenarios that prove the feature works end to end. Each names the requirement
it holds, so a scenario that gets deleted takes a visible guarantee with it.

**Every document assertion extracts text back out of the PDF.** A page of
hollow boxes is the right size, starts with `%PDF-`, and passes any check on
bytes. Feature 003 established this and it matters more here, not less: the one
place this document renders Japanese is an employer's name, which is exactly
where a missing glyph is both likeliest and worst.

## Prerequisites

```bash
# PostgreSQL on 5433, as the other features expect
uv sync --all-packages --all-extras
uv run --project apps/api alembic upgrade head
```

The default provider is the fake (`ai_provider = "fake"`). Nothing below
reaches a network, and the scenarios that exercise drafting use the fake's
behaviours the way feature 002's tests do.

## Running

```bash
uv run --project apps/api pytest tests/ -q
uv run --project apps/api pytest tests/integration/test_resume_generate.py -q
```

---

## Scenario 0 — The Japanese that has to render

**Given** an employer recorded only as 株式会社サンプル, with no English name
supplied
**When** a resume is generated
**Then** the extracted text contains 株式会社サンプル, and the document embeds
a font (`/FontFile2`)

The check a page of boxes fails. R-007 and FR-021.

## Scenario 1 — A profile becomes a resume

**Given** a profile with an identity, two employers, one degree, skills and a
certification
**When** the user generates
**Then** the name, email and telephone appear; both employers appear with
title and period; the education, skills and certification sections appear;
and `X-Snapshot-Id` is returned

US1. FR-001, FR-003.

## Scenario 2 — Newest first

**Given** two employers, one 2018–2021 and one 2021–present
**When** the user generates
**Then** the 2021 employer appears before the 2018 one in the extracted text

US1-1. FR-002.

## Scenario 3 — Western dates, no era anywhere

**Given** a profile whose interface locale is Japanese
**When** the user generates
**Then** the periods read as `Mar 2021 – Present`, and none of 令和, 平成,
昭和 or 年号 appears anywhere in the document

US1-4. FR-004, SC-003. Asserted as an absence across the whole text, not per
field — an era leaking through one unconverted date is the failure.

## Scenario 4 — Nothing to say, so no document

**Given** a profile with an identity and no career history at all
**When** the user generates
**Then** the response is 422 and names what is missing

US1-5. FR-006. The mirror of feature 003's first-time applicant, which
deliberately *does* produce a document: a 履歴書 with an empty table is a
conventional document, and a resume with no experience is not.

## Scenario 5 — Told before, not after

**Given** two entries written in Japanese with no stored English version
**When** the user requests the readiness report
**Then** both are named in `needs_english`, each with its source text

US2-1. FR-020.

## Scenario 6 — A draft is offered, never placed

**Given** an entry with no English version
**When** the user requests a draft
**Then** a draft is returned with its source text beside it, and querying the
stored English versions afterwards returns nothing

US2-2. FR-018, SC-010. The second half is the assertion that matters: the
request that produces a draft must store nothing.

## Scenario 7 — The alternatives are surfaced, not resolved

**Given** a job title recorded as 課長
**When** the user requests a draft
**Then** the response carries alternatives naming the phrase and at least two
readings of it

R-004. FR-013, SC-006. The product does not choose between "Manager" and
"Section Chief" on the user's behalf.

## Scenario 8 — Approved once, reused thereafter

**Given** a draft the user edits and approves
**When** the resume is generated, and then the readiness report is requested
again
**Then** the approved text appears in the document, and the entry is no longer
in `needs_english`

US2-3, US2-4. FR-018, SC-012. Principle I: the same work is not asked for
twice.

## Scenario 9 — Character for character

**Given** an approval whose text differs from the draft that preceded it
**When** the resume is generated
**Then** the extracted text contains the user's wording exactly, and does not
contain the draft's

US2-6. FR-019, SC-011.

## Scenario 10 — An approved blank is not an English version

**Given** an approval whose text is empty or whitespace
**When** it is submitted
**Then** the response is 422

Edge case. An approved blank would make an entry vanish from the document
silently, which is worse than having no English version at all.

## Scenario 11 — Editing the source does not discard the approval

**Given** an approved English version, **and** the underlying Japanese is then
edited
**When** the readiness report is requested
**Then** the approval appears in `stale_translations` with the current source
text, and **is still stored** — not deleted and not re-drafted

**And when** the resume is generated
**Then** it is generated, carrying the approved text

R-009. The user approved those words; a typo fix in the source does not
withdraw their approval.

## Scenario 12 — Nothing personal

**Given** a profile with a date of birth, a full address, a photograph
reference and every `JapanProfile` field populated **and disclosed**
**When** the user generates
**Then** none of the date of birth, any age derived from it, the address, the
nationality, the residence status, the visa type or 写真貼付欄 appears anywhere

US3-1, US3-2, US3-3, US3-4. FR-008, FR-009, FR-010, SC-002. The disclosure
flags are set to `true` on purpose: they are consent for a Japanese document,
not standing permission.

## Scenario 13 — An empty section is absent, not blank

**Given** a profile with no certifications
**When** the user generates
**Then** no certifications heading appears

US3, US4-4. FR-011, SC-005. The opposite of the 履歴書, which labels its empty
sections because a Japanese employer expects to see them.

## Scenario 14 — Exactly as much as was recorded

**Given** an employer with a title and dates and no description
**When** the user generates
**Then** that employer appears with title and period and nothing else — no
summary, no adjective, no inferred scope

US4-1. FR-012, Principle IV.

## Scenario 15 — The two documents agree

**Given** one profile with approved English for every entry
**When** both a 履歴書 and an English resume are generated from it
**Then** the same employers appear in both, over the same periods, in the same
set

FR-016, SC-007. Compared as entries and periods, never as strings — the
Japanese document says 課長 and the English one says what the user approved,
and that is the product working correctly. See research.md R-008.

## Scenario 16 — What was sent stays inspectable

**Given** a generated resume and its snapshot id
**When** the user then edits one of the entries it drew on
**Then** fetching the snapshot still shows the English the document carried

FR-015, SC-008.

## Scenario 17 — A proper noun is never guessed

**Given** an employer recorded only in Japanese, a second with
`employer_name_english` supplied, and a certification whose issuer is recorded
only in Japanese
**When** the user generates
**Then** the first employer and the issuer appear in Japanese exactly as
recorded, the second employer in the supplied English, and the readiness report
names both untranslated names under `untranslated_names`

**And when** a draft is requested for any of them
**Then** it is refused — `certification` is not a translatable entry type, and
an organisation name is never drafted

FR-021, SC-013, R-002. An invented issuer is the FR-021 failure in its most
checkable form: an employer verifying a certification looks the issuer up by
name.

## Scenario 18 — Generation calls no model

**Given** a configuration whose provider raises on every call
**When** a resume is generated from a profile with approved English
**Then** the document is produced

FR-017, FR-005 of the generator's determinism. The strongest available check
that the render path cannot reach a provider: make every provider call fail
and watch generation succeed anyway.

## Scenario 19 — Deleting an entry takes its English with it

**Given** approved English on an entry of each translatable type — work
experience, education, career story, skill
**When** each entry is deleted
**Then** no `entry_translation` row survives for it

data-model.md. `entry_id` cannot be a foreign key across four tables, so this
test is the foreign key.

## Scenario 20 — The document is not retained

**Given** any generated resume
**When** the schema is inspected
**Then** no column anywhere could hold it

FR-005. Asserted against `Base.metadata` rather than a count of rows, as
feature 003 established: a count shows only that today's code stores nothing.
