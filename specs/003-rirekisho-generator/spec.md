# Feature Specification: 履歴書 Generator

**Feature Branch**: `43-specify-rirekisho`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "履歴書 generator — produce a Japanese rirekisho from the Master Career Profile, following the conventions Japanese employers expect, with every statement traceable to the profile entries that support it and nothing invented to fill a blank field."

## Clarifications

### Session 2026-09-30

- Q: What appears in a Japanese 履歴書 when the profile entries are written in English? → A: Render as written, and offer to add a Japanese version to the profile, which the user reviews and approves before it is used
- Q: Should the document include a field for the applicant's gender? → A: No gender field at all
- Q: Should the document include a photograph, or a frame for one? → A: A frame is drawn where convention places it, left empty; the product stores no photograph
- Q: What happens when a career history will not fit the conventional page count? → A: Produce every entry across as many pages as needed, and tell the user it exceeds the usual length
- Q: Should the document include 志望の動機 and 本人希望記入欄? → A: Both appear as labelled empty sections for the user to complete per employer

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn my profile into a 履歴書 (Priority: P1)

A user has filled in their career profile. They ask for a 履歴書 and receive one
laid out the way a Japanese employer expects: their name and reading, a single
chronological 学歴・職歴 table, their qualifications, and 以上 at the end. Every
line in it came from something they entered.

**Why this priority**: it is the feature. A user who can produce one correct
履歴書 from a profile they already filled in has received the whole value; the
options and edge cases refine it.

**Independent Test**: with a complete profile, generate a 履歴書 and confirm every
row of 学歴・職歴 corresponds to a profile entry, in the right order, with the
right conventions.

**Acceptance Scenarios**:

1. **Given** a profile with identity, education and two work experiences,
   **When** the user generates a 履歴書, **Then** they receive a document
   containing all of them.
2. **Given** that document, **When** the user looks at 学歴・職歴, **Then** the
   rows appear oldest first, with education before employment.
3. **Given** a work experience, **When** it appears in 学歴・職歴, **Then** it
   produces one row for joining and one for leaving.
4. **Given** a role the user still holds, **When** it appears, **Then** the
   leaving row reads 現在に至る rather than a date.
5. **Given** a completed 学歴・職歴 table, **When** the user reads its last line,
   **Then** it is 以上.
6. **Given** a generated document, **When** the user checks any statement in it,
   **Then** they can see which profile entry it came from.

---

### User Story 2 - Produce it the way this employer expects (Priority: P2)

Employers differ in what they expect. A user chooses whether dates are written
in 和暦 or 西暦, and whether the page is A4 or B5, and sees the result before
downloading it.

**Why this priority**: a 履歴書 in the wrong convention is not wrong information,
but it is the kind of detail that marks an applicant as unfamiliar. It follows
P1 because it is a choice about a document that must first exist.

**Independent Test**: generate the same profile twice, once in each date
convention and page size, and confirm the content is identical while the
presentation differs.

**Acceptance Scenarios**:

1. **Given** a profile, **When** the user selects 和暦, **Then** every date in the
   document is written as an era year.
2. **Given** a profile, **When** the user selects 西暦, **Then** every date is
   written as a calendar year.
3. **Given** either selection, **When** the user reads the document, **Then** one
   convention is used throughout; the two are never mixed.
4. **Given** a profile, **When** the user selects B5 rather than A4, **Then** the
   document is produced at that size with the same content.
5. **Given** any selection, **When** the user asks, **Then** they can see the
   document before deciding to download it.

---

### User Story 3 - Leave blank what I have not said (Priority: P3)

A profile is rarely complete. The user has no education entries, or has not
recorded an address, or has chosen to keep their nationality private. The
document reflects exactly that: the sections they can fill are filled, and the
rest is left for them to complete by hand.

**Why this priority**: it is what makes the feature trustworthy rather than
merely convenient, but it is only observable once documents are being produced.
A generator that quietly invents a plausible blank is worse than one that
refuses, because the user will not notice.

**Independent Test**: generate from a deliberately incomplete profile and confirm
every absent field is empty in the document, with nothing filled in on the user's
behalf.

**Acceptance Scenarios**:

1. **Given** a profile with no education entries, **When** the user generates a
   履歴書, **Then** the 学歴 section contains no rows and no placeholder text.
2. **Given** a profile with no recorded address, **When** the document is
   produced, **Then** the address field is blank.
3. **Given** a user who has not disclosed their nationality, **When** the
   document is produced, **Then** it does not appear anywhere in it.
4. **Given** a user who has disclosed their nationality, **When** the document is
   produced, **Then** it appears.
5. **Given** any generated document, **When** the user reads it, **Then** no
   statement appears that they did not enter.

---

### Edge Cases

- A work experience with no end date, still held. It renders 現在に至る.
- Two roles held at once. Both appear, ordered by when they began; the overlap is
  shown as the profile records it rather than reconciled.
- A role and an education period that overlap. Both appear in their own sections.
- A profile with employment but no education, or the reverse. The section that
  has entries is filled and the other is empty.
- A profile with no work experience at all. The document is still produced, with
  an empty 職歴 section — a first-time applicant has a legitimate 履歴書.
- A profile with no identity recorded at all. The user is told what is missing
  rather than receiving a document with an empty name.
- An entry whose start date is recorded but whose end date is not, for a role the
  user has left. It renders as ongoing, because that is what the profile says;
  correcting it is a profile edit.
- A name recorded only in Latin characters, with no Japanese form. The Latin form
  is used, and the reading is left blank rather than transliterated.
- A profile written entirely in English. The document is produced with English
  content, and the user is offered Japanese versions to add to their profile
  rather than being blocked or having one invented for them.
- A profile mixing languages. Each entry appears in the language it was written
  in; the document does not normalise them.
- A very long employment history that will not fit the conventional page count.
  Every entry is produced across as many pages as needed, and the user is told
  the document runs longer than usual.
- A qualification with no date. It appears without one.
- The profile changes after a document was generated. The earlier document is
  unaffected, and what it was based on remains inspectable.

## Requirements *(mandatory)*

### Functional Requirements

**Producing the document**

- **FR-001**: Users MUST be able to generate a 履歴書 from their career profile.
- **FR-002**: The document MUST follow the conventional layout Japanese employers
  expect, including 氏名 with its reading, 学歴・職歴, and 免許・資格.
- **FR-003**: The system MUST produce the document as a file the user can
  download and print.
- **FR-004**: Users MUST be able to see the document before downloading it.
- **FR-005**: The system MUST NOT retain the generated document after delivering
  it. The profile and its snapshot are what persist.

**The 学歴・職歴 table**

- **FR-006**: Education and employment MUST appear in one chronological table,
  oldest first, with education before employment.
- **FR-007**: Each education entry MUST produce a row for entering and a row for
  completing.
- **FR-008**: Each work experience MUST produce a row for joining and a row for
  leaving.
- **FR-009**: A role the user still holds MUST render its final row as 現在に至る
  rather than a date.
- **FR-010**: The table MUST end with 以上.
- **FR-011**: Where two entries overlap in time, both MUST appear as recorded.
  The system MUST NOT reconcile, reorder or omit either to make the history look
  tidier.

**Nothing invented**

- **FR-012**: Every statement in the document MUST come from an entry in the
  profile.
- **FR-013**: The system MUST NOT fill a field the profile does not support.
  A conventional section with no entries behind it MUST be produced empty, with
  no placeholder, sample or inferred content.
- **FR-014**: The system MUST NOT infer a value from another. A missing end date
  MUST NOT be estimated from a later entry, and a missing reading MUST NOT be
  generated from a Latin name.
- **FR-014a**: Where a profile entry is written in English, the document MUST
  render it as written. The system MUST NOT translate it during generation: a
  translated value is words the user never wrote, and would appear in a document
  they sign their name to.
- **FR-014b**: The system MAY offer to add a Japanese version of an entry to the
  profile. Any such suggestion MUST be reviewed and approved by the user before
  it is stored, and once stored it is an ordinary profile entry the user
  authored — traceable like any other.
- **FR-014c**: A user MUST be able to generate a 履歴書 without providing Japanese
  for every entry. An unusual document is the user's decision to make; being
  unable to produce one at all is not.
- **FR-015**: Where the profile lacks what the document requires to be
  meaningful — a name above all — the system MUST say what is missing rather
  than produce a document with it blank.
- **FR-016**: Each generated document MUST record what it was based on, so that
  its statements remain traceable to specific profile entries after those entries
  are edited or removed.

**What the document leaves for the user**

- **FR-022a**: The document MUST include an empty frame where convention places a
  photograph. The product MUST NOT store a photograph: holding an image of
  someone's face is a materially different commitment from holding text, and the
  user attaches one when they submit.
- **FR-022b**: The document MUST include 志望の動機 and 本人希望記入欄 as labelled
  empty sections. Both are written for a particular employer rather than held as
  career history, so the system MUST NOT generate content for either.
- **FR-022c**: Every section the document deliberately leaves empty MUST be
  labelled, so a user can see what remains for them to complete rather than
  discovering it after printing.

**Conventions the user chooses**

- **FR-017**: Users MUST be able to choose whether dates are written in 和暦 or
  西暦, and the system MUST use that choice throughout a single document.
- **FR-018**: Users MUST be able to choose the page size between A4 and B5.
- **FR-018a**: Where a career history does not fit the conventional two pages,
  the system MUST produce every entry across as many pages as it needs, and MUST
  tell the user the document is longer than usual so they can decide what to
  do. The system MUST NOT drop, shorten or summarise entries to fit: losing
  someone's career to a layout constraint is a worse outcome than an unusual
  page count, and only the user can judge which roles matter.
- **FR-019**: The system MUST apply one date convention consistently within a
  document; the two MUST NOT appear together.

**Privacy**

- **FR-020**: The system MUST NOT include any Japan-specific field from the
  profile — residence status, nationality, visa details or work authorisation —
  unless the user has marked that field as includable in generated documents.
- **FR-021**: Where such a field is included, it MUST appear only because the
  user opted it in, and the user MUST be able to withdraw it and regenerate.
- **FR-022**: The document MUST NOT contain a field asking the applicant's
  gender, blank or otherwise. The profile does not record it, so there is
  nothing to render; and for this product's users the field carries
  discrimination weight that an empty box inviting completion would not avoid.

### Key Entities

- **Generated 履歴書**: one document produced at one moment from one profile, with
  the conventions chosen for it. Not retained after delivery.
- **Document Conventions**: the choices a user makes for a document — date form
  and page size — which affect presentation and never content.
- **学歴・職歴 Row**: one line of the combined table, derived from an education or
  employment entry, carrying its date, its subject and what happened.
- **Generation Record**: what a document was based on, kept so its statements
  remain traceable after the entries behind them change.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with a complete profile can produce a 履歴書 in under one
  minute from asking for it.
- **SC-002**: 100% of statements in a generated document correspond to an entry
  in the profile it was generated from.
- **SC-003**: 0% of fields are filled with content the profile does not support.
- **SC-003a**: 0% of documents contain text translated during generation. Any
  Japanese in a document was authored or approved by the user first.
- **SC-004**: 100% of generated documents can be traced to what they were based
  on, after the profile has since changed.
- **SC-005**: 0% of generated documents contain a Japan-specific field the user
  has not marked as includable.
- **SC-006**: A user who regenerates after correcting their profile sees the
  correction reflected, in 100% of cases.
- **SC-007**: 100% of documents use a single date convention throughout.
- **SC-007a**: 0% of entries are dropped or shortened to fit a page count.
- **SC-007b**: 100% of deliberately empty sections are labelled as such.
- **SC-008**: A user reviewing a generated document can identify, for any line,
  which profile entry produced it.
- **SC-009**: 90% of users produce a document they are willing to submit without
  editing it outside the product, except for the fields the system deliberately
  leaves blank.

## Assumptions

- **The profile gains two identity fields.** A 履歴書 conventionally carries a date
  of birth and a current address, which the Master Career Profile does not hold.
  Principle I says a user tells us their career once, so these belong on the
  profile rather than being asked for per document. This feature depends on a
  small extension to specification 001 adding both as optional fields; the plan
  carries that change explicitly rather than leaving it to be discovered.
- **The photograph is out of scope.** The document draws the frame where
  convention places it and leaves it empty; the product stores no photograph,
  because holding an image of someone's face is a materially different
  commitment from holding text.
- **志望の動機 and 本人希望記入欄 are out of scope.** Both are written for a
  particular employer rather than held as career history, so they belong to a
  later application-assistant feature. The generator leaves them blank and
  labelled.
- **No gender field.** The profile does not record gender, Japanese guidance has
  treated the field as optional since 2021, and for this product's users it
  carries discrimination weight. The generator produces a form without it rather
  than an empty one inviting completion.
- **This feature makes no AI calls.** Laying out a 履歴書 is deterministic: the
  rows follow from the entries, and the date conventions follow from arithmetic.
  A model would add a fabrication surface to a feature whose entire purpose is
  that nothing is fabricated.
- **The output is a document file.** Users print 履歴書 or attach them, so the
  result is a fixed-layout file rather than a web page.
- **Entries are shown as recorded.** Where a profile is internally inconsistent —
  overlapping roles, a missing end date — the document reflects what the profile
  says. Correcting it is a profile edit, not something this feature decides.
- **Authentication exists**, and a document is generated from the profile of the
  user who asked for it.
