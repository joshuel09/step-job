# Data Model: English Resume Generator

**Feature**: 005-english-resume | **Date**: 2026-10-11

This is the first document feature to change the schema. Features 003 and 004
read the profile and wrote one snapshot row between them; this one has to store
something new, because FR-017 requires an English version per entry and
Principle I puts that on the profile rather than inside the generator.

Everything below ships in **one Alembic migration** (constitution gate G11).

---

## New: `entry_translation`

One approved English rendering of one field of one profile entry.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | no | `Entity` primary key |
| `profile_id` | UUID FK → `career_profile.id` | no | `ProfileOwned`, `ON DELETE CASCADE`, indexed |
| `entry_type` | enum `TranslatableEntry` | no | `work_experience`, `education`, `career_story`, `skill`. Not `certification` — see below |
| `entry_id` | UUID | no | the entry this renders. Not a foreign key — see below |
| `field` | varchar(64) | no | the attribute translated, e.g. `job_title` |
| `language` | enum `Locale` | no | `en` today. The column exists so a third language is a row, not a migration |
| `approved_text` | text | no | the user's words, stored exactly as approved |
| `approved_at` | timestamptz | no | when the user approved it |
| `source_fingerprint` | varchar(64) | no | digest of the source text as it read at approval (R-009) |
| `created_at`, `updated_at` | timestamptz | no | `Timestamps` |

**Unique**: `(profile_id, entry_type, entry_id, field, language)`. One approved
English version per field, replaced rather than accumulated.

**Index**: `(profile_id, language)` — the readiness report's query.

### Why `entry_id` is not a foreign key

It cannot be. The column points at one of four tables depending on
`entry_type`, and PostgreSQL has no referential integrity across a
discriminated reference. Two consequences, both handled rather than tolerated:

- **Deletion.** Removing an entry must remove its translations. A database-level
  cascade is unavailable, so the service does it, and an integration test
  asserts no orphan survives the deletion of each of the four entry types. That
  test is the foreign key.
- **Profile deletion.** Covered by the real foreign key on `profile_id`, which
  cascades.

The alternative — four nullable foreign key columns with a check constraint
that exactly one is set — buys integrity for one of the two cases and costs a
column per entity added later. Rejected in research.md R-001.

### Why the fingerprint is stored and not recomputed

The digest is of the source text *at the moment of approval*. Recomputing it
later from the current source answers a different question. Comparing the
stored value against a fresh digest of the current source is what makes
staleness detectable at all (R-009), and it is the whole reason this is a row
with history rather than a column beside the text it renders.

---

## Changed: four columns for proper nouns

Research R-002 keeps organisation names out of `entry_translation` entirely.
They are facts the user states, not renderings of anything, and nothing drafts
them.

| Entity | New column | Type | Null |
|---|---|---|---|
| `work_experience` | `employer_name_english` | varchar(255) | yes |
| `education` | `institution_english` | varchar(255) | yes |
| `certification` | `name_english` | varchar(255) | yes |
| `certification` | `issuer_english` | varchar(255) | yes |

All four default to `NULL`, which means "the user has not supplied one" and
renders as the name recorded (FR-021). No backfill: a migration that guessed
these would be the exact transliteration FR-021 forbids, performed once and
invisibly.

### Why a certification is in no translation at all

It holds a name, an issuer and two dates. The first two are proper nouns and
the last two are not words, so there is nothing on a certification a model
could draft — which is why `certification` appears in `NamedEntry` and not in
`TranslatableEntry`.

The issuer needed the same treatment as the other three and nearly did not get
it. "Japan Information-Technology Engineers Examination" is the body's own
English name or it is a guess, and an invented issuer on a resume is the
FR-021 failure in its most checkable form — an employer verifying a
certification looks the issuer up by name.

**Consequence for feature 001**: these are profile fields, so they belong on
001's contract and on `WorkExperienceIn/Out`, `EducationIn/Out` and
`CertificationIn/Out` (which gains two). The existing `PATCH /profile/experiences/{id}` and the
section routes carry them. No new route is needed to set an English name — one
would be a second way to edit an entry, which Principle I rules out.

---

## Read, not changed

| Entity | Fields this feature reads | Fields it must never read |
|---|---|---|
| `Identity` | `full_name_latin`, `email`, `phone` | `date_of_birth`, `address`, `full_name_japanese`, `furigana` |
| `WorkExperience` | `employer_name`, `employer_name_english`, `job_title`, `started_on`, `ended_on`, `description` | — |
| `Education` | `institution`, `institution_english`, `qualification`, `field_of_study`, `started_on`, `ended_on` | — |
| `Certification` | `name`, `name_english`, `issuer`, `issuer_english`, `issued_on` | — |
| `Skill` | `name`, `level` | — |
| `JapanProfile` | **nothing** | every field, disclosed or not (FR-010) |

### How "must never read" is enforced

Not by review. The projection in `app/resume/sections.py` returns frozen
dataclasses, and those dataclasses have no attribute for a date of birth, an
address or a residence status. The renderer is given only those dataclasses.
A later layout change cannot leak a field that its input type does not carry,
and adding one would mean editing the dataclass, which is a visible diff with
FR-009 written beside it.

This is the same argument feature 004 made for gate G5, one step further: 004
passes by never fetching `JapanProfile`; this feature passes by never fetching
it *and* by the renderer having nowhere to put it.

---

## Written at generation

| Entity | Row | Notes |
|---|---|---|
| `EntrySnapshot` | one | `document_ref = "english-resume"` |

`captured_entry_ids` holds the identity followed by every entry rendered, in
render order. `payload` holds the rendered content including the approved
English used, so a snapshot still describes what was sent after the user edits
an approval (R-010, SC-008).

The identity leads the list for the same reason it does in the 履歴書: a
profile with no experience still produces a document, and `snapshots.capture`
refuses an empty id list.

---

## Not stored

The generated PDF (FR-005), and the translation draft (FR-018). A draft exists
in the response to the request that produced it and nowhere else — there is no
`translation_draft` table, which is how SC-010 holds structurally rather than
by a status column nobody forgets to check.
