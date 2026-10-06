# Feature Specification: 職務経歴書 Generator

**Feature Branch**: `71-shokumu-keirekisho-spec`

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "職務経歴書 generator — produce a Japanese career history document from the Master Career Profile. Unlike the 履歴書, which is a fixed standardized form, the 職務経歴書 is free-form prose and tables where the applicant explains what they actually did: scope, responsibilities, achievements and the technologies or methods used, employer by employer or project by project. It draws on the same profile entries and career stories, reuses the snapshot machinery so every statement stays traceable to the entries behind it, and invents nothing to fill a gap — an employer with no recorded detail gets a short entry, not a generated narrative. The user chooses the arrangement (chronological, reverse-chronological, or grouped by project) and the same 和暦/西暦 and paper conventions the 履歴書 offers."

## Context

A Japanese application almost always asks for two documents. The 履歴書 (feature
003) is a standardised form: fixed fields, fixed order, little room for
expression. The 職務経歴書 is the other half — free-form, usually one to three
pages, where the applicant explains what they actually did and what they are
good at.

The difference matters more than it looks. A 履歴書 is filled in; a 職務経歴書 is
*written*. It asks for scope, responsibilities, achievements and the methods
used, and it is read as the applicant's own account of their career. That makes
it the single most tempting document in the product to embellish, and therefore
the one where Principle IV carries the most weight. A generated sentence that
rounds "contributed to" up to "led", or supplies a team size nobody recorded, is
not a quality improvement — it is a claim the user will be asked to defend in an
interview.

This feature is a second consumer of the Master Career Profile, not a second
place to describe a career (Principle I). It also reuses what feature 003 built:
the embedded Japanese font, the 和暦/西暦 conversion, the paper sizes, and the
snapshot machinery that keeps a sent document's statements traceable after the
profile moves on.

## Clarifications

### Session 2026-10-06

- Q: Who writes 職務要約 (career summary) and 自己PR (self-promotion)? → A: Split them. 職務要約 is assembled deterministically from verified profile entries; 自己PR is labelled and left for the user, because self-characterisation is not something the profile can evidence. No model is involved in this feature.
- Q: What should "grouped by project" mean, given the profile has no project entity? → A: Drop project grouping from this feature. Ship the two chronological arrangements; project grouping returns as its own feature once a project entity exists.
- Q: Where does a career story attached to no employer belong? → A: A closing achievements section, so nothing the user recorded is lost.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn my profile into a 職務経歴書 (Priority: P1) 🎯 MVP

A user who has recorded their career — employers, roles, dates, descriptions and
career stories — asks for a 職務経歴書 and receives a document they could send to
a Japanese employer today. It opens with a short career summary, then covers each
employer in turn: the period, the employer, what the role involved, and the
achievements the user recorded. It closes with the skills and certifications the
profile holds.

**Why this priority**: it is the whole feature. Without it there is no document.
Everything else refines how the document reads, not whether it exists.

**Independent Test**: record two employers and a career story, generate, and read
the resulting document. Every employer appears, every recorded achievement
appears, and nothing appears that the profile does not hold.

**Acceptance Scenarios**:

1. **Given** a profile with two employers and recorded descriptions, **When** the user generates a 職務経歴書, **Then** both employers appear with their periods and descriptions, in the document's chosen order.
2. **Given** a profile with career stories attached to an employer, **When** the user generates, **Then** those stories appear as that employer's achievements, in the user's own words.
3. **Given** a generated document, **When** the user inspects any statement in it, **Then** the profile entry that produced it can be named.
4. **Given** a generated document, **When** the user reads it, **Then** the Japanese is readable text rather than missing glyphs, and the document can be printed.
5. **Given** a profile with no career data at all, **When** the user generates, **Then** generation is refused with the missing essentials named, rather than producing an empty document.

---

### User Story 2 - Arrange it the way this employer expects (Priority: P2)

Different careers call for different arrangements. A user with a steady
progression wants reverse-chronological, newest first, which is what most
mid-career Japanese applications expect. A new graduate or career-changer may
want plain chronological. The same document content, arranged two ways.

Grouping by project is deliberately not offered. The profile records employers
and achievements, not engagements, so a project section would have no client,
period or role to show. It returns as its own feature once the profile holds
projects.

The user also chooses the same conventions the 履歴書 offers: 和暦 or 西暦, and the
paper size.

**Why this priority**: the document exists without this, in one default
arrangement. But a 職務経歴書 in the wrong arrangement reads as though the
applicant did not know the convention, which is the same failure mode the 履歴書
work was careful to avoid.

**Independent Test**: generate the same profile both ways and confirm each
arrangement contains the identical set of facts in a different order, with no
entry gained or lost between them.

**Acceptance Scenarios**:

1. **Given** a profile with three employers, **When** the user chooses reverse-chronological, **Then** the newest employer appears first.
2. **Given** the same profile, **When** the user chooses chronological, **Then** the oldest appears first and the content is otherwise identical.
3. **Given** the same profile, **When** the user switches between 和暦 and 西暦, **Then** every date in the document follows the chosen convention and the two never appear together.
4. **Given** any arrangement, **When** the document is produced, **Then** it contains exactly the same entries as every other arrangement of that profile.

---

### User Story 3 - Say only what I have said (Priority: P3)

A user whose profile is thin in places gets a thin document in those places. An
employer with no recorded description gets its period and name and nothing else.
A role with no recorded achievements has no achievements section. Where the
document conventionally carries prose the user has not written, the section is
labelled and left for them rather than filled in on their behalf.

Nothing in the document asserts scope, seniority, duration, team size or outcome
that the profile does not support.

**Why this priority**: it is the constitutional constraint made testable. It is
third only because it is most naturally verified once there is a document to
inspect — in importance it outranks the other two, and a failure here is not a
defect to be weighed against output quality (Principle IV).

**Independent Test**: record an employer with a name and dates and nothing else,
generate, and confirm the document says exactly that much about it.

**Acceptance Scenarios**:

1. **Given** an employer with no recorded description, **When** the user generates, **Then** that employer appears with its period and name and no invented narrative.
2. **Given** a role with no recorded achievements, **When** the user generates, **Then** no achievements are listed for it and no placeholder stands in for them.
3. **Given** any generated document, **When** its claims are compared with the profile, **Then** every statement about scope, seniority, duration, team size or outcome traces to a profile entry that supports it.
4. **Given** a section the product does not write on the user's behalf, **When** the document is produced, **Then** the section is present and labelled rather than silently omitted.
5. **Given** entries the user wrote in English, **When** the document is produced, **Then** they appear in English as written rather than translated into Japanese.

---

### Edge Cases

- An employer the user held for one month, and one held for fifteen years — both appear, neither is summarised away.
- Overlapping employment, such as a contract held alongside a permanent role: both appear, unreconciled, as in the 履歴書.
- A career story attached to no employer: it goes in the closing achievements section rather than being dropped (FR-021).
- A profile with employers but no career stories at all: a legitimate document, thinner than most, and with no closing achievements section at all rather than an empty one.
- A profile with too little to summarise — one employer and no dates: 職務要約 says only what can be traced, and says less rather than reaching.
- Every career story unattached: the employer sections carry no achievements and the closing section carries them all, which is a true picture of what was recorded.
- A career long enough that the document runs past the conventional pages: entries are never dropped to fit (inherited from the 履歴書's FR-018a).
- The same profile generating a 履歴書 and a 職務経歴書 on the same day: the two documents must not contradict each other.
- A user who edits a profile entry after sending the document: what was sent stays inspectable.

## Requirements *(mandatory)*

### Functional Requirements

**Producing the document**

- **FR-001**: The system MUST produce a 職務経歴書 from the Master Career Profile, requiring no career information the profile does not already hold.
- **FR-002**: The system MUST render Japanese as readable, selectable text with embedded glyphs, so the document survives being printed or opened on a machine without the font.
- **FR-003**: The system MUST cover each employer with, at minimum, the period and the employer's name, and additionally the recorded role, description and achievements where the profile holds them.
- **FR-004**: The system MUST present recorded career stories as the achievements of the employer they belong to, in the user's own words.
- **FR-005**: The system MUST NOT retain the generated document; the profile and the record of what the document drew on are what persist.
- **FR-006**: The system MUST refuse to generate when the profile holds no career history at all, naming what is missing rather than producing an empty document.

**Arrangement and conventions**

- **FR-007**: Users MUST be able to choose the arrangement: reverse-chronological or chronological. Grouping by project is out of scope for this feature; the profile holds no project entity, and inventing one from achievements would produce a section with no client, period or role.
- **FR-008**: Every arrangement MUST contain the same set of entries; changing the arrangement MUST NOT add, drop, merge or shorten any entry.
- **FR-009**: Users MUST be able to choose 和暦 or 西暦, and one convention MUST be used throughout a document; the two MUST NOT appear together.
- **FR-010**: Users MUST be able to choose the paper size, with the same content at either size.
- **FR-011**: The system MUST produce every entry across as many pages as are needed rather than dropping or shortening entries to fit a conventional length.

**Truthfulness**

- **FR-012**: The system MUST NOT state scope, seniority, duration, team size or outcome that the profile does not support.
- **FR-013**: The system MUST leave a section empty where the profile holds nothing for it, rather than supplying a placeholder, a sample or an inferred narrative.
- **FR-014**: The system MUST label a section it deliberately leaves to the user, so a blank reads as a decision rather than a defect.
- **FR-015**: Entries the user recorded in English MUST appear in English as written; the system MUST NOT translate them.
- **FR-016**: Every statement in the document MUST be traceable to the profile entry that produced it.
- **FR-017**: The system MUST record what each generated document drew on, and that record MUST remain accurate after the underlying entries are edited or deleted.
- **FR-018**: A 職務経歴書 and a 履歴書 generated from the same profile MUST NOT contradict each other on any fact both documents carry.

**Sections the product does and does not write**

- **FR-019**: The system MUST assemble 職務要約 (career summary) from verified profile entries — the span of the career, the number of employers, the most recent role — restating facts the profile holds rather than characterising the applicant. It MUST NOT state anything 職務要約 cannot trace to an entry.
- **FR-020**: The system MUST leave 自己PR (self-promotion) labelled and empty for the user. It is a claim about what kind of worker someone is, which no set of dates and titles can evidence, so the product does not write it.
- **FR-021**: The system MUST present a career story attached to no employer in a closing achievements section, so that nothing the user recorded is dropped from the document.

### Key Entities

- **職務経歴書 request**: what the user chose for this document — arrangement, date convention, paper size. Affects presentation only, never content.
- **Career history section**: one employer's portion of the document — period, employer, role, description and achievements, each drawn from a profile entry.
- **Achievement**: a recorded career story presented under the employer it belongs to, in the user's words. One belonging to no employer appears in the closing achievements section instead.
- **Career summary**: the opening 職務要約, assembled from facts the profile holds — career span, employer count, most recent role — and carrying nothing that cannot be traced to an entry.
- **Document record**: what a generated document drew on, captured at generation and unchanged afterwards, so a sent document stays inspectable. The same machinery the 履歴書 uses.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with a populated profile obtains a complete 職務経歴書 without typing any career information that is already in their profile.
- **SC-002**: Every Japanese character in a generated document is readable as text, verified by extracting the text back out of the document — the check that fails when glyphs are missing.
- **SC-003**: Every factual statement in a generated document can be traced to the profile entry that produced it, with no unattributable statements.
- **SC-004**: A profile section the user has not filled in produces no content in the document — measured as zero placeholder, sample or inferred sentences across every empty-section case.
- **SC-005**: The same profile generated in both arrangements yields the identical set of entries in each, with none gained, lost, merged or shortened.
- **SC-006**: A document generated before a profile edit still shows what it drew on after that edit.
- **SC-007**: A 履歴書 and a 職務経歴書 generated from the same profile agree on every employer, period and title that both carry.
- **SC-008**: A career long enough to exceed the conventional length produces every entry, with none dropped or truncated.
- **SC-009**: Every statement in 職務要約 traces to a profile entry, with no sentence characterising the applicant rather than reporting their record.
- **SC-010**: 自己PR is present and labelled in every generated document, and empty in every one of them.
- **SC-011**: A career story attached to no employer appears in the document, measured as zero recorded stories missing from a generated 職務経歴書.

## Assumptions

- The Master Career Profile already holds what this document needs — employers, roles, periods, descriptions, career stories, skills and certifications. Where it does not, Principle I requires extending the profile rather than collecting the data inside this feature.
- The embedded Japanese font, the 和暦/西暦 conversion and the paper sizes are reused from the 履歴書 rather than built again.
- The record of what a document drew on reuses the same snapshot machinery as the 履歴書.
- Reverse-chronological is the default arrangement, being what most mid-career Japanese applications expect; the user can change it to chronological.
- No model is involved. Every section is assembled deterministically from profile entries, which is what makes FR-019's 職務要約 traceable by construction rather than by verification. This feature does not depend on the AI provider.
- Project grouping is deferred rather than rejected. It needs a project entity on the profile, which belongs to the profile's own feature under Principle I, not to this one.
- The conventional length is one to three pages. It is a guide, not a cap — FR-011 governs.
- Photographs are out of scope, as in the 履歴書: a 職務経歴書 does not carry one.
- The document is generated and handed over, not stored, edited in place, or treated as a second source of truth.
- Disclosure-flagged Japan-specific fields are not part of this document; it is a career history, not a personal-details form.
