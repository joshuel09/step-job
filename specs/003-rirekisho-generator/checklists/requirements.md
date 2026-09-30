# Specification Quality Checklist: 履歴書 Generator

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-30
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

## Constitution Alignment

This is the first feature that produces a document from the profile rather than
reading into it, so it is the first real consumer of two rules that have until
now only been stated.

- [x] **IV. Truthful AI (NON-NEGOTIABLE)** — applies here in a second way, new to
      this feature. The familiar way is FR-012 and FR-016: every statement traces
      to an entry, and a generation record keeps that true after the entries
      change. The new way is FR-013 and FR-014: a 履歴書 has conventional slots a
      template *expects* filled, and filling one the profile does not support
      would be inventing experience just as surely as an AI would. SC-003 sets
      that at zero.
- [x] **I. Capture Once, Generate Everywhere** — the document derives entirely
      from the profile. The two identity fields a 履歴書 needs are added to the
      profile rather than collected per document.
- [x] **V. User Authority** — FR-020 to FR-022. This is the first real exercise of
      FR-006 of specification 001: Japan-specific fields appear only where the
      user opted them in.
- [x] **§2 AI boundary (G12)** — not applicable. This feature makes no model
      calls, by decision rather than omission.
- [x] **§2 Release scope** — item 3 of the eight-item first release.

Principles II and III concern application tracking and are not exercised here.

## Validation Notes

Three decisions were taken on the user's behalf that are cultural judgments
rather than technical defaults. They are recorded here prominently because they
are the ones most worth confirming:

- **No gender field.** The profile does not record gender, Japanese guidance has
  treated the field as optional since 2021, and for a product serving foreign
  professionals the field carries discrimination weight. The generator omits it
  rather than producing an empty one that invites completion. A user who needs a
  form with it would have to say so.
- **No photograph.** Conventional on a 履歴書, but storing a photograph of
  someone's face is a materially different privacy commitment from storing text,
  and the product does not do that today. The frame is left empty.
- **No 志望の動機.** Written for a particular employer rather than held as career
  history, so it belongs to a later feature. Left blank and labelled.

Also settled during drafting rather than deferred:

- **Two fields are added to the profile**, not collected per document. Date of
  birth and address are career identity data, and Principle I says a user tells
  us these once. The dependency on specification 001 is named in Assumptions so
  the plan carries the change deliberately.
- **No AI.** Laying out a 履歴書 follows deterministically from the entries. A
  model would add a fabrication surface to the one feature whose entire purpose
  is that nothing is fabricated.

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`
