# Phase 1 Data Model: Master Career Profile

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

Entities derive from the spec's Key Entities; fields and rules derive from the
functional requirements and the Phase 0 decisions. Types are described in
database-neutral terms.

## Conventions

These apply to every entity below and exist to satisfy constitution gates rather
than as house style.

- **Identity** — every entity has a stable UUID primary key, assigned on creation
  and never reused. This is what makes FR-010 traceability possible (gate G3).
- **Ownership** — every entity belongs to exactly one `CareerProfile`, directly or
  through a parent, and is reachable only through the calling user's profile
  (research.md R-006).
- **Timestamps** — `created_at` and `updated_at` on every entity.
- **Source language** — every entity holding user-authored prose carries
  `source_language` (enum: `en`, `ja`). This is the language the user wrote in, not
  a display preference, and satisfies FR-009 and gate G2.
- **Soft deletion** — reads exclude soft-deleted profiles at the data-access
  layer, so FR-027 holds structurally rather than per endpoint.

## Entities

### CareerProfile

Root record; one per user.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `user_id` | UUID | Unique; the authenticated owner (R-006) |
| `interface_locale` | enum `en` \| `ja` | Default `en`; the persisted setting from FR-021 and R-003 |
| `deleted_at` | timestamp, nullable | Set when the user deletes the profile |
| `purge_after` | timestamp, nullable | `deleted_at` + 30 days (FR-025) |

**Rules**

- Exactly one profile per user.
- `interface_locale` is independent of any entry's `source_language` (FR-023).
- When `deleted_at` is set, the profile and everything below it are excluded from
  every read (FR-027).

### Identity

The user's names and contact details. One per profile.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `profile_id` | UUID | Unique — one identity per profile |
| `full_name_latin` | text | Required |
| `full_name_japanese` | text, nullable | Optional (FR-001) |
| `furigana` | text, nullable | Phonetic reading of the Japanese name |
| `email` | text, nullable | |
| `phone` | text, nullable | |

**Rules**

- A single-part name is valid; the model stores one name string rather than
  separate given and family fields, per the spec's edge cases.
- `furigana` is only meaningful alongside `full_name_japanese`, but neither is
  required.

### JapanProfile

Japan-specific hiring circumstances. One per profile. Every field is optional
(FR-005) and every field is independently disclosable (FR-006).

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `profile_id` | UUID | Unique |
| `residence_status` | text, nullable | |
| `nationality` | text, nullable | |
| `visa_type` | text, nullable | |
| `visa_expires_on` | date, nullable | |
| `work_authorisation` | boolean, nullable | |
| `japanese_qualification` | text, nullable | e.g. a language proficiency certificate and level |
| `disclose_residence_status` | boolean | **Default false** |
| `disclose_nationality` | boolean | **Default false** |
| `disclose_visa` | boolean | **Default false** — governs type and expiry together |
| `disclose_work_authorisation` | boolean | **Default false** |
| `disclose_japanese_qualification` | boolean | **Default false** |

**Rules**

- Disclosure flags default to false **in the schema**, not merely in the
  interface (gate G5). A generated document may read a field only when its flag is
  true.
- Disclosure flags govern generated documents only. A profile export includes
  these fields regardless (FR-037).
- `residence_status`, `nationality`, `visa_type` and `visa_expires_on` are hard
  deleted immediately on profile deletion and are never recoverable (FR-024).

### WorkExperience

One role at one employer over a period.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `profile_id` | UUID | |
| `employer_name` | text | Required |
| `employer_name_normalised` | text | Derived; used for duplicate matching (R-004) |
| `job_title` | text | Required |
| `employment_type` | enum | e.g. permanent, contract, part-time, internship, freelance |
| `started_on` | date | Required |
| `ended_on` | date, nullable | Null means ongoing |
| `description` | text | Responsibilities, free-form, stored in full |
| `source_language` | enum `en` \| `ja` | |

**Rules**

- `ended_on`, when present, MUST be on or after `started_on` (FR-014). Rejected
  with an explanation, not silently corrected.
- A null `ended_on` means ongoing, and counts as extending to the present for
  overlap comparisons (R-004).
- Overlapping experiences are valid and produce no warning — concurrent roles and
  contract work are normal.
- More than one ongoing experience is valid.
- `employer_name_normalised` is derived from `employer_name`: case-folded, with
  punctuation, whitespace runs and common company suffixes removed. It exists for
  matching and is never shown to the user.
- `description` is stored in full; no truncation.

### Education

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `profile_id` | UUID | |
| `institution` | text | Required |
| `qualification` | text, nullable | |
| `field_of_study` | text, nullable | |
| `started_on` | date, nullable | |
| `ended_on` | date, nullable | |
| `source_language` | enum `en` \| `ja` | |

**Rules**

- A profile with no education entries is valid (spec edge cases).
- Where both dates are present, `ended_on` MUST be on or after `started_on`.

### Certification

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `profile_id` | UUID | |
| `name` | text | Required |
| `issuer` | text, nullable | |
| `issued_on` | date, nullable | |
| `expires_on` | date, nullable | Null means it does not expire |
| `source_language` | enum `en` \| `ja` | |

### Skill

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `profile_id` | UUID | |
| `name` | text | Required |
| `level` | enum, nullable | Self-assessed |

**Relationships**

- Many-to-many with `WorkExperience`, recording where a skill was used. The join
  carries no additional attributes.

### Language

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `profile_id` | UUID | |
| `language` | text | Required |
| `proficiency` | enum | Required — e.g. native, business, conversational, basic |
| `qualification` | text, nullable | A formal certificate and level, if any |

**Rules**

- `proficiency` is a typed enumeration, never free text (gate G9).

### CareerPreference

What the user is seeking next. One per profile.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `profile_id` | UUID | Unique |
| `desired_roles` | text[] | |
| `desired_locations` | text[] | |
| `working_arrangement` | enum, nullable | e.g. onsite, hybrid, remote |
| `salary_min` | integer, nullable | |
| `salary_max` | integer, nullable | |
| `currency` | text, nullable | |
| `source_language` | enum `en` \| `ja` | |

**Rules**

- Where both are present, `salary_max` MUST be greater than or equal to
  `salary_min`.

### CareerStory

A structured accomplishment, reusable as a STAR example (FR-007).

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `profile_id` | UUID | |
| `work_experience_id` | UUID, nullable | The role it happened in |
| `title` | text | Required |
| `challenge` | text | Required |
| `action` | text | Required |
| `result` | text | Required |
| `source_language` | enum `en` \| `ja` | |

**Rules**

- Deleting a linked `WorkExperience` requires confirmation and the user is told
  stories are linked (FR-013, User Story 2 scenario 3).
- When two experiences are merged, linked stories follow the surviving experience
  rather than being orphaned (spec edge cases).
- Stories are searchable by keyword across `title`, `challenge`, `action` and
  `result`.

### ProposedEntry

Career information suggested by an outside source, awaiting review (FR-017 to
FR-020). Not part of the profile.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `profile_id` | UUID | |
| `entry_type` | enum | Which kind of entry is proposed |
| `source` | text | Which source produced it (FR-017) |
| `status` | enum `pending` \| `accepted` \| `rejected` | Default `pending` |
| `payload` | structured document | The proposed content, shaped by `entry_type` |
| `possible_duplicate_of` | UUID, nullable | An existing entry it may duplicate |
| `reviewed_at` | timestamp, nullable | |

**Rules**

- Proposals live in their own table and are never joined into profile reads, so
  they are invisible to every profile reader until accepted (FR-018, gate G6).
- The user may edit `payload` before accepting. On acceptance the **edited**
  version becomes the profile entry and the original proposal content is not
  retained as profile data (FR-019, User Story 3 scenario 2).
- `possible_duplicate_of` is a suggestion only; the system never merges without
  the user choosing to, and keeping both is always available (FR-034).

**State transitions**

```text
pending ──accept──► accepted   (creates the corresponding profile entry)
   │
   └────reject────► rejected   (creates nothing)
```

`accepted` and `rejected` are terminal. A proposal cannot return to `pending`.

### EntrySnapshot

An immutable copy of the entries a generated document drew on (FR-028 to FR-031,
research.md R-001).

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `profile_id` | UUID | For cascade on deletion (FR-031) |
| `document_ref` | text | Identifies the document that caused the capture |
| `captured_at` | timestamp | |
| `captured_entry_ids` | UUID[] | The entries captured, by identity |
| `payload` | structured document | Their content as it read at capture time |

**Rules**

- Insert-only. A snapshot is never updated after creation (FR-029).
- Remains readable and unchanged after the entries it captured are edited or
  deleted — that is its entire purpose.
- `captured_entry_ids` preserves the link back to live entries where they still
  exist, satisfying FR-010 in both directions.
- Erased with the profile, on the same terms as the entries it captured
  (FR-031) — meaning within the 30-day window, not immediately.

## Profile deletion lifecycle

Derived from FR-024 to FR-027 and research.md R-002. Two mechanisms, because the
two classes of data carry different obligations.

```text
active
  │
  │ user deletes profile
  ▼
same transaction:
  • JapanProfile residence_status, nationality, visa_type,
    visa_expires_on  ─────────────────────────► hard deleted, unrecoverable
  • CareerProfile.deleted_at  = now
  • CareerProfile.purge_after = now + 30 days
  ▼
soft-deleted  ── excluded from every read; invisible to all features
  │
  ├── user restores within 30 days ──► active
  │                                     (Japan-specific fields do not return)
  │
  └── purge_after passes ──► scheduled job hard deletes the profile
                             and everything below it, permanently
```

**Rules**

- Before deletion proceeds, the user is told what is erased immediately, what is
  recoverable, and when the window ends (FR-026).
- Restoration recovers everything still held. It does not recover the
  immediately-erased fields, and the user is told so at deletion time.
- The purge job is idempotent: re-running it over an already-purged profile is a
  no-op, so a retry cannot fail the whole batch.

## Entity relationships

```text
CareerProfile (1)
├── (1) Identity
├── (1) JapanProfile
├── (1) CareerPreference
├── (*) WorkExperience ──(*)──┐
├── (*) Education             │ skills used in a role
├── (*) Certification         │
├── (*) Skill ────────────────┘
├── (*) Language
├── (*) CareerStory ──(0..1)──► WorkExperience
├── (*) ProposedEntry ──(0..1)──► any existing entry (possible duplicate)
└── (*) EntrySnapshot
```

## Validation summary

| Rule | Source | Applies to |
|---|---|---|
| End date on or after start date | FR-014 | WorkExperience, Education |
| Salary maximum at least the minimum | derived | CareerPreference |
| Overlapping experiences permitted without warning | spec edge cases | WorkExperience |
| Duplicate when employer matches and dates overlap | FR-032 | ProposedEntry vs WorkExperience |
| Non-overlapping roles at one employer stay distinct | FR-033 | WorkExperience |
| Disclosure flags default false | FR-006, gate G5 | JapanProfile |
| Free text stored in full, never truncated | spec edge cases | all prose fields |
| One source language per entry | FR-009, gate G2 | all content-bearing entities |
| Proposals excluded from profile reads | FR-018, gate G6 | ProposedEntry |
| Snapshots immutable after insert | FR-029 | EntrySnapshot |
