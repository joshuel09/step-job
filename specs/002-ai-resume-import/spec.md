# Feature Specification: AI Resume Import

**Feature Branch**: `25-specify-resume-import`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "AI resume import — extract structured career information from a PDF, DOCX, or pasted text and deliver it into the Master Career Profile's review queue as proposed entries, so the user approves everything before it becomes part of their profile."

## Clarifications

### Session 2026-09-22

- Q: How long is the source evidence for each extracted value retained, given the uploaded document itself is discarded? → A: Until the proposal is accepted or rejected, then discarded with the review decision
- Q: Does an import complete while the user waits, or continue in the background? → A: Wait first, and hand off to the background if it takes longer than a few seconds
- Q: What happens when a source document contradicts itself? → A: Propose what the document says, flag the conflict, and let the user resolve it in review
- Q: What should a user see when the extraction service is unavailable? → A: Retry a few times automatically, then report that the service is unavailable and the document was not used
- Q: Is a record of past imports kept once their proposals have been reviewed? → A: A minimal record — the kind of source and when it ran — without the filename

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Paste my career and let the system structure it (Priority: P1)

A user has their career written down somewhere — an old resume, a profile on a
job platform, a document they keep for themselves. Rather than retyping it, they
paste it in. The system reads it and proposes structured entries: roles,
education, skills, languages. Each proposed value shows the words in the pasted
text it came from, so the user can see it was read rather than guessed. Nothing
enters their profile until they accept it.

**Why this priority**: it removes the largest barrier to a complete profile,
which everything else in the product depends on. Pasting exercises the entire
extraction path — reading, structuring, evidencing, proposing — without file
handling, so it is the smallest slice that delivers the feature's actual value.

**Independent Test**: paste career text containing at least two roles and some
skills; proposals appear in the review queue, each carrying its source evidence;
the profile itself is unchanged until the user accepts.

**Acceptance Scenarios**:

1. **Given** a user with an empty profile, **When** they paste text describing
   two roles, **Then** two work experience proposals are created and appear in
   the review queue.
2. **Given** a proposal created from pasted text, **When** the user views it,
   **Then** each extracted field is shown alongside the words in the source it
   came from.
3. **Given** text that states an employer and dates but no job title, **When**
   extraction runs, **Then** the job title is left empty and marked as not found
   rather than inferred from context.
4. **Given** proposals created by extraction, **When** the user looks at their
   profile, **Then** none of the proposed entries appear there.
5. **Given** pasted text that contains no recognisable career information,
   **When** extraction runs, **Then** no proposals are created and the user is
   told what was missing.

---

### User Story 2 - Import the resume file I already have (Priority: P2)

A user uploads a resume as a PDF or a DOCX. The system reads the document,
proposes the same structured entries, and then discards the file. Their original
stays where it always was, on their own machine.

**Why this priority**: it is how most people actually hold their career history,
so it materially widens who can use the feature. It follows P1 because it adds
document handling on top of an extraction path that must already work.

**Independent Test**: upload a PDF and a DOCX containing the same career
information; both produce equivalent proposals; neither file is still held by
the system afterwards.

**Acceptance Scenarios**:

1. **Given** a PDF resume with selectable text, **When** the user uploads it,
   **Then** proposals are created from its contents.
2. **Given** a DOCX resume, **When** the user uploads it, **Then** proposals are
   created from its contents.
3. **Given** a completed import, **When** the user checks what the system holds,
   **Then** the uploaded document is no longer stored.
4. **Given** a scanned PDF with no readable text, **When** the user uploads it,
   **Then** they are told the document contains no text that can be read, and no
   proposals are created.
5. **Given** a file that is not a resume or is in an unsupported format, **When**
   the user uploads it, **Then** they are told plainly and nothing is created.

---

### User Story 3 - Import my 職務経歴書 as it is written (Priority: P3)

A user imports a Japanese 職務経歴書. Its conventions — a summary section, roles
in reverse order, responsibilities in tables — are read as the structure they
are. The resulting entries stay in Japanese, because that is the language the
user wrote them in.

**Why this priority**: it is what makes the feature useful to the people this
product is for, but it builds on extraction that must already work for ordinary
documents. Getting it wrong is worse than not having it, so it follows P1 and P2.

**Independent Test**: import a 職務経歴書 containing a 職務要約 and two roles;
entries are proposed with their Japanese text intact and their source language
recorded as Japanese.

**Acceptance Scenarios**:

1. **Given** a 職務経歴書 with a 職務要約 and two roles, **When** it is imported,
   **Then** two work experience proposals are created with their Japanese text
   unchanged.
2. **Given** a document written in Japanese, **When** entries are proposed,
   **Then** each records Japanese as the language it was written in.
3. **Given** a document containing both Japanese and English sections, **When**
   entries are proposed, **Then** each entry records the language of the text it
   came from, and no text is translated.
4. **Given** dates written in a Japanese era format, **When** they are extracted,
   **Then** they are converted to calendar dates, and the original text remains
   visible as the evidence for that value.

---

### Edge Cases

- A document with no text layer, such as a photographed or scanned page. The
  user is told the document cannot be read, and nothing is created.
- A password-protected or corrupt file. The user is told which, and nothing is
  created.
- A very long document, far beyond a normal resume. Either it is processed or
  the user is told it is too large; it is never silently truncated to whatever
  fitted.
- A document in a language the system does not handle. The user is told, rather
  than receiving entries extracted badly.
- Text that gives a month and year but no day, or a year alone. The date is
  recorded at the precision stated, never padded to a precision the source does
  not support.
- A resume states an end date earlier than its start date. Both are proposed as
  written, with the conflict flagged, because the user knows which is wrong and
  the system does not.
- The same role appears twice with different dates. One entry is proposed, the
  disagreement is flagged, and both readings are visible in the evidence.
- Text listing a role with no employer, or an employer with no role. The entry is
  proposed with the missing field empty and marked as not found.
- Overlapping roles in the source. Both are proposed; overlapping employment is
  legitimate.
- The same role appearing twice in one document, such as a summary repeating the
  detail. One proposal is created, not two.
- A user imports a second document describing career they have already entered
  by hand. Proposals are still created, and the existing review queue flags the
  possible duplicates.
- Extraction fails part way through. No partial set of proposals is created; the
  user is told it failed and can try again.
- The extraction service is briefly unavailable. The system retries and the user
  never learns anything went wrong.
- The extraction service stays unavailable. The user is told the service is down
  rather than that their document was faulty, so they know to return later.
- A user starts an import and navigates away. The import either completes and the
  proposals are waiting, or it fails and says so; it does not hang unresolved.
- An import is handed off to the background and the user closes the browser
  entirely. It still completes, and its outcome is waiting when they return.
- A user starts a second import while the first is still running in the
  background. Both run and both produce their own result; neither replaces the
  other.

## Requirements *(mandatory)*

### Functional Requirements

**Accepting a source**

- **FR-001**: Users MUST be able to import career information by pasting text.
- **FR-002**: Users MUST be able to import career information by uploading a PDF
  or a DOCX document.
- **FR-003**: The system MUST tell the user which formats it accepts before they
  try, and MUST reject anything else with a reason rather than a generic failure.
- **FR-004**: The system MUST NOT retain an uploaded document once extraction has
  finished or failed.
- **FR-005**: The system MUST report progress while an import is running, and
  MUST reach a definite outcome — proposals created, or a stated reason why not.
- **FR-005a**: An import MUST attempt to complete while the user waits. If it has
  not finished within a few seconds, it MUST continue in the background and the
  user MUST be free to leave the screen without losing it.
- **FR-005b**: A user MUST be able to see that an import is still running, and
  MUST be told when its proposals are ready, whether or not they stayed on the
  screen.
- **FR-005c**: An import that has been handed off MUST reach the same outcomes as
  one completed in place. Being slow MUST NOT change what is produced, and MUST
  NOT relax FR-017 — a failure in the background still creates no proposals.

**Extracting**

- **FR-006**: The system MUST extract work experience, education,
  certifications, skills and languages where the source contains them.
- **FR-007**: The system MUST record, for every extracted field, the passage of
  source text that field was taken from.
- **FR-008**: The system MUST NOT populate a field that the source does not
  support. A field with no supporting passage MUST be left empty and marked as
  not found.
- **FR-009**: The system MUST NOT infer, round, complete or embellish any value.
  Dates MUST be recorded at the precision the source states. Titles,
  responsibilities and achievements MUST come from the document, not from what a
  role of that kind usually involves.
- **FR-010**: The system MUST record, for each extracted entry, the language the
  source text was written in, and MUST NOT translate content during extraction.
- **FR-011**: The system MUST convert dates written in other calendar
  conventions, including Japanese era years, into calendar dates, while keeping
  the original text as the evidence for that value.
- **FR-012**: Where one document describes the same role more than once, the
  system MUST propose it once.
- **FR-012a**: Where a source contradicts itself — the same role given different
  dates, or a date range that ends before it begins — the system MUST propose
  what the document states and MUST mark the conflict, naming the fields that
  disagree.
- **FR-012b**: The system MUST NOT resolve a contradiction by choosing the more
  likely reading. Deciding what a user's career was, rather than reporting what
  the document says, is the fabrication Principle IV forbids.
- **FR-012c**: A flagged conflict MUST be resolvable by the user during review,
  and the entry MUST be acceptable once they have corrected it.

**Delivering into review**

- **FR-013**: The system MUST deliver extracted entries to the Master Career
  Profile's review queue as proposed entries, recording the import as their
  source.
- **FR-014**: The system MUST NOT write to the profile directly. Nothing extracted
  may reach the profile except by the user accepting it in review.
- **FR-015**: Each proposal MUST carry its source evidence through to review, so
  the user can see what each value was based on before accepting it.
- **FR-015a**: Source evidence MUST be discarded when its proposal is accepted or
  rejected. It exists so the user can judge a value before accepting it; once
  that judgement is made, retaining fragments of a resume — which may state
  residence status, an address or a previous salary — serves no remaining
  purpose.
- **FR-015b**: Discarding evidence MUST NOT alter the accepted entry. What the
  user approved stays in the profile exactly as approved.
- **FR-016**: Where extraction produces nothing usable, the system MUST create no
  proposals and MUST tell the user what it could not find.
- **FR-017**: Where extraction fails part way, the system MUST create no
  proposals at all rather than an incomplete set.
- **FR-017a**: Where the extraction service is unavailable or does not respond,
  the system MUST retry a limited number of times before giving up. A brief
  outage MUST NOT cost the user their import.
- **FR-017b**: Once retries are exhausted, the system MUST tell the user that the
  service is unavailable and that their document was not used, distinguishing
  this from a document it could not read. The two have different remedies: one
  is worth trying again later, the other never will be.
- **FR-017c**: The system MUST NOT retry indefinitely. A user MUST NOT be left
  waiting on a recovery that may not come.
- **FR-017d**: A failed import MUST leave nothing behind — no proposals, and no
  retained document.

**Keeping the user in control**

- **FR-018**: Users MUST be able to see what was extracted before anything is
  proposed to them, and MUST be able to abandon an import without it reaching
  the review queue.
- **FR-019**: Users MUST be able to import more than once, and each import MUST be
  distinguishable in review by what it came from.
- **FR-019a**: The system MUST keep a record of each import — the kind of source
  and when it ran — after its proposals have been reviewed, so a user can see
  where an entry in their profile originally came from.
- **FR-019b**: That record MUST NOT include the uploaded filename. A name such as
  the company someone was applying to reveals their job search, and nothing in
  this feature needs it once extraction is done.
- **FR-019c**: Import records MUST be erased with the profile, on the same terms
  as the entries they produced.
- **FR-020**: The system MUST NOT begin an import without the user starting it.

### Key Entities

- **Import**: one attempt to bring career information in from a source, with its
  kind — pasted text, PDF, DOCX — its outcome, and when it ran. Deliberately not
  the filename: it survives the import, and a name can reveal where someone was
  applying.
- **Extracted Entry**: a single piece of career information found in a source,
  before it becomes a proposal: what kind of entry it is, its fields, the
  language it was written in, and the evidence for each field.
- **Source Evidence**: the passage of the original text a particular field was
  taken from, kept so the user can see the basis for a value rather than trusting
  it.
- **Extraction Outcome**: what happened — what was found, what was looked for and
  not found, and, where it failed, why in terms the user can act on.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with an existing resume can go from starting an import to a
  reviewable set of proposals in under two minutes.
- **SC-002**: 100% of proposed field values can be shown alongside the source
  text they were taken from.
- **SC-003**: 0% of proposed fields contain information that does not appear in
  the source document, including where the source contradicts itself.
- **SC-003a**: 100% of self-contradictory entries are flagged rather than
  silently resolved.
- **SC-004**: 100% of extracted entries pass through review; none reach a profile
  without the user accepting them.
- **SC-005**: A user importing a complete resume spends less than a quarter of
  the time they would have spent entering the same career by hand.
- **SC-006**: 100% of uploaded documents are no longer held by the system once
  the import has finished or failed.
- **SC-006a**: 100% of source evidence is discarded once its proposal has been
  reviewed; none survives an accepted or rejected proposal.
- **SC-007**: Every import reaches a stated outcome; none are left in an
  indeterminate state, whether it finished while the user waited or after they
  left the screen.
- **SC-007a**: A user who leaves during an import finds its result waiting for
  them, in 100% of cases.
- **SC-007b**: A failed import leaves no proposals and no retained document, in
  100% of cases.
- **SC-009**: A user can tell where any profile entry originally came from, for
  100% of entries created by import.
- **SC-008**: 90% of users importing a resume accept at least one proposal
  without needing to correct it first.

## Assumptions

- **The review queue already exists and is not respecified here.** Specification
  001 defines what happens to a proposal once it exists — review, correction,
  acceptance, rejection, duplicate detection and merging (FR-017 to FR-020 and
  FR-032 to FR-034 of that specification). This feature ends at submitting
  proposals with their source and evidence.
- **Platform imports are out of scope.** Connecting to a job platform to read a
  profile is a separate feature. Text a user copies from such a profile and
  pastes in is simply pasted text, and is in scope.
- **One language per entry, detected from the source.** Following FR-009 of
  specification 001, an entry has one language it was written in. A document
  mixing languages produces entries in the languages they were written in;
  nothing is translated during import.
- **Uploaded documents are not retained.** The document holds everything
  specification 001 protects — nationality, residence status, visa details — so
  it is discarded once extraction ends. The user keeps their original. This
  mirrors the decision not to retain generated exports.
- **Extraction quality is bounded by the source.** A vague or badly structured
  document yields fewer entries. That is a correct outcome, not a defect: the
  alternative is inventing the missing parts.
- **Authentication exists**, and an import belongs to the user who started it.
- **Documents are of ordinary resume length.** A handful of pages, not hundreds.
