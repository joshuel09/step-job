# Specification Quality Checklist: English Resume Generator

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-04
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

All items pass. The three markers were resolved by `/speckit-clarify` on
2026-10-07 and recorded under Clarifications; 16/16 items now pass, up from
15/16.

**What was decided:**

- **Translation became a profile-filling step, not a document step.** A model
  drafts, the user corrects and approves, and the approved wording is saved to
  the profile as that entry's English version. This is what Principle IV
  prescribes for a claim that cannot be grounded — surface it for explicit
  confirmation rather than emit it silently — and it keeps the generator
  deterministic, matching feature 004. Capturing the approved words on the
  profile means the work is asked for once (Principle I).
- **Proper nouns are supplied, never guessed.** A transliteration is not an
  official name: 日本電信電話 is NTT, which no transliteration produces. A
  guessed name misnames a real organisation on a document an employer can check.
- **One US-style resume.** The other conventions are different documents and
  can be their own work.

**Why this needed a new user story.** The translation flow is a distinct user
journey — told what is missing, offered a draft, correcting it, approving it,
and never seeing it again — with its own acceptance criteria and independently
testable. Folding it into a requirement would have hidden a whole screen's worth
of behaviour inside FR-018. It is now User Story 2 at P2, and the two stories
below it were renumbered to 3 and 4. User Story 4's "third only because" line
was reworded to match, since it is no longer third.

**Flagged for planning, not decided here.** Storing an English version per entry
is a change to the Master Career Profile. Principle I puts new career data on
the profile, so that schema change belongs to the profile's own feature and this
one depends on it. Recorded in Assumptions; planning should sequence it first
rather than discovering it mid-build.

**A note on what was rejected and why it matters.** Translating under feature
002's evidence verification looked attractive and is not possible: that
machinery checks that a quoted passage appears in the source text, which
validates extraction. A translation by definition does not appear in its source,
so it would need a different and unproven verification method. Worth recording
so it is not proposed again.
