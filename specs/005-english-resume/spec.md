# Feature Specification: English Resume Generator

**Feature Branch**: `73-english-resume-spec`

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "English resume generator — the fifth item of the eight-item first release. An English-language resume produced from the Master Career Profile, for foreign-affiliated employers in Japan and for applications abroad."

## Context

This is the first document in the product written for a reader who is not
Japanese, and almost every convention inverts.

The 履歴書 carries a photograph, a date of birth and an address because a
Japanese employer expects them. On an English resume those same details are a
liability: in most of the markets this document is sent to, asking for them —
or volunteering them — invites a discrimination claim, and a screener may
discard the document rather than risk handling it. What feature 003 was careful
to include, this feature must be equally careful to leave out.

The harder problem is language. Feature 003 set a clear precedent: the product
does **not** translate on the user's behalf. Its readiness report names the
entries that have no Japanese version and leaves writing one to the user, on the
grounds that putting words in someone's mouth about their own career is exactly
what Principle IV forbids.

The mirror of that precedent is uncomfortable. A user whose profile is written
in Japanese — which is most of this product's users — would receive an English
resume that a non-Japanese reader cannot read, which is no document at all.
Principle IV does permit translation: *"Rewriting, translating and reformatting
verified facts is permitted; introducing scope, seniority, duration, headcount or
outcomes that the profile does not support is not."* But translation is where
that line is thinnest. 課長 can be rendered "Manager", "Section Chief" or
"Department Head", and those are three different claims about seniority. The
choice of English word is itself a claim.

How this feature resolves that is its central open question, and it is left open
rather than guessed.

## Clarifications

### Session 2026-10-07

- Q: How is an entry recorded in Japanese handled? → A: A model drafts the English, the user confirms or edits each line, and the approved text is saved to their profile as that entry's English version. Document generation itself stays deterministic, assembled from confirmed profile data. The model assists the user in filling their profile; it never writes the document.
- Q: How are employer, institution and certification names handled? → A: The profile holds an optional English name per organisation. Where the user supplied one it is used; where they did not, the Japanese appears as recorded. Never transliterated or guessed.
- Q: Which English convention? → A: A US-style resume only. Other conventions may be added later as their own work.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn my profile into an English resume (Priority: P1) 🎯 MVP

A user applying to a foreign-affiliated employer asks for an English resume and
receives a document they could send today. It leads with their name and contact
details, then their experience newest first — employer, title, dates and what
they did — followed by education, skills and certifications. It reads as a
resume, not as a translated Japanese form.

**Why this priority**: it is the feature. Everything else governs how it reads.

**Independent Test**: record two employers and generate. Both appear newest
first, with the dates in a Western format, and nothing appears that the profile
does not hold.

**Acceptance Scenarios**:

1. **Given** a profile with two employers, **When** the user generates an English resume, **Then** both appear in reverse-chronological order with employer, title and period.
2. **Given** a profile with recorded skills and certifications, **When** the user generates, **Then** they appear in their own sections.
3. **Given** a generated resume, **When** the user inspects any statement, **Then** the profile entry that produced it can be named.
4. **Given** a generated resume, **When** the user reads the dates, **Then** they follow a Western convention and no Japanese era appears anywhere.
5. **Given** a profile with no career history, **When** the user generates, **Then** generation is refused with what is missing named.

---

### User Story 2 - Get my Japanese career into English (Priority: P2)

A user whose profile is written in Japanese asks for an English resume and is
told, before anything is generated, which entries have no English version. For
each one the product offers a draft translation. The user reads it, corrects
what is wrong, and approves it — and the approved words are saved to their
profile, not just used once. The next document needs no translation at all.

The product never puts an unapproved translation in a document. A model drafts;
the user decides; the document is assembled from what the user approved.

**Why this priority**: without it, a user whose profile is in Japanese receives
a document a non-Japanese reader cannot use, which is no document at all — and
that is most of this product's users. It ranks below producing the resume only
because a user whose profile is already in English needs none of it.

**Independent Test**: record an entry in Japanese, run the translation step,
approve a corrected draft, and confirm the approved English is in the profile
and appears in the next document without being translated again.

**Acceptance Scenarios**:

1. **Given** entries with no English version, **When** the user asks to generate, **Then** they are told which entries those are before a document is produced.
2. **Given** a Japanese entry, **When** the user requests a draft, **Then** a translation is offered for review rather than placed in a document.
3. **Given** a draft the user edits and approves, **When** it is saved, **Then** the approved text is stored on that profile entry as its English version.
4. **Given** an entry with an approved English version, **When** the user generates again, **Then** the stored text is used and no new translation is produced.
5. **Given** a draft the user has not approved, **When** a document is generated, **Then** the draft does not appear in it.
6. **Given** an approved translation, **When** the document is compared with it, **Then** the document contains the user's approved words exactly.

---

### User Story 3 - Leave out what does not belong (Priority: P3)

The profile holds a date of birth and an address because the 履歴書 needs them.
It may hold nationality, visa status and other Japan-specific details behind
disclosure flags. None of that belongs on an English resume, and a user should
not have to know that in order to be protected from it.

The resume carries no photograph, no date of birth, no age, no gender, no
marital status and no nationality — not as empty fields, but absent.

**Why this priority**: it is what separates an English resume from a translated
履歴書. A document carrying a date of birth marks the applicant as unfamiliar
with the convention, and in some markets it is actively harmful to them.

**Independent Test**: populate every personal field the profile can hold,
generate, and confirm none of them appears anywhere in the document.

**Acceptance Scenarios**:

1. **Given** a profile with a date of birth recorded, **When** the user generates an English resume, **Then** neither the date of birth nor any age derived from it appears.
2. **Given** a profile with Japan-specific details recorded and disclosed, **When** the user generates, **Then** none of them appears — a disclosure flag governs Japanese documents, not this one.
3. **Given** any generated resume, **When** it is inspected, **Then** it contains no photograph and no placeholder for one.
4. **Given** a profile with a full address, **When** the user generates, **Then** the document carries at most the contact details a resume conventionally shows.

---

### User Story 4 - Say only what I have said (Priority: P4)

A user whose profile is thin gets a short resume. An employer with no recorded
description gets its title and dates. Nothing asserts scope, seniority,
duration, team size or outcome the profile does not support — and where the
document is rendered in English from an entry written in another language, the
English must not claim more than the original did.

**Why this priority**: the constitutional constraint, made testable. Last only
because it is most readily checked once a document exists; in importance it
outranks every story above it and is not tradeable against how well the resume
reads.

**Independent Test**: record an employer with a title and dates and nothing
else, generate, and confirm the document says exactly that much.

**Acceptance Scenarios**:

1. **Given** an employer with no recorded description, **When** the user generates, **Then** it appears with title and dates and no invented summary.
2. **Given** any generated resume, **When** its claims are compared with the profile, **Then** every statement about scope, seniority, duration, team size or outcome traces to an entry that supports it.
3. **Given** an entry rendered into English from another language, **When** the English is compared with the original, **Then** it claims neither more seniority nor more scope than the original.
4. **Given** a section for which the profile holds nothing, **When** the document is produced, **Then** the section is absent rather than present and empty — an English resume omits what it has nothing to say about.

---

### Edge Cases

- A profile written entirely in Japanese: the user is told before generating, offered a draft for each entry, and the document is assembled from what they approve.
- A profile written entirely in English: no language handling is needed at all, and the document should be straightforward.
- A profile mixing both: the resulting document must not switch language mid-sentence or mid-section.
- An employer whose only recorded name is Japanese: it appears as recorded, never guessed at, and the readiness report names it so the user can supply the official English name.
- A user who approves a draft and later edits the underlying Japanese entry: the stored English no longer matches its source, and the user must be able to find out.
- A user who approves an empty or whitespace translation: an approved blank is not an English version.
- A career long enough to exceed the conventional length: a resume is conventionally short, and shortening is done by the user choosing what to include, never by the system silently dropping entries.
- The same profile generating a 履歴書 and an English resume: the two must not disagree on any fact both carry, even though they present it differently.
- A user who edits a profile entry after sending the resume: what was sent stays inspectable.

## Requirements *(mandatory)*

### Functional Requirements

**Producing the document**

- **FR-001**: The system MUST produce an English resume from the Master Career Profile, requiring no career information the profile does not already hold.
- **FR-002**: The system MUST present experience in reverse-chronological order, newest first.
- **FR-003**: The system MUST include, where the profile holds them, the user's name, contact details, experience, education, skills and certifications.
- **FR-004**: The system MUST write all dates in a Western convention and MUST NOT use Japanese era years anywhere in the document.
- **FR-005**: The system MUST NOT retain the generated document; the profile and the record of what the document drew on are what persist.
- **FR-006**: The system MUST refuse to generate when the profile holds no career history, naming what is missing.
- **FR-007**: The system MUST produce every entry it includes in full rather than truncating entries to reach a conventional length.

**What must not appear**

- **FR-008**: The system MUST NOT include a photograph or any placeholder for one.
- **FR-009**: The system MUST NOT include date of birth, age, gender, marital status or nationality, and MUST NOT include any value derived from them.
- **FR-010**: The system MUST NOT include Japan-specific details such as visa or residence status, regardless of their disclosure flags; those flags govern Japanese documents and MUST NOT be read as consent to disclose on this one.
- **FR-011**: The system MUST omit a section entirely where the profile holds nothing for it, rather than showing an empty heading.

**Truthfulness**

- **FR-012**: The system MUST NOT state scope, seniority, duration, team size or outcome that the profile does not support.
- **FR-013**: Where an entry's English version came from a drafted translation, the approved English MUST NOT claim more seniority, scope or responsibility than the original. The user approving the wording is what makes it theirs; the draft is a suggestion, never a claim the product makes on their behalf.
- **FR-014**: Every statement in the document MUST be traceable to the profile entry that produced it.
- **FR-015**: The system MUST record what each generated document drew on, and that record MUST remain accurate after the underlying entries are edited or deleted.
- **FR-016**: An English resume and a 履歴書 generated from the same profile MUST NOT disagree on any fact both carry.

**Language**

- **FR-017**: The system MUST store an English version per profile entry, and MUST assemble the document from stored English rather than translating while generating. Document generation itself MUST remain deterministic and MUST NOT call a model.
- **FR-018**: The system MUST offer a drafted translation for any entry with no stored English version, and MUST NOT place a draft in a document until the user has approved it. An approved draft MUST be saved to the profile as that entry's English version, so the same work is never asked for twice (Principle I).
- **FR-019**: The system MUST let the user edit a draft before approving it, and MUST use the user's approved wording exactly.
- **FR-020**: The system MUST tell the user which entries have no stored English version before producing a document, rather than after.
- **FR-021**: The system MUST use a stored English name for an employer, institution or certification where the user supplied one, and MUST otherwise show the name as recorded. It MUST NOT transliterate or otherwise guess a proper noun, because a guessed name misnames a real organisation on a document an employer may verify.

**Convention**

- **FR-022**: The document MUST follow a US-style resume convention: reverse-chronological, concise, carrying no personal details and no references. Other English conventions are out of scope for this feature.

### Key Entities

- **Resume request**: what the user chose for this document. Affects presentation only, never content.
- **English version of an entry**: the user-approved English wording stored against a profile entry. Written once, reused by every later document.
- **Translation draft**: a model's suggestion for an entry with no English version. It exists only until the user approves, edits or discards it, and never reaches a document unapproved.
- **Resume section**: one part of the document — experience, education, skills, certifications — present only when the profile holds something for it.
- **Experience entry**: one employer's portion — employer, title, period and what the role involved, each drawn from a profile entry.
- **Document record**: what a generated document drew on, captured at generation and unchanged afterwards. The same machinery the 履歴書 uses.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with a populated profile obtains a complete English resume without typing any career information the profile already holds.
- **SC-002**: Across every personal field the profile can hold — date of birth, age, gender, marital status, nationality, visa and residence status, photograph — zero appear in any generated English resume.
- **SC-003**: No Japanese era year appears in any generated English resume.
- **SC-004**: Every factual statement in a generated resume traces to the profile entry that produced it, with no unattributable statements.
- **SC-005**: A profile section the user has not filled in produces no heading and no content.
- **SC-006**: Where an entry is rendered into English from another language, a reviewer comparing the two finds no increase in claimed seniority, scope or responsibility.
- **SC-007**: An English resume and a 履歴書 generated from the same profile agree on every employer, title and period that both carry.
- **SC-008**: A document generated before a profile edit still shows what it drew on after that edit.
- **SC-009**: A user whose profile is written in Japanese is never handed a document they cannot read without being told so first.
- **SC-010**: No unapproved translation appears in any generated document, measured as zero drafts reaching a document without an approval recorded.
- **SC-011**: An approved translation appears in the document in the user's approved wording, character for character.
- **SC-012**: Approving a translation once is enough: generating the same document again produces no new draft for that entry.
- **SC-013**: No proper noun appears in a form the user did not supply and the profile does not hold.

## Assumptions

- The Master Career Profile holds what this document needs — employers, titles, periods, descriptions, education, skills and certifications. Where it does not, Principle I requires extending the profile rather than collecting the data inside this feature.
- The record of what a document drew on reuses the same snapshot machinery as the 履歴書 rather than a new mechanism.
- Reverse-chronological is the only ordering. Unlike the 職務経歴書, an English resume has one conventional arrangement, so no choice is offered.
- No Japanese era conversion is involved; this document is Western-dated throughout.
- The embedded Japanese font is still required, because a proper noun with no supplied English name appears as recorded.
- Contact details mean the name, email address and telephone number the profile holds. A full street address is not conventional on an English resume and is excluded by FR-009's intent even though it is not a protected characteristic.
- Storing an English version per entry is a change to the Master Career Profile, not to this feature's own storage. Principle I puts new career data on the profile, so the schema change belongs to the profile's feature and this one depends on it. Planning should sequence that first.
- A model is involved in this feature, but only in drafting a translation for the user to approve. No model is called while a document is generated, which keeps the generator deterministic as feature 004 settled.
- References are out of scope. "References available on request" is a convention the product does not need to assert on the user's behalf.
- A cover letter is a separate document and is not part of this feature.
- The document is generated and handed over, never stored or edited in place.
