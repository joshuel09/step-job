# Research: English Resume Generator

**Feature**: 005-english-resume | **Date**: 2026-10-11

Ten decisions. Every one of them was a real choice with a rejected
alternative; where the rejected option is the obvious one, the rationale says
why it loses.

---

## R-001: Where an approved English version is stored

**Decision**: one new table, `entry_translation`. A row is
`(profile_id, entry_type, entry_id, field, language, approved_text,
approved_at, source_fingerprint)`. One row per translated field of one entry.

**Rationale**: FR-017 requires an English version per entry, and Principle I
puts new career data on the profile rather than inside the feature that first
needs it. A single table does that for every entity at once — including the
ones features 006 and 007 will add — at the cost of one migration.

**Why the migration ships with this feature rather than with 001.** The spec's
assumptions say the storage "belongs to the profile's feature and this one
depends on it. Planning should sequence that first." The columns and the table
do belong to the profile, and they land on 001's models and 001's contract. The
migration ships here because feature 001 is complete and merged: reopening it
to add storage with no consumer is a change nobody can test, and the
requirement that motivates every column is FR-017 of this feature. Sequencing
is honoured in substance — the schema lands before anything renders — without
pretending the work belongs to a feature that is done.

It also answers an edge case the spec raises and no column arrangement answers
cheaply: *a user who approves a draft and later edits the underlying Japanese
entry*. `source_fingerprint` holds a digest of the source text as it read at
the moment of approval. When the source no longer hashes to it, the stored
English is stale, and the readiness report can say so (R-009). A
`description_english` column beside `description` has nowhere to put that fact.

**Alternatives considered**:

- *A parallel `*_english` column per translatable field.* Rejected. Four
  entities with two to four translatable fields each is a dozen columns today
  and a migration for every field added later. It also makes "which entries
  have no English version" a query over a dozen `IS NULL` checks that must be
  revised whenever the schema grows — exactly the check that silently stops
  checking.
- *A JSONB `english` blob per entry.* Rejected. It removes the migration cost
  but gives up the one thing worth having here: an approval is a row with a
  timestamp, addressable on its own, countable, and deletable without
  rewriting its neighbours.

---

## R-002: Proper nouns are not translations

**Decision**: the English name of an employer, institution, certification or
certifying body is a plain nullable column on that entity —
`employer_name_english`, `institution_english`, `name_english`,
`issuer_english` — never a row in `entry_translation`, and never drafted by a
model.

A consequence worth stating because it reads as an omission otherwise: a
certification then has *no* translatable field at all. Its name and its issuer
are both proper nouns and its two dates are not words. So `certification`
belongs to `NamedEntry` and not to `TranslatableEntry`, and the two enums exist
because the two kinds of fact do.

**Rationale**: the two look alike and behave nothing alike. A translation has a
source text it is a translation *of*, which means it can go stale when that
source changes. 株式会社サンプル's English name has no source — it is either
the name the organisation uses in English or it is a guess. FR-021 forbids the
guess outright, because a guessed name misnames a real organisation on a
document an employer may verify.

Storing them together would mean one lifecycle for two different kinds of
fact, and would put a proper noun one code path away from a model that drafts.
Separate storage makes "never drafted" structural rather than a rule someone
has to remember.

**Alternatives considered**:

- *One table with a `user_supplied` flag.* Rejected. The flag is the only thing
  keeping a proper noun out of the drafting path, and a boolean is a weak place
  to put a constitutional guarantee.
- *Transliteration for missing names.* Rejected by FR-021 and by Principle IV.
  サンプル is "Sample", "Sanpuru" or the company's own romanisation, and only
  one of those is its name.

---

## R-003: A second operation on the provider protocol

**Decision**: `AIProvider` gains `draft_translation(...) -> TranslationDraft`
beside `extract_career_information`. Both the fake and the OpenAI provider
implement it. `TranslationDraft` is added to `app/ai/schemas.py` as structured
output.

**Rationale**: the protocol's docstring says "One operation, deliberately", and
that sentence is worth honouring rather than stepping around. Read in context
it is about what the provider is *given*, not about how many methods it has:
"A provider is given text and nothing else. It receives no database access, no
profile, and no ability to write anything: it proposes, and deterministic code
decides."

The new operation keeps every one of those properties. It takes text and the
two languages, returns a proposal, and touches nothing. What would breach the
docstring is an operation that took a profile, or wrote, or returned something
the application stored without a human in between. This one does none of that.

**Alternatives considered**:

- *A separate `TranslationProvider` protocol.* Rejected. It splits the single
  model boundary the constitution requires into two, and doubles the surface
  gate G12 has to watch for no gain — the two operations share a provider
  implementation and a configuration either way.
- *Reusing `extract_career_information` with a translation prompt.* Rejected.
  Its return type describes extracted entries with source quotes, which is the
  wrong shape, and overloading it would make both behaviours harder to test
  separately than the constitution requires them to be.

---

## R-004: What the draft carries, and the 課長 problem

**Decision**: `TranslationDraft` carries `text` and `alternatives`. Each
alternative names a `phrase` in the source, the `options` it could reasonably
render as, and a short `note`. The interface shows the alternatives beside the
draft; the user picks or writes their own.

**Rationale**: this is the feature's central difficulty made concrete. 課長 is
"Manager", "Section Chief" or "Department Head", and those are three different
claims about seniority. No mechanical check can tell which one is true — the
answer is a fact about the user's job that only the user holds.

So the design does not try to resolve the ambiguity, and does not hide it
either. Returning a single confident rendering would make the product's choice
of English word into a claim about the user's seniority, which is precisely
what Principle IV forbids. Returning the alternatives moves that choice to the
person who knows the answer, and makes FR-013 and SC-006 something the
interface actively serves rather than something it hopes for.

**Alternatives considered**:

- *A confidence score on the draft.* Rejected. A number tells the user how sure
  a model is, which is not the same as telling them what the choice is between,
  and is the kind of signal people learn to click past.
- *Refusing to draft ambiguous terms at all.* Rejected. It leaves the user
  facing a blank field with no help, which is the outcome US2 exists to
  prevent.

---

## R-005: Generation never calls a model

**Decision**: document generation reads `entry_translation` and renders. It
makes no provider call, and a missing English version is a readiness failure
rather than a translation performed on the spot.

**Rationale**: FR-017 states it, and it is what keeps the generator
deterministic as feature 004 settled. It also makes SC-010 structural rather
than behavioural — a draft cannot reach a document, because the render path has
no way to produce one. The same document generated twice from an unchanged
profile is byte-identical for the same reason.

**Alternatives considered**:

- *Translate on demand during generation when a version is missing.* Rejected.
  It puts unapproved model output in a document the user sends under their own
  name, which Principle IV forbids and FR-018 names explicitly.

---

## R-006: Dates

**Decision**: `MMM YYYY` with an en dash, and `Present` for an ongoing role —
`Mar 2021 – Present`. Month precision, never a day. The formatter lives in
`app/documents/dates.py` beside the era table it must never consult.

**Rationale**: FR-004 and SC-003. Putting the Western formatter in the shared
module next to `year_to_era` is deliberate: the two are the same decision made
for two audiences, and a reader of either will see the other. A day-precision
date is both unconventional on a resume and more than most profiles honestly
hold.

**Alternatives considered**:

- *`2021-03` or `03/2021`.* Rejected — the first reads as data, and the second
  is ambiguous across exactly the two markets this document is sent to.

---

## R-007: The font is still needed

**Decision**: the English resume registers the same embedded CJK font as the
Japanese documents, from `app/documents/typography.py`.

**Rationale**: R-002 means an employer with no supplied English name appears in
Japanese. A document that renders that as hollow boxes has failed in the one
place the user most needs it to be legible — the name of the company they
worked for. The font is not optional merely because the document is English.

**Consequence**: this feature depends on `app/documents/typography.py`, which
feature 004's Phase 2 creates by extracting it from `app/rirekisho/render.py`.
That phase waits on issue #66. See *Sequencing* in plan.md.

---

## R-008: What "must not disagree" means for FR-016

**Decision**: the agreement test compares the *set of entries and their
periods* across the two documents, not their strings.

**Rationale**: this is a trap worth naming before someone writes the obvious
test. A 履歴書 shows 課長; the English resume shows the user's approved
"Section Chief". A test asserting the two documents contain the same title
strings would fail on a correctly working product.

The facts both documents carry are which employers appear, in which order, and
over which periods. Those must match exactly. The job title is one fact in two
languages — rendered from the same entry, one of them through an approval the
user made — and comparing its surface form across languages tests nothing.

**Alternatives considered**:

- *Comparing rendered text directly.* Rejected as above.
- *Dropping the test.* Rejected. SC-007 is a real guarantee: the two documents
  must not draw on different entries or disagree about when someone worked
  somewhere, and nothing else in the suite would catch it.

---

## R-009: Staleness is reported, never resolved

**Decision**: when an entry's source text no longer matches the
`source_fingerprint` recorded at approval, the stored English is marked stale.
The readiness report names it. The stored text is neither deleted nor
re-drafted automatically, and generation is not blocked by it.

**Rationale**: the user approved those words. Deleting them because the
Japanese changed would discard work they did, possibly over a typo fix.
Re-drafting silently would replace approved wording with unapproved wording,
which FR-018 forbids. Blocking generation would punish a user for editing
their own profile.

Telling them is the only action that respects all three. It is also what the
spec's edge case asks for: *"the user must be able to find out."*

**Alternatives considered**:

- *Invalidate the translation on source edit.* Rejected — destroys approved
  work on a whitespace change.
- *Compare at generation and refuse.* Rejected — FR-020 requires the user be
  told before a document is produced, not at the point of failure.

---

## R-010: The record of what a document drew on

**Decision**: reuse `EntrySnapshot` with `document_ref = "english-resume"`.
`captured_entry_ids` holds the identity and every entry rendered;
`payload` holds the rendered content, including the approved English actually
used.

**Rationale**: FR-015 and SC-008. The payload has to hold the English, not
just the entry ids — a snapshot naming entry ids alone would, after a user
edits an approval, describe a document that no longer resembles what was sent.
The 履歴書 established the machinery and the transaction boundary; this feature
adds a `document_ref` value and nothing else.

**Alternatives considered**:

- *A new table for resume snapshots.* Rejected. The assumption in the spec
  rules it out, and two snapshot mechanisms would be two answers to "what did
  this document say".
