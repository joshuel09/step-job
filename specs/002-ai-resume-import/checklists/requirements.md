# Specification Quality Checklist: AI Resume Import

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-21
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

This is the first feature in the project to call a model, so Principle IV stops
being a stated intention and becomes the thing the specification is built around.

- [x] **IV. Truthful AI (NON-NEGOTIABLE)** — FR-007 requires every extracted field
      carry the passage it came from; FR-008 leaves unsupported fields empty and
      marked rather than filled; FR-009 forbids inferring, rounding or
      embellishing. SC-002 and SC-003 make this measurable at 100% and 0%.
- [x] **I. Capture Once, Generate Everywhere** — extraction feeds the Master
      Career Profile rather than creating a parallel store; FR-013 and FR-014.
- [x] **V. User Authority Over External Actions** — FR-014 keeps extraction out of
      the profile, FR-018 allows abandoning an import, FR-020 requires the user to
      start one.
- [x] **§2 Release scope** — this is item 2 of the eight-item first release.

Principles II and III concern application tracking and are not exercised here.

## Validation Notes

Decisions taken during drafting rather than deferred, each grounded in
specification 001 or the constitution:

- **Scope of "pasted text".** Platform-specific imports are excluded and recorded
  in Assumptions, because "import sources" in the source material lists several
  platforms. Text copied from a platform and pasted in is in scope; connecting to
  one is a separate feature. Without this the planning phase would design
  scrapers.
- **Source evidence as a first-class requirement.** Principle IV cannot be
  enforced by instruction alone. Requiring a source passage per field, and
  forbidding a value without one, makes truthfulness checkable rather than
  hoped for.
- **Uploaded documents are not retained.** The document contains the most
  sensitive data in the product. Discarding it after extraction mirrors the
  existing decisions not to retain exports and to erase immigration data on the
  request path.
- **Failure produces nothing.** A partial set of proposals from a failed
  extraction would be indistinguishable from a complete one, so FR-017 requires
  all or nothing.

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`
