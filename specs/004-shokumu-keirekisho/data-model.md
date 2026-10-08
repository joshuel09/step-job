# Data Model: 職務経歴書 Generator

**Feature**: [spec.md](./spec.md) · **Date**: 2026-10-08

This feature **adds no table and no column**. It reads the Master Career Profile
and writes one row of a table feature 001 already owns. That is Principle I
working: a second document is a second consumer, never a second place to
describe a career.

## What is read

| Entity | Fields used | What they become |
|---|---|---|
| `Identity` | `full_name_latin`, `full_name_japanese`, `furigana` | The heading, and the required field (FR-006) |
| `WorkExperience` | `employer_name`, `job_title`, `employment_type`, `started_on`, `ended_on`, `description` | One employer section each |
| `CareerStory` | `work_experience_id`, `title`, `challenge`, `action`, `result` | Achievements under their employer, or the closing section |
| `Certification` | `name`, `issuer`, `issued_on` | The certifications section |
| `Skill` | `name`, `level` | The skills section |
| `Language` | `language`, `proficiency` | The skills section |
| `Education` | `institution`, `qualification`, `started_on`, `ended_on` | Not used — a 職務経歴書 is work history; education belongs to the 履歴書 |

`employer_name_normalised` is read by nobody here. It exists for duplicate
detection and is never shown.

## What is written

| Entity | When | Fields |
|---|---|---|
| `EntrySnapshot` | Once per generation, in the render's transaction | `document_ref`, `captured_at`, `captured_entry_ids`, `payload` |

Insert-only, as feature 001 defined it. Nothing in this feature updates a
snapshot after creation; that is what keeps a sent document inspectable.

## The projection

A pure function from entries to an ordered structure, with no knowledge of
documents, mirroring `rows.py` (research.md R-002).

```
CareerHistory
├── summary: Summary            # assembled from counted facts (R-003)
├── sections: [EmployerSection] # ordered by the chosen arrangement
│   ├── employer, title, employment_type
│   ├── period: (started_on, ended_on | ongoing)
│   ├── description
│   ├── achievements: [Achievement]
│   └── source_entry_id
├── unattached: [Achievement]   # closing section (R-005)
├── skills, languages, certifications
└── self_pr: empty, labelled    # the user's to write (R-007)
```

**`Summary`** holds only countable facts: `span_years`, `employer_count`,
`latest_role`, `latest_employer`. It carries no adjective. A profile with too
little to count produces a shorter summary or none — saying less is correct,
reaching is not.

**`Achievement`** is a career story rendered as the user wrote it: `title`,
`challenge`, `action`, `result`, and the `source_entry_id` that produced it.
Nothing is rephrased.

**`source_entry_id`** on every element is what makes FR-016 checkable: for any
statement in the document, the entry behind it can be named. Only the summary's
derived counts have none, because a count is arithmetic over entries rather
than a claim from one.

## Ordering rules

1. Employer sections sort by `started_on` — newest first by default,
   oldest first when chronological is chosen.
2. An entry with no `started_on` sorts last rather than being dropped. It is
   still part of someone's history (`rows.py` established this).
3. Achievements within a section keep their recorded order; the profile does
   not rank them and neither does this.
4. Overlapping employment produces two sections, unreconciled. Concurrent roles
   are legitimate and the document does not tidy them away.

## Validation

| Rule | Where | Effect |
|---|---|---|
| A name is required | `service.generate` | 422 naming `identity`, as the 履歴書 does (FR-006) |
| Some career history is required | `service.generate` | 422; a 職務経歴書 with no work history is not the document |
| Captured ids must be non-empty | `snapshots.capture` | The identity leads the list, so this cannot be hit (R-006) |

## What this feature does not touch

- **`JapanProfile` and its disclosure flags.** A 職務経歴書 is a career history,
  not a personal-details form. The flags govern the 履歴書; reading them here
  would be treating consent for one document as consent for another.
- **`ProposedEntry`.** This feature creates no proposals.
- **Any model provider.** The generator is deterministic (#82). The AST walker
  from feature 002 enforces this by test.
