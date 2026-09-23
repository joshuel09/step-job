# Phase 0 Research: AI Resume Import

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-23

The constitution fixes the stack and the architecture, and specification 001
already settled the review queue this feature delivers into. What follows are
the decisions this feature's design leaves open — chiefly how a requirement that
says "AI must never invent" becomes something a machine can check.

---

## R-001: How "never invent" is enforced

**Context**: FR-007 to FR-009, SC-002, SC-003. Principle IV forbids AI inventing
professional experience, and this is the first feature that calls a model.

**Decision**: The model returns, for every field it fills, the **quoted passage**
of source text it took that value from. Deterministic code then verifies that the
quoted passage genuinely appears in the source. A field whose quote cannot be
found is dropped: it is left empty and marked not found, exactly as if the model
had reported nothing.

The verifier is the enforcement. The prompt is not.

```text
source text ──► model ──► {value, quote} per field
                              │
                              ▼
                    does quote appear in source?
                     ┌────────┴────────┐
                    yes               no
                     │                 │
              field proposed      field dropped,
              with evidence       marked not found
```

**Rationale**: a model asked not to fabricate will still fabricate sometimes, and
no amount of prompt wording changes that. What does change it is making a
fabricated field structurally impossible to deliver: a value the model invented
has no source passage behind it, so it cannot survive the check. This converts
Principle IV from an instruction into an invariant, and makes SC-003 — zero
proposed fields containing anything absent from the source — measurable rather
than aspirational.

**Alternatives considered**:
- *Instruct the model carefully and trust the output.* Unfalsifiable. There is no
  point in the system where a fabrication would be caught.
- *Ask for character offsets rather than quotes.* Models compute offsets
  unreliably, so a correct extraction would frequently fail a strict check while
  a fabricated one might pass by coincidence.
- *A second model call to check the first.* Two models can agree on the same
  invention, and it doubles cost and latency to produce a weaker guarantee than
  a string search.
- *Confidence scores.* A number the model chose about its own reliability is not
  evidence, and it gives the user nothing to inspect.

**Matching consequence**: verification is whitespace-normalised, because
extracted document text often differs from the original in line breaks and
spacing. It is otherwise exact — no fuzzy matching, which would reintroduce the
gap this is closing.

---

## R-002: Where extraction runs, and how the handoff works

**Context**: FR-005a to FR-005c. Clarification Q2 chose to wait where possible
and continue in the background where not.

**Decision**: Extraction begins inside the request under a configured deadline.
If it completes within the deadline, the response carries the finished outcome.
If it does not, the work is handed to the existing background worker and the
response returns the import's identifier with a running status, which the client
polls. An import moves through `pending → running → completed | failed`, a typed
enumeration rather than free text.

**Rationale**: a resume is a few pages, so most imports finish in seconds, and
making the common case a synchronous call keeps both the interface and the code
simple. The rare slow document would otherwise become a request that never
returns. Reusing the worker introduced for the purge job avoids a second
mechanism for background work. The deadline is a setting so it can be tuned
without a code change, and so tests can force the handoff path deliberately.

**Alternatives considered**:
- *Always synchronous.* A large scanned document produces a request that times
  out at the proxy, and the user learns nothing.
- *Always background.* Every import gains a poll cycle for no benefit in the case
  that dominates.
- *Server-sent events or websockets.* More machinery than a poll needs for an
  operation measured in seconds, and it does not survive the user closing the tab.

---

## R-003: Where evidence and conflicts are stored

**Context**: FR-007, FR-012a, FR-015, FR-015a. Clarification Q1 discards evidence
at review; Q3 flags conflicts rather than resolving them.

**Decision**: Two nullable structured columns are added to the existing
`ProposedEntry` table from feature 001 — one holding evidence per field, one
holding any conflicts detected — together with a nullable reference to the import
that created the proposal. Accepting or rejecting a proposal clears the evidence
column in the same transaction that records the decision.

**This changes feature 001's schema and its acceptance path.** Both are named in
the plan so they are built deliberately rather than discovered.

**Rationale**: evidence belongs to the proposal it justifies, and a separate
table would mean a join on every review read and a second thing to remember to
delete. Nullable columns keep proposals created by other means — a manual test
fixture, a future integration — valid without evidence. Clearing evidence inside
the review transaction is what makes FR-015a true even if the process dies
immediately afterwards.

**Alternatives considered**:
- *A separate evidence table.* More machinery, and it makes the FR-015a deletion
  a second operation that can fail independently.
- *Keep evidence on the import rather than the proposal.* Evidence is per field
  of a specific proposal; hanging it off the import would require reconstructing
  which value it justified.

---

## R-004: The model boundary

**Context**: Constitution §2 requires all model access behind a single
`AIProvider` abstraction, with structured output against an explicit schema, and
no provider SDK called from feature code (gate G12). FR-017a to FR-017c require
bounded retry and a distinguishable unavailability outcome.

**Decision**: A provider protocol defines one operation — extract structured
career information from text — returning a validated schema object. One concrete
implementation targets the provider the constitution names first. Feature code
depends only on the protocol.

Retries are bounded and distinguish two failures that look alike and are not:

| Failure | Meaning | Retried | Reported as |
|---|---|---|---|
| Provider unreachable, rate limited, timed out | The service is unavailable | Yes, bounded | Service unavailable, try later |
| Response does not match the schema | The model returned something unusable | Yes, bounded | Could not extract |
| Document yielded no text | Nothing to extract from | No | Document cannot be read |

A fake implementation returns scripted results with no network access. Every
automated test uses it.

**Rationale**: the abstraction is a constitutional requirement, but the fake is
what makes this feature testable at all — continuous integration cannot depend on
a paid external service, and a test whose outcome varies with a model's mood
tests nothing. Separating the three failure classes is what lets FR-017b tell a
user whether returning later is worth their time.

**Alternatives considered**:
- *Call the provider SDK directly.* Prohibited by the constitution, and it makes
  the tests either networked or meaningless.
- *Record and replay real responses.* Brittle against prompt changes, and the
  recordings would contain document text.

---

## R-005: Reading documents, and why the file never lands

**Context**: FR-002, FR-004, SC-006. The uploaded document is the most sensitive
artefact in the product.

**Decision**: Document bytes are read from the upload into memory, text is
extracted deterministically by library code, and the bytes are released. The file
is never written to disk, never placed in object storage, and never passed to the
model — only the extracted text is. A document yielding text below a small
threshold is reported as unreadable, which is how a scanned page with no text
layer is detected.

**Rationale**: FR-004 says an uploaded document is not retained. Never writing it
anywhere makes that structurally true rather than a cleanup step that can be
skipped or fail. Text extraction is a solved deterministic problem and does not
need a model; using one would add a fabrication surface where none is required.
Detecting the no-text case by threshold rather than by attempting extraction and
failing gives the user the accurate message from FR-016.

**Alternatives considered**:
- *Store the upload, then delete it after extraction.* Creates a window in which
  the document exists at rest, and a failure path where it is never removed.
- *Send the document to a multimodal model directly.* Sends the whole document,
  including data the feature has no need for, to an external service, and
  forfeits the deterministic text the evidence verifier depends on.
- *Optical character recognition for scanned documents.* A larger feature with
  its own accuracy problems; the honest answer for now is to say the document
  cannot be read.

---

## R-006: Two contracts, one generated client

**Context**: Constitution §2 requires the typed client be generated from the
OpenAPI document rather than hand-maintained. That document is currently
feature 001's, and this feature adds a second.

**Decision**: Each feature keeps its own contract file. The generation script
produces one typed module per contract, and an index re-exports them. Continuous
integration diffs the whole generated directory rather than a single file. The
contract test that compares served routes against the specification is extended
to read every contract file rather than one named path.

**Rationale**: one contract per feature keeps each specification self-contained
and reviewable. The alternative — merging both into one document — would make
every feature's contract a shared file that two branches edit at once. The
existing continuous integration check only notices staleness in the one file it
names, which would silently stop protecting anything the moment a second
contract appeared.

**Alternatives considered**:
- *One combined contract.* Constant merge conflicts, and a specification
  directory that no longer contains its own interface.
- *Leave the check pointing at the first file.* The staleness gate would pass
  while the second client drifted.

---

## R-007: Japanese era dates

**Context**: FR-011 requires era years converted to calendar dates with the
original text kept as evidence.

**Decision**: Conversion is deterministic post-processing over the value the model
extracted, not something the model is asked to do. The original text — 令和6年4月
and similar — is what the evidence records, so the user sees the document's own
words beside the converted date.

**Rationale**: era conversion is arithmetic against a published table, and
arithmetic is exactly what a model should not be trusted with when the answer
matters. Doing it deterministically also means an unrecognised era fails visibly
rather than producing a confident wrong year. Keeping the original as evidence is
what lets a user confirm the conversion rather than take it on trust.

**Alternatives considered**:
- *Let the model return a calendar date.* The converted value would have no
  verifiable passage behind it, because the document does not contain it —
  precisely the case R-001 is built to reject.

---

## Resolved unknowns

Every `NEEDS CLARIFICATION` raised in the plan's Technical Context is resolved
above: evidence enforcement (R-001), synchronous and background execution
(R-002), evidence and conflict storage (R-003), the model boundary and its
failure classes (R-004), document handling (R-005), client generation across two
contracts (R-006) and era dates (R-007). Nothing is left open for Phase 1.
