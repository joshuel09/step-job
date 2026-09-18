# Phase 0 Research: Master Career Profile

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-18

The constitution already fixes the stack, the architecture and the domain
distinctions, so this document does not revisit them. It resolves only the
questions this feature's design leaves genuinely open, each arising from a
requirement or a clarification recorded in the spec.

---

## R-001: How an entry snapshot is stored

**Context**: FR-028 to FR-031. Clarification Q3 chose immutable snapshots over a
general revision history, so generated documents stay traceable after their
source entries change.

**Decision**: Store each snapshot as a single immutable row holding a structured
copy of the captured entries, keyed by the document that caused it. The row
records the identifiers of every entry it captured alongside their content at
capture time. Snapshots are never updated after insert, and are removed with the
profile they belong to.

**Rationale**: the requirement is to answer "what did this document draw on?"
after the fact, not "how has this entry changed over time". A self-contained copy
answers that in one read, with no join against a version table and no
reconstruction logic. Keeping the entry identifiers alongside the content
preserves FR-010 traceability in both directions — from document to content, and
from content back to the live entry if it still exists.

**Alternatives considered**:
- *Append-only entry versions, with snapshots pointing at version numbers.* A
  general revision history is what FR-030 explicitly excludes; it also forces
  every write path through versioning logic to serve a read that happens rarely.
- *Regenerate from current entries on demand.* Cannot work: the entries may have
  been edited or deleted, which is the whole problem being solved.
- *Store the rendered document only.* Loses the link back to the specific entries,
  which is what Principle IV requires.

---

## R-002: Where the deletion grace period is enforced

**Context**: FR-024 to FR-027. Clarification Q2 requires immediate erasure of
residence, nationality and visa data, and a 30-day recovery window for the rest.

**Decision**: Two distinct mechanisms. The immediately-erased fields are hard
deleted on the request path, inside the same transaction that marks the profile
deleted. Everything else is soft deleted by recording a deletion timestamp and a
purge-due timestamp, and a scheduled background job permanently erases profiles
whose purge date has passed. Every read path filters out soft-deleted profiles,
so FR-027 holds without each caller remembering to check.

**Rationale**: the two classes of data have different obligations. The sensitive
fields must not survive the request, so they cannot wait on a scheduler — if the
job fails, that data is still gone. The remainder must survive exactly 30 days,
which is a scheduling problem and belongs in the background worker the
constitution already provides for. Filtering at the data-access layer rather than
per endpoint makes FR-027 a structural guarantee instead of a convention.

**Alternatives considered**:
- *Soft delete everything, purge all of it after 30 days.* Rejected at
  clarification: it leaves immigration data recoverable for a month.
- *Hard delete everything immediately.* Removes the recovery window users need to
  survive a misclick on years of career history.
- *Purge on next login instead of on a schedule.* A deleted user does not log in,
  so the data would never be erased.

---

## R-003: How the interface language is selected and persisted

**Context**: FR-021 to FR-023. Clarification Q1 requires switchable English and
Japanese, English by default, with interface language independent of the language
an entry is authored in.

**Decision**: Interface locale is a persisted user setting owned by the API, not
browser-only state. The web application resolves messages per request from that
setting, falling back to English when it is unset. The browser's language may be
used to pick the initial default for a brand-new user, but once the user chooses,
their choice wins on every device. Entry content is never passed through the
translation layer.

**Rationale**: a setting kept only in the browser breaks the moment a user opens
the product on their phone, which is precisely the audience — people checking
applications between interviews. Server-side resolution also keeps rendering
server-first as the constitution requires, rather than flashing English before
swapping to Japanese. Keeping content out of the translation layer is what makes
FR-023 structurally true.

**Alternatives considered**:
- *Browser language only, no stored setting.* Fails FR-021's requirement that the
  user can switch, and fails a bilingual user whose browser is set to neither
  preference.
- *Client-side switching after hydration.* Produces a visible language flash and
  moves presentation logic into the client for no benefit.
- *Separate localised deployments.* Disproportionate for two languages and breaks
  a single user switching between them.

---

## R-004: How duplicate work experiences are detected

**Context**: FR-020, FR-032 to FR-034. Clarification Q4 defined a duplicate as the
same employer with overlapping dates, ignoring job title wording.

**Decision**: Compare a proposed experience against existing entries on normalised
employer name and date-range overlap. Normalisation is case-insensitive and
ignores punctuation, whitespace and common company suffixes, so that a name
written slightly differently by two sources still matches. Two entries at the same
employer whose ranges do not overlap are never offered as a merge. An ongoing
entry with no end date is treated as extending to the present for overlap
purposes. The result is always a suggestion the user accepts or dismisses.

**Rationale**: employer and dates are the two facts different sources agree on;
titles are exactly what they disagree about. Suffix normalisation handles the
common real case where one source writes the legal entity name and another writes
the trading name. Treating a missing end date as ongoing is required or a current
role never matches anything.

**Alternatives considered**:
- *Exact string match on employer.* Fails on trivial formatting differences,
  which is the majority of real duplicates.
- *Fuzzy similarity scoring across all fields.* Introduces a tuning threshold and
  unexplainable results for a decision the user makes anyway; FR-034 already
  keeps the human in the loop, so the extra machinery buys nothing.
- *Automatic merge above a confidence threshold.* Prohibited by FR-034 and by
  Principle V.

---

## R-005: What the profile export contains

**Context**: FR-016, FR-035 to FR-037. Clarification Q5 chose a structured file
plus a readable document, delivered together.

**Decision**: One downloadable archive containing a structured data file that
carries every entry, career story, disclosure setting and the relationships
between them, alongside a readable document rendering the same profile for a
person. Export includes the Japan-specific fields regardless of their disclosure
settings, per FR-037. Export is generated on request and is not retained on the
server after delivery.

**Rationale**: the two artefacts serve different needs — portability and
readability — and shipping them separately would make one of them the thing users
never find. Not retaining generated exports avoids creating a second, unmanaged
copy of the most sensitive data in the product, which would undercut the
deletion guarantees in R-002.

**Alternatives considered**:
- *Structured file only.* Most users cannot read it, so the export fails the
  "keep a copy of my career" need.
- *Readable document only.* Loses relationships between entries and cannot round
  trip, failing portability.
- *Server-side export history.* Creates retained copies that survive profile
  deletion unless separately tracked; the cost outweighs the convenience.

---

## R-006: Where the API establishes user identity

**Context**: the spec assumes an authenticated user and does not specify sign-in.
Every requirement here is scoped to "their" profile, so the boundary still needs
stating.

**Decision**: Authentication is handled at the web layer, which holds the session.
The API receives a verified identity with each request and derives the profile
owner from it. The API never accepts a user identifier from the request body or
path as the means of deciding whose data to return. This feature builds no
sign-in, registration or session management.

**Rationale**: naming the boundary prevents the plan from silently growing an
authentication system, and prevents the more dangerous alternative where a client
tells the server which profile it wants. Every endpoint in this feature therefore
operates on "the caller's profile" with no user identifier in the path.

**Alternatives considered**:
- *API-owned sessions.* A larger change than this feature warrants and outside
  its specified scope.
- *Profile identifier in the path.* Invites a straightforward authorisation bug
  for no gain, since a user has exactly one profile.

---

## Resolved unknowns

Every `NEEDS CLARIFICATION` raised in the plan's Technical Context is resolved
above: snapshot storage (R-001), deletion mechanics (R-002), interface
localisation (R-003), duplicate detection (R-004), export contents (R-005) and the
identity boundary (R-006). No unknowns remain open for Phase 1.
