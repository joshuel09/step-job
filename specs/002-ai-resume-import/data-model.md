# Phase 1 Data Model: AI Resume Import

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

This feature adds one entity and changes one belonging to feature 001. The
conventions from [001's data model](../001-master-career-profile/data-model.md)
apply unchanged: UUID primary keys, created and updated timestamps, ownership
through a profile, and soft-deleted profiles excluded from every read.

## What does not persist

The specification names **Extracted Entry** and **Source Evidence** as entities.
Neither becomes a table.

- An **extracted entry** exists only between the model returning a result and
  that result becoming a `ProposedEntry`. Entries that fail evidence verification
  are dropped at that moment and never stored.
- **Source evidence** is stored, but as a column on the proposal it justifies
  rather than a table of its own (research.md R-003), because it is meaningless
  apart from that proposal and must be deleted with the review decision.

The **extraction outcome** is stored on the import.

## New entity

### Import

One attempt to bring career information in from a source.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `profile_id` | UUID | Owner; cascade deleted with the profile (FR-019c) |
| `source_kind` | enum `pasted_text` \| `pdf` \| `docx` | What the user supplied |
| `status` | enum `pending` \| `running` \| `completed` \| `failed` | Typed, not free text (gate G9) |
| `failure_reason` | enum, nullable | Why it failed, where it did — see below |
| `started_at` | timestamp | |
| `completed_at` | timestamp, nullable | Set when it reaches a terminal state |
| `outcome` | structured document, nullable | What was found and what was looked for and not found (FR-016) |
| `entry_count` | integer | How many proposals it produced; zero is a valid result |

**Deliberately absent: the filename.** Clarification Q5 excluded it. An import
record survives review, and a name such as the company someone was applying to
reveals their job search. Nothing after extraction needs it (FR-019b).

**Also absent: the document, and its text.** The bytes are never written
(research.md R-005), and the extracted text is not retained either — what
survives is the evidence attached to each proposal, and that only until review.

**`failure_reason` values**, distinguishing outcomes that look alike to a user
but have different remedies (FR-017b):

| Value | Meaning | Worth retrying |
|---|---|---|
| `unreadable_document` | No text layer, corrupt, or password protected | No |
| `unsupported_format` | Not a format this feature accepts | No |
| `no_career_information` | Readable, but nothing extractable was found | No |
| `service_unavailable` | The extraction service could not be reached | Yes, later |
| `extraction_failed` | The service responded with something unusable | Yes, later |

**State transitions**

```text
pending ──► running ──┬──► completed   (proposals created, or zero found)
                      └──► failed      (failure_reason set; nothing created)
```

`completed` and `failed` are terminal. A `running` import either finished in the
request or was handed to the worker (research.md R-002); which of those happened
is not recorded, because it makes no difference to the result (FR-005c).

**Rules**

- An import MUST reach a terminal state. Nothing is left `running` indefinitely
  (SC-007).
- A `failed` import MUST have produced no proposals (FR-017, FR-017d).
- A `completed` import with `entry_count` zero is valid: the document was read
  and contained nothing extractable (FR-016).
- Import records are erased with the profile, on the same terms as the entries
  they produced.

## Changed entity

### ProposedEntry — feature 001

Three nullable additions. All are nullable so that proposals created by any other
means remain valid without them.

| Field | Type | Notes |
|---|---|---|
| `import_id` | UUID, nullable | The import that created this proposal, where one did |
| `evidence` | structured document, nullable | Per field: the passage of source text the value came from |
| `conflicts` | structured document, nullable | Fields whose values disagree within the source (FR-012a) |

**`evidence` shape** — one entry per populated field:

```text
{
  "job_title":     {"quote": "<passage from the source>", "verified": true},
  "employer_name": {"quote": "<passage from the source>", "verified": true}
}
```

A field only appears here if its quote was verified against the source. A field
whose quote could not be found is absent from the proposal entirely — left empty
and marked not found (FR-008), never populated with a value it cannot justify.

**`conflicts` shape** — one entry per disagreement:

```text
[
  {"fields": ["started_on", "ended_on"], "reason": "end date precedes start date"}
]
```

**Rules**

- Evidence MUST be cleared when the proposal is accepted or rejected, in the same
  transaction that records the decision (FR-015a). Doing it in the same
  transaction is what makes the guarantee survive a process dying immediately
  afterwards.
- Clearing evidence MUST NOT alter the accepted entry (FR-015b). What the user
  approved stays exactly as approved.
- `conflicts` is retained with the proposal, because a rejected proposal's
  conflict is part of why it was rejected; unlike evidence, it holds no document
  text.
- A proposal carrying a conflict MUST still be acceptable once the user has
  corrected the offending fields (FR-012c).

## Relationships

```text
CareerProfile (1)
├── (*) Import
│        └── (*) ProposedEntry        via ProposedEntry.import_id
└── (*) ProposedEntry                  (feature 001; may exist without an import)
```

Deleting a profile removes its imports and its proposals together, as it already
removes everything else beneath it.

## Validation summary

| Rule | Source | Applies to |
|---|---|---|
| A field without verified evidence is never populated | FR-008, R-001 | ProposedEntry.evidence |
| Evidence cleared on review, in the same transaction | FR-015a | ProposedEntry |
| Clearing evidence does not alter the accepted entry | FR-015b | ProposedEntry |
| A failed import produced no proposals | FR-017, FR-017d | Import |
| Every import reaches a terminal state | SC-007 | Import.status |
| Filename never stored | FR-019b, Q5 | Import |
| Document bytes never written | FR-004, R-005 | — enforced by never persisting |
| Dates recorded at the source's precision | FR-009 | extracted values |
| Era years converted deterministically, original kept as evidence | FR-011, R-007 | ProposedEntry.evidence |
| Contradictions flagged, never resolved | FR-012a, FR-012b | ProposedEntry.conflicts |
