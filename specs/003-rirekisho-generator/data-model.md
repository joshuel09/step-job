# Phase 1 Data Model: 履歴書 Generator

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

This feature persists almost nothing. Two optional columns are added to feature
001's identity record; everything else exists for the duration of one request.
That is the point: a generated document is not retained (FR-005), and what
survives is the profile it came from and the snapshot recording what was used.

## What does not persist

| Named in the spec | What it actually is |
|---|---|
| **Generated 履歴書** | Streamed to the user and discarded. Nothing stores it. |
| **Document Conventions** | The request body. Affects presentation only, never content, so there is nothing to remember. |
| **学歴・職歴 Row** | An intermediate value between the projection and the renderer. |
| **Generation Record** | The existing `EntrySnapshot` from feature 001 (research.md R-003). No new table. |

## Changed entity

### Identity — feature 001

Two optional additions. Optional so that every existing profile stays valid, and
so the generator leaves them blank when absent rather than inventing them
(FR-013).

| Field | Type | Notes |
|---|---|---|
| `date_of_birth` | date, nullable | Conventional on a 履歴書; identity data, so it lives on the profile rather than being asked per document |
| `address` | text, nullable | The applicant's current address, 現住所 |

**Rules**

- Both are optional. A profile without them produces a document with those
  fields blank, not a refusal and not a guess.
- A date of birth is rendered in whichever convention the document uses, like
  every other date in it.
- Changing these changes four things together, listed in research.md R-004 — the
  model, the schemas, feature 001's contract, and the form a user types them
  into. A migration without the form would add fields nobody could fill in.

## Transient structures

### RirekishoRequest

What the user chose for this document.

| Field | Type | Notes |
|---|---|---|
| `date_convention` | enum `seireki` \| `wareki` | Default `seireki` (FR-017) |
| `paper_size` | enum `a4` \| `b5` | Default `a4` (FR-018) |

Typed enumerations rather than strings, per constitution gate G9. Neither
affects what the document says, only how it reads.

### Row

One line of the combined 学歴・職歴 table.

| Field | Type | Notes |
|---|---|---|
| `date` | date \| None | Rendered in the document's convention. None only for the closing row. |
| `institution` | text | The school or employer |
| `event` | enum | 入学, 卒業, 入社, 退社, 現在に至る, 以上 |
| `source_entry_id` | UUID \| None | Which profile entry produced this row |

`source_entry_id` is what makes FR-012 and SC-008 checkable: for any line in the
document, the entry behind it can be named. The closing 以上 row has none,
because it is a convention rather than a claim.

### ReadinessReport

What the user still needs to do, returned before or instead of a document.

| Field | Type | Notes |
|---|---|---|
| `can_generate` | boolean | False only when something essential is missing |
| `missing_required` | list of field names | Things without which a document is meaningless — a name above all (FR-015) |
| `missing_optional` | list of field names | Things that will be blank: a date of birth, an address |
| `entries_without_japanese` | list of entry ids | Written in English, so they will appear in English (R-001) |

The last of these is how FR-014b's offer is discharged without generating
anything: the user is told which entries have no Japanese version and can add
one to their profile themselves.

## The 学歴・職歴 projection

The one non-trivial transform here, and the one where a mistake produces a wrong
career history rather than an ugly document. A pure function, defined here and
implemented in its own module so it can be tested without producing a PDF.

**Input**: the profile's education entries and work experiences.
**Output**: an ordered list of rows.

```text
education, sorted by start date, oldest first
  each entry →  [started_on]  institution  入学
                [ended_on]    institution  卒業      (omitted if no end date)

then work experience, sorted by start date, oldest first
  each entry →  [started_on]  employer     入社
                [ended_on]    employer     退社      if the role has ended
                [—]           —            現在に至る  if it has not

then                                       以上
```

**Rules**

- Education precedes employment, whatever the dates say. This is the convention,
  not a chronological claim (FR-006).
- Within each block, oldest first (FR-006).
- An education entry with no end date produces only the entering row. Nothing is
  inferred about whether the course finished (FR-014).
- A work experience with no end date produces 現在に至る rather than a date
  (FR-009). This is what the profile says, and correcting it is a profile edit.
- Overlapping entries both appear, in start-date order. The system does not
  reconcile, reorder or omit either to make a history look tidier (FR-011).
- Entries with no start date are placed last within their block rather than
  dropped, and render without a date.
- The table always ends with 以上 (FR-010), including when it is otherwise
  empty — a first-time applicant's 履歴書 is a legitimate document.

## Disclosure filtering

Which Japan-specific fields may appear. Small, single-purpose, and separate
because getting it wrong means publishing someone's visa status.

| Profile field | Appears only if |
|---|---|
| `residence_status` | `disclose_residence_status` |
| `nationality` | `disclose_nationality` |
| `visa_type`, `visa_expires_on` | `disclose_visa` |
| `work_authorisation` | `disclose_work_authorisation` |
| `japanese_qualification` | `disclose_japanese_qualification` |

**Rules**

- The default is withheld, set in the schema by feature 001 and read here for
  the first time (FR-020, gate G5).
- A disclosed field appears in 本人希望記入欄, which is where a 履歴書
  conventionally carries anything outside its fixed sections.
- The filter is applied before rendering, so an undisclosed value never reaches
  the renderer at all. A field that is never passed cannot be accidentally
  drawn.
- Withdrawing a disclosure and regenerating produces a document without the
  field (FR-021).

## Validation summary

| Rule | Source | Applies to |
|---|---|---|
| A field the profile does not support is left blank | FR-013 | every section |
| No value inferred from another | FR-014 | dates, readings |
| No translation during generation | FR-014a, SC-003a | every entry |
| Education before employment, oldest first within each | FR-006 | the projection |
| An unfinished role renders 現在に至る | FR-009 | the projection |
| Overlapping entries both appear, unreconciled | FR-011 | the projection |
| The table ends with 以上 | FR-010 | the projection |
| No entry dropped to fit a page | FR-018a, SC-007a | rendering |
| One date convention per document | FR-019, SC-007 | rendering |
| Undisclosed Japan-specific fields never appear | FR-020, SC-005, gate G5 | disclosure filtering |
| No gender field at all | FR-022 | the form itself |
| Every row names the entry that produced it | FR-012, SC-008 | the projection |
| A snapshot records what the document used | FR-016, SC-004 | generation |
