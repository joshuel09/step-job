# Phase 0 Research: 履歴書 Generator

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-10-01

The constitution fixes the stack, and specifications 001 and 002 settled the
profile, the disclosure rules and the snapshot machinery this feature consumes.
What follows are the decisions this feature's design leaves open.

---

## R-001: What "may offer a Japanese version" means here

**Context**: FR-014a to FR-014c. Clarification Q1 settled that entries render as
written and that the system *may* offer a Japanese version for the user to
approve. That "may" is the only thing in this feature that could involve a
model, so it decides whether the AI gate is live.

**Decision**: Out of scope for this feature. The generator **detects** entries
written in English and **tells the user** which ones have no Japanese version,
with a link to edit the profile. It does not generate a suggestion. Producing
one is a separate feature with its own specification.

**Rationale**: three reasons, each sufficient on its own.

A translation cannot be checked the way feature 002 checks an extraction. That
verifier works because an extracted value quotes a passage of the source; a
translation *is* new content, so there is no passage to find. Putting it inside
this feature would mean shipping AI output into a document the user signs their
name to, with none of the machinery that makes that safe elsewhere.

It is a different feature wearing this one's clothes. Translating career text
well is its own problem — tone, keigo, how a job title maps between markets —
and burying it inside a layout feature would mean it never gets specified
properly.

And it is not needed for this feature to work. FR-014c requires a document be
producible without Japanese for every entry. Telling the user what is missing
discharges the obligation; writing it for them does not.

**Consequence**: this feature makes no model calls at all, and gate G12 holds by
test rather than by assertion — the AST walker added in feature 002 already
fails if anything under `app/rirekisho/` imports a provider.

**Alternatives considered**:
- *Generate a suggestion the user approves.* The approval step sounds like it
  restores safety, but a plausible translation is exactly what a user skims past.
  Feature 002's whole lesson is that review is weaker than verification.
- *Block generation until every entry has Japanese.* Prohibited by FR-014c, and
  it would make the feature useless to the users it is for.

---

## R-002: Rendering the document

**Context**: FR-003 requires a downloadable, printable file; FR-018 requires A4
and B5.

**Decision**: Draw the PDF directly with the library already present in the
repository, promoted from a development dependency to a runtime one. One
open-licensed Japanese font is shipped with the application and registered at
startup.

**The font is the part that matters.** Without an embedded CJK font every
Japanese character renders as a hollow box, and the failure is silent — the file
is produced, the right size, and unreadable. A developer with Japanese system
fonts may not reproduce it. So the quickstart extracts the text back out of a
generated PDF and asserts the Japanese is present *as text*, which fails
loudly in continuous integration if the font is missing.

**Rationale**: the library is already a dependency and already generates the
test fixtures for feature 002, so this adds no new technology. Drawing directly
gives exact control over a form whose layout is the point — a 履歴書 in roughly
the right shape is not a 履歴書.

**Alternatives considered**:
- *Render HTML and convert it.* Adds a browser binary to the API image for one
  feature, and gives less control over a fixed-size form than it appears to.
- *A second PDF library better suited to forms.* Two PDF libraries in one
  codebase for one feature is not a trade worth making.
- *Rely on system fonts.* Works on a developer's machine and fails in a
  container, which is the worst possible distribution of outcomes.

---

## R-003: Using the snapshot machinery

**Context**: FR-016 requires each document record what it was based on. Feature
001 built exactly this and nothing has used it yet.

**Decision**: Generation captures a snapshot of the entries it rendered, using
the existing capture function called directly rather than over HTTP, with
`document_ref` identifying the document and the moment. The capture and the
render happen in one transaction: if rendering fails, no snapshot is left behind
for a document that never existed.

The **Generation Record** named in the specification *is* that snapshot. No new
table.

**Rationale**: the machinery exists and this is what it was built for. Calling
it in-process rather than over the network keeps it in the same transaction,
which is what makes the all-or-nothing property true rather than hoped for. A
second table recording the same thing would be a second thing to keep in step.

**Alternatives considered**:
- *Call the snapshot endpoint over HTTP.* Two transactions, so a crash between
  them leaves a snapshot with no document or a document with no record.
- *A new table for generated documents.* Duplicates the snapshot and invites the
  two to disagree.

---

## R-004: The change to feature 001

**Context**: a 履歴書 carries a date of birth and a current address; the profile
holds neither. The specification's Assumptions name this dependency.

**Decision**: `Identity` gains two optional fields, date of birth and address.
Four things change together, and all four are named so none is discovered during
implementation:

| What | Where |
|---|---|
| The model and its migration | `apps/api/app/career/models.py`, a new revision |
| The request and response shapes | `apps/api/app/career/schemas.py` |
| Feature 001's contract | `specs/001-master-career-profile/contracts/openapi.yaml` |
| The form a user types them into | `apps/web/components/profile/identity-form.tsx` |

**Rationale**: Principle I says a user tells us their career once. Asking for a
date of birth per document would be asking repeatedly for something that does
not change. Both fields are optional, so an existing profile stays valid and the
generator leaves them blank when they are absent, exactly as FR-013 requires.

The web form is listed deliberately. Adding the columns without the form would
give the generator fields no user could ever fill in — a change that looks
complete in the API and is useless in the product.

**Alternatives considered**:
- *Collect them during generation.* Breaks Principle I, and asks again every
  time a document is produced.
- *A separate document-details record.* A date of birth is identity, not
  document metadata, and splitting it would mean two places to look.

---

## R-005: Writing dates in 和暦

**Context**: FR-017 and FR-019 require one convention throughout a document.

**Decision**: Rendering a calendar date as an era year is the inverse of the
conversion feature 002 already performs, and lives beside it in the same module
rather than in this feature. Both directions share one era table, so they cannot
drift apart.

**Rationale**: two copies of the era table would eventually disagree, and the
disagreement would show up as a date that converts one way and renders another.
Keeping them adjacent makes that impossible rather than unlikely. The conversion
is arithmetic in both directions, so no model is involved either way.

**Alternatives considered**:
- *A table local to this feature.* Guarantees two sources of truth for the same
  facts.
- *A formatting library.* Era handling is a dozen lines against a published
  table; a dependency for it is not worth the surface.

---

## R-006: The 学歴・職歴 projection

**Context**: FR-006 to FR-011. One chronological table combining two kinds of
entry, with conventions about what each produces.

**Decision**: A pure function from the profile's education and work entries to a
list of rows, in its own module, with no knowledge of PDFs. Education entries
produce entering and completing rows; work experiences produce joining and
leaving rows, with an unfinished role rendering 現在に至る; education precedes
employment; each block is ordered oldest first; the table ends with 以上.
Overlapping entries are preserved in order rather than reconciled.

**Rationale**: this is the only non-trivial transform in the feature, and the
one where a mistake is a wrong career history rather than a cosmetic flaw.
Keeping it separate from rendering means it can be tested exhaustively without
producing a single PDF, which is the difference between testing the rules and
testing a picture of them.

**Alternatives considered**:
- *Build the rows while drawing.* The ordering rules become untestable except
  by reading rendered output, which is slow and imprecise.
- *Let the template decide the order.* Puts career-history logic in a layout
  file, where nobody will look for it.

---

## Resolved unknowns

Every `NEEDS CLARIFICATION` raised in the plan's Technical Context is resolved
above: the scope of the Japanese-version offer (R-001), rendering and fonts
(R-002), snapshot integration (R-003), the change to feature 001 (R-004), era
rendering (R-005) and the table projection (R-006). Nothing is left open for
Phase 1.
