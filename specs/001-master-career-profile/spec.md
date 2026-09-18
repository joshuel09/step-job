# Feature Specification: Master Career Profile

**Feature Branch**: `5-master-career-profile`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "Master Career Profile — the canonical record of a user's career that every generated document derives from."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Describe my career once (Priority: P1)

A job seeker signs up and records their career: who they are, where they have
worked, what they studied, the skills and languages they have, and what they are
looking for. They can return at any time to correct or extend any part of it.
Nothing they enter is thrown away, and nothing has to be entered twice.

**Why this priority**: this is the product's foundational promise and the source
of truth every other feature reads. Without it there is nothing to generate a
resume from and nothing to ground an AI claim against. It is the smallest slice
that delivers standalone value: a structured, durable record of a career is
useful even before a single document is produced.

**Independent Test**: a new user can complete a profile containing at least one
work experience, one education entry, and a set of skills and languages, leave
the product, return, and find every value exactly as entered.

**Acceptance Scenarios**:

1. **Given** a new user with an empty profile, **When** they add a work
   experience with employer, job title, start date, and description, **Then** the
   entry is saved and appears in their profile.
2. **Given** a saved work experience, **When** the user edits the job title and
   saves, **Then** the updated value is stored and the previous value is no
   longer presented as current.
3. **Given** a work experience marked as the user's current role, **When** they
   leave the end date empty, **Then** the entry is accepted and treated as
   ongoing.
4. **Given** a profile with entries in several sections, **When** the user signs
   out and signs back in, **Then** every entry is present and unchanged.
5. **Given** a work experience the user no longer wants, **When** they delete it,
   **Then** it is removed from the profile and the user is told what else
   referenced it, if anything did.

---

### User Story 2 - Keep my accomplishments so I can reuse them (Priority: P2)

Users forget what they achieved. A user records a specific accomplishment as a
structured story — the situation, the challenge, what they did, and what
resulted — and links it to the job where it happened. Months later, when
preparing a resume or an interview answer, that accomplishment is still there in
their own words.

**Why this priority**: it materially raises the quality of everything generated
later and is the main defence against a user having to reconstruct their own
history from memory. It is valuable on its own, but only once there are work
experiences for stories to attach to, so it follows P1.

**Independent Test**: a user can create a career story against an existing work
experience, sign out and back in, and retrieve it in full with its link intact.

**Acceptance Scenarios**:

1. **Given** a saved work experience, **When** the user adds a career story with
   challenge, action, and result, **Then** the story is saved and linked to that
   experience.
2. **Given** a career story, **When** the user views the linked work experience,
   **Then** the story is listed alongside it.
3. **Given** a career story linked to a work experience, **When** the user
   deletes that work experience, **Then** the user is warned that linked stories
   exist and must confirm before the deletion proceeds.
4. **Given** a set of career stories, **When** the user searches their stories by
   keyword, **Then** matching stories are returned.

---

### User Story 3 - Review what was extracted before it becomes mine (Priority: P3)

A user brings career information in from an outside source rather than typing it.
The proposed entries do not silently become part of their profile: they arrive in
a review queue where the user sees each proposed entry, edits anything that is
wrong, and accepts or rejects it. Only accepted entries enter the profile.

**Why this priority**: it removes the largest barrier to a complete profile, but
the profile must exist and be editable before there is anywhere for proposals to
land. This story defines the contract an import source delivers into; the import
and extraction mechanism itself is a separate feature.

**Independent Test**: proposed entries submitted to the review queue can be
listed, edited, accepted, and rejected, and only accepted entries appear in the
profile — testable with proposals from any source, including a manual test
fixture.

**Acceptance Scenarios**:

1. **Given** proposed entries in the review queue, **When** the user views the
   queue, **Then** each proposal is shown with its content and the source it came
   from.
2. **Given** a proposed work experience with an incorrect job title, **When** the
   user corrects the title and accepts it, **Then** the corrected version enters
   the profile and the original proposal is not retained as profile data.
3. **Given** a proposed entry, **When** the user rejects it, **Then** it does not
   enter the profile.
4. **Given** a proposal that duplicates an existing profile entry, **When** the
   user views it, **Then** the possible duplicate is indicated and the user can
   merge it into the existing entry instead of creating a second one.
5. **Given** an unreviewed proposal, **When** any other feature reads the
   profile, **Then** the proposal is absent from the results.

---

### Edge Cases

- A work experience whose end date precedes its start date is rejected with an
  explanation rather than saved.
- Two work experiences overlap in time. This is legitimate — concurrent roles,
  contract work — and is accepted without warning.
- A user has a single-name legal name, or a name that does not separate into
  given and family parts. The profile accepts it.
- A user has no formal education entries. The profile is valid without them.
- A user's current role has no end date, and a second role is also marked
  current. Both are accepted.
- A career story is written against a work experience that is later found to be a
  duplicate and merged. The story follows the surviving experience rather than
  being orphaned.
- A user deletes their entire profile. Every entry, story, and pending proposal
  is removed, and the user is told what will be lost before it happens.
- A proposal arrives for a section the user has already completed. It is queued
  as a possible duplicate rather than overwriting existing data.
- A user enters a very long free-text description. It is stored in full rather
  than silently truncated.

## Requirements *(mandatory)*

### Functional Requirements

**Profile content**

- **FR-001**: Users MUST be able to record and edit personal identity
  information, including name in Latin characters and, optionally, name in
  Japanese characters with its phonetic reading.
- **FR-002**: Users MUST be able to record multiple work experiences, each with
  employer, job title, start date, optional end date, employment type, and a
  free-text description of responsibilities.
- **FR-003**: Users MUST be able to record education entries, certifications,
  skills, and languages with a stated proficiency for each language.
- **FR-004**: Users MUST be able to record what they are looking for next,
  including desired roles, locations, working arrangement, and salary
  expectations.
- **FR-005**: Users MUST be able to record Japan-specific circumstances relevant
  to hiring, including residence status, work authorisation, visa type and
  expiry, and Japanese language qualifications.
- **FR-006**: Every field described in FR-005 MUST be optional, and the user MUST
  be able to control, per field, whether it may appear in any generated document.
  The default for these fields MUST be to withhold them.
- **FR-007**: Users MUST be able to record career stories capturing a challenge,
  the action they took, and the result, and MUST be able to link each story to a
  work experience.

**Canonical source of truth**

- **FR-008**: The profile MUST be the single source of career information. No
  other feature may ask a user for information the profile already holds.
- **FR-009**: Every entry MUST record one user-authored source language. Any
  other language version of that entry is a generated output derived from it, not
  a second independently editable source.
- **FR-010**: Every entry MUST be individually addressable so that any statement
  in a generated document can be traced back to the specific entries that
  support it.
- **FR-011**: The system MUST NOT alter the meaning of user-authored content when
  storing it.

**Editing and lifecycle**

- **FR-012**: Users MUST be able to create, edit, and delete any entry in their
  profile at any time.
- **FR-013**: Before deleting an entry, the system MUST tell the user what else
  references it and require confirmation.
- **FR-014**: The system MUST validate that date ranges are coherent and reject
  an end date earlier than its start date with an explanation.
- **FR-015**: The system MUST accept a profile that is incomplete, and MUST be
  able to report which sections are empty so the user can see what is missing.
- **FR-016**: Users MUST be able to export their complete profile in a portable
  form, and MUST be able to delete it entirely.

**Proposed entries**

- **FR-017**: The system MUST accept proposed entries from an external source and
  hold them in a review queue, recording which source each proposal came from.
- **FR-018**: Proposed entries MUST NOT form part of the profile, and MUST NOT be
  visible to any feature reading the profile, until the user accepts them.
- **FR-019**: Users MUST be able to edit a proposed entry before accepting it,
  and MUST be able to reject it outright.
- **FR-020**: The system MUST identify a proposal that appears to duplicate an
  existing entry and offer to merge it rather than create a duplicate.

### Key Entities

- **Career Profile**: the root record belonging to one user; owns every entry
  below and represents the user's complete career history.
- **Identity**: the user's names, including optional Japanese name and phonetic
  reading, and contact details.
- **Japan Profile**: residence status, work authorisation, visa type and expiry,
  and Japanese language qualifications, each with its own disclosure setting.
- **Work Experience**: one role at one employer over a period of time, with
  responsibilities; may be ongoing.
- **Education**: a course of study at an institution, with a period and
  qualification obtained.
- **Certification**: a named credential, with issuer and date, optionally
  expiring.
- **Skill**: a named capability, optionally with a self-assessed level and the
  work experiences where it was used.
- **Language**: a language with a stated proficiency and any formal
  qualification.
- **Career Preference**: what the user is seeking next.
- **Career Story**: a structured accomplishment — challenge, action, result —
  optionally linked to a work experience.
- **Proposed Entry**: career information suggested by an external source, with
  the source recorded, awaiting the user's review; becomes a profile entry only
  on acceptance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who has their career details to hand can record a usable
  profile — identity, at least one work experience, education, skills, and
  languages — in under 15 minutes.
- **SC-002**: 100% of statements in any document generated from the profile can
  be traced to the specific profile entries that support them.
- **SC-003**: No user is asked for the same piece of career information twice
  anywhere in the product.
- **SC-004**: 100% of externally proposed entries pass through user review before
  entering the profile; none appear in the profile unreviewed.
- **SC-005**: 90% of users successfully add a second work experience without
  assistance after adding their first.
- **SC-006**: A user can locate and reuse an accomplishment they recorded at
  least three months earlier in under one minute.
- **SC-007**: Every profile value a user enters is still present and unchanged
  when they next sign in, in 100% of cases.
- **SC-008**: A user can export or delete their entire profile within one minute
  of deciding to.

## Assumptions

- **Import is a separate feature.** This specification defines the review-and-
  accept contract that an import source delivers into. Extracting career
  information from resumes, profiles, or pasted text is a distinct first-release
  item and is not specified here.
- **Document generation is out of scope.** The profile is the input to resume,
  application, and interview features; producing those outputs is specified
  separately.
- **One source language per entry.** Where a user's career must be presented in
  both Japanese and English, the user authors each entry once in one language and
  other language versions are generated from it. This follows from the profile
  being the single source of truth and from every generated claim needing to
  trace back to user-authored content. Entries in different languages may coexist
  in one profile.
- **Japan-specific fields are sensitive and optional.** They are withheld from
  generated documents by default because they carry discrimination risk; the user
  opts each one in.
- **Authentication exists.** This feature assumes an authenticated user and does
  not specify sign-up or sign-in.
- **Single-user profiles.** Each profile belongs to exactly one user. Sharing,
  collaboration, and recruiter access are out of scope.
- **Users may be mid-career with many entries.** The profile is expected to hold
  dozens of entries across sections, not thousands.
