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

### User Story 2 - Leave out what does not belong (Priority: P2)

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

### User Story 3 - Say only what I have said (Priority: P3)

A user whose profile is thin gets a short resume. An employer with no recorded
description gets its title and dates. Nothing asserts scope, seniority,
duration, team size or outcome the profile does not support — and where the
document is rendered in English from an entry written in another language, the
English must not claim more than the original did.

**Why this priority**: the constitutional constraint, made testable. Third only
because it is most readily checked once a document exists; in importance it
outranks the other two and is not tradeable against how well the resume reads.

**Independent Test**: record an employer with a title and dates and nothing
else, generate, and confirm the document says exactly that much.

**Acceptance Scenarios**:

1. **Given** an employer with no recorded description, **When** the user generates, **Then** it appears with title and dates and no invented summary.
2. **Given** any generated resume, **When** its claims are compared with the profile, **Then** every statement about scope, seniority, duration, team size or outcome traces to an entry that supports it.
3. **Given** an entry rendered into English from another language, **When** the English is compared with the original, **Then** it claims neither more seniority nor more scope than the original.
4. **Given** a section for which the profile holds nothing, **When** the document is produced, **Then** the section is absent rather than present and empty — an English resume omits what it has nothing to say about.

---

### Edge Cases

- A profile written entirely in Japanese: the outcome depends on the translation question below, and the user must not receive a document they cannot read without being told.
- A profile written entirely in English: no language handling is needed at all, and the document should be straightforward.
- A profile mixing both: the resulting document must not switch language mid-sentence or mid-section.
- An employer whose only recorded name is Japanese, applying to a reader who cannot read it.
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
- **FR-013**: Where an entry is rendered into English from another language, the English MUST NOT claim more seniority, scope or responsibility than the original.
- **FR-014**: Every statement in the document MUST be traceable to the profile entry that produced it.
- **FR-015**: The system MUST record what each generated document drew on, and that record MUST remain accurate after the underlying entries are edited or deleted.
- **FR-016**: An English resume and a 履歴書 generated from the same profile MUST NOT disagree on any fact both carry.

**Open questions**

- **FR-017**: An entry recorded in Japanese MUST be handled by [NEEDS CLARIFICATION: this is the central question of the feature. Feature 003 set the precedent that the product does not translate — its readiness report names entries lacking a Japanese version and leaves writing one to the user. Applied here that yields an English resume containing Japanese, which a non-Japanese reader cannot use. Options: (a) carry the precedent over — show the entry as written, name it in a readiness report, and let the user add an English version to their profile, which per Principle I means extending the profile to hold both languages per entry; (b) translate with a model under the evidence verification feature 002 established, dropping any rendering that cannot be grounded; (c) translate and present every translated line to the user for explicit confirmation before it enters the document, per Principle IV's requirement that ungrounded claims be surfaced rather than emitted silently.]
- **FR-018**: Employer, institution and certification names recorded in Japanese MUST be handled by [NEEDS CLARIFICATION: distinct from FR-017 because a proper noun is not prose. Many Japanese companies have an official registered English name, which is a fact rather than a translation; many do not, and inventing one misnames a real organisation on a document an employer may verify. Options: (a) leave proper nouns as recorded and let the user add an English name to the profile; (b) transliterate predictably, accepting that a transliteration is not the official name; (c) treat an English name as profile data the user supplies per organisation.]
- **FR-019**: The target convention MUST be [NEEDS CLARIFICATION: "English resume" is not one format. A US resume is short, omits personal details entirely and carries no references; a UK or European CV runs longer and admits more; an academic CV is longer still and differently ordered. Options: (a) one US-style resume, the most common target for foreign-affiliated employers in Japan; (b) a user-selectable convention, as the 履歴書 offers for dates and paper; (c) one format now, with the choice deferred to a later feature.]

### Key Entities

- **Resume request**: what the user chose for this document. Affects presentation only, never content.
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

## Assumptions

- The Master Career Profile holds what this document needs — employers, titles, periods, descriptions, education, skills and certifications. Where it does not, Principle I requires extending the profile rather than collecting the data inside this feature.
- The record of what a document drew on reuses the same snapshot machinery as the 履歴書 rather than a new mechanism.
- Reverse-chronological is the only ordering. Unlike the 職務経歴書, an English resume has one conventional arrangement, so no choice is offered.
- No Japanese era conversion is involved; this document is Western-dated throughout.
- The embedded Japanese font is still required, because a profile entry or a proper noun may remain in Japanese depending on how FR-017 and FR-018 resolve.
- Contact details mean the name, email address and telephone number the profile holds. A full street address is not conventional on an English resume and is excluded by FR-009's intent even though it is not a protected characteristic.
- References are out of scope. "References available on request" is a convention the product does not need to assert on the user's behalf.
- A cover letter is a separate document and is not part of this feature.
- The document is generated and handed over, never stored or edited in place.
