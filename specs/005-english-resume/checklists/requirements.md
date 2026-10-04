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

- [ ] No [NEEDS CLARIFICATION] markers remain
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

Three [NEEDS CLARIFICATION] markers remain, deliberately. All three concern
language, which is this feature's substance rather than a detail of it:

- **FR-017 — an entry recorded in Japanese.** The central question. Feature 003
  established that the product does not translate on the user's behalf; carried
  over literally, that hands a Japanese-reading user an English resume they
  cannot use. Principle IV permits translating verified facts but forbids
  introducing seniority the profile does not support, and the choice of English
  word is itself a claim about seniority. This decides whether the feature calls
  a model, and option (a) implies extending the profile to hold both languages
  per entry.
- **FR-018 — proper nouns.** Separate from FR-017 because a company name is not
  prose. An official registered English name is a fact; an invented one misnames
  a real organisation on a document an employer may verify.
- **FR-019 — which English convention.** A US resume, a UK/European CV and an
  academic CV differ in length, in what personal detail is admissible, and in
  ordering. "English resume" names three documents, not one.

None has a defensible default, and guessing on FR-017 in particular would risk
building a translation feature the project may not want, or a document most of
its users cannot use.

Everything else was resolved by informed default and recorded under Assumptions.
One of those defaults is worth noting as a judgement rather than a convention:
FR-009 excludes a full street address. It is not a protected characteristic, but
it is not conventional on an English resume and carries the same screening risk,
so it is grouped with the fields the document leaves out.
