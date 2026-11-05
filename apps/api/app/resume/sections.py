"""The profile, in the shape an English resume needs.

A pure function from entries to an ordered structure, knowing nothing about
PDFs — the discipline `rirekisho/rows.py` set and `shokumu/sections.py`
followed, applied to a third document.

Two things make this one different.

**The dataclasses are where FR-009 and FR-010 are enforced.** There is no
attribute here for a date of birth, an address, a photograph, a nationality
or a residence status — nothing from `JapanProfile`, disclosed or not. The
renderer is handed these and nothing else, so a later layout change cannot
leak a field its input type does not carry, and adding one would be a
visible diff with the requirement written beside it. Feature 004 passed the
same gate by never fetching `JapanProfile`; this passes by never fetching it
*and* by having nowhere to put it.

**Each displayed string is resolved here, from three places in order.** An
organisation's English name where the user supplied one, an approved
`EntryTranslation` where one exists, and otherwise the text as recorded. The
third case is not a failure: an entry with no English version appears in
Japanese, legibly, and readiness says so before the document is asked for
(FR-017). Nothing in this module calls a provider, and nothing in
`app/resume/` can — there is no import of `app.ai` anywhere beneath it, and
a test fails the build if one appears.
"""

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.career.models import Locale
from app.translations.models import EntryTranslation, TranslatableEntry

#: The `field` values an approved translation is stored under. These are the
#: column names on the entry, deliberately: a second vocabulary ("title",
#: "body") would have to be kept in step with the first by everyone who
#: touched either, and the approval route in User Story 2 writes the same
#: strings this reads.
TRANSLATABLE_FIELDS = {
    TranslatableEntry.work_experience: ("job_title", "description"),
    TranslatableEntry.education: ("qualification", "field_of_study"),
    TranslatableEntry.skill: ("name",),
    TranslatableEntry.career_story: ("title", "challenge", "action", "result"),
}


@dataclass(frozen=True)
class Contact:
    """The heading of the document.

    A name, and the two ways to reach someone. No date of birth, no address,
    no photograph — a US resume carries none of them, and FR-009 says this
    document must not either. The absence is the mechanism, not an oversight
    to be caught in review.
    """

    full_name: str
    email: str | None
    phone: str | None
    source_entry_id: uuid.UUID


@dataclass(frozen=True)
class ExperienceEntry:
    """One role, as the profile records it.

    The employer is a name the user supplied or the name as recorded; the
    title and the description are approved English or the text as written.
    Nothing here is rephrased or summarised on the way through.
    """

    employer: str
    job_title: str
    started_on: date | None
    ended_on: date | None
    """None means the role is ongoing — never that the date is unknown."""
    description: str
    source_entry_id: uuid.UUID


@dataclass(frozen=True)
class EducationEntry:
    """One course of study.

    `qualification` and `field_of_study` are both optional: a profile that
    names the institution and nothing else is a complete answer, and a
    resume prints what it has.
    """

    institution: str
    qualification: str | None
    field_of_study: str | None
    started_on: date | None
    ended_on: date | None
    source_entry_id: uuid.UUID


@dataclass(frozen=True)
class SkillEntry:
    """One skill, with the level the user chose for it.

    `level` is a string here rather than the enum it came from: the
    renderer prints it and has no business comparing it, and this is the
    boundary where the profile's vocabulary stops.
    """

    name: str
    level: str | None
    source_entry_id: uuid.UUID


@dataclass(frozen=True)
class CertificationEntry:
    """A certification is in no translation at all (R-002).

    Its name and its issuer are proper nouns and its dates are not words, so
    both English forms are the user's to supply and neither is ever drafted.
    """

    name: str
    issuer: str | None
    issued_on: date | None
    source_entry_id: uuid.UUID


@dataclass(frozen=True)
class ResumeContent:
    """Everything the renderer is given, and the boundary FR-010 rests on."""

    contact: Contact
    experiences: tuple[ExperienceEntry, ...] = ()
    education: tuple[EducationEntry, ...] = ()
    skills: tuple[SkillEntry, ...] = ()
    certifications: tuple[CertificationEntry, ...] = ()


class Approved:
    """The approved English a profile holds, looked up by entry and field.

    Built once per document from rows already loaded, so the projection makes
    no query per entry. A lookup that finds nothing returns nothing, and the
    caller falls back to what was recorded — which is the ordinary case for a
    profile written in English, where there is nothing to translate.

    The language is filtered here rather than left to the caller. `en` is the
    only value stored today, and the column exists so that a third language
    is a row rather than a migration — on the day that happens, a lookup
    keyed without it would put someone's German into their English resume,
    and it would do so silently. Discipline at the call site is not a
    mechanism; this is.
    """

    def __init__(
        self, translations: Iterable[EntryTranslation] = (), *, language: Locale = Locale.en
    ) -> None:
        """Index the rows for this language by entry, type and field."""
        self._by_key = {
            (row.entry_type, row.entry_id, row.field): row.approved_text
            for row in translations
            if row.language is language
        }

    def text(
        self,
        entry_type: TranslatableEntry,
        entry_id: uuid.UUID,
        field: str,
        recorded: str | None,
    ) -> str | None:
        """The approved English for this field, or what the user recorded.

        An approved blank is not returned in place of the source: FR-025
        refuses one at approval, and were one ever stored, printing it would
        take the entry out of the document with nothing to say it had gone.
        """
        approved = self._by_key.get((entry_type, entry_id, field))
        if approved and approved.strip():
            return approved
        return recorded


def _supplied_or_recorded(supplied: str | None, recorded: str | None) -> str | None:
    """An organisation's own English name, or its name as recorded.

    Never a transliteration. 株式会社サンプル is whatever that company calls
    itself in English, and where the user has not told us, the Japanese is
    what appears — which is why this document still embeds a CJK font
    (FR-021, R-007).

    `recorded` is optional because a certification's issuer is: a profile
    may name the certificate and not who awarded it. The English name is
    still preferred when there is one, and a user who supplied an English
    issuer without a Japanese one has said something — dropping it on the
    grounds that the field it would have fallen back to is empty would
    throw away the only answer they gave.
    """
    if supplied and supplied.strip():
        return supplied.strip()
    return recorded


def build_content(
    identity: Any,
    *,
    experiences: Sequence[Any] = (),
    education: Sequence[Any] = (),
    skills: Sequence[Any] = (),
    certifications: Sequence[Any] = (),
    translations: Iterable[EntryTranslation] = (),
    language: Locale = Locale.en,
    include_skills: bool = True,
) -> ResumeContent:
    """Project the profile into what the renderer may see.

    Experience and education run newest first, which is what a US resume
    means by order (FR-003). An entry with no start date sorts last rather
    than first: the profile does not say when it began, and putting it at the
    top would assert that it is the most recent thing the person did.

    **A stale approval is used, deliberately.** Where the source text was
    edited after its English was approved, FR-023 says to keep the approved
    wording, report that it no longer matches, and not block generation —
    so the divergence is the readiness report's to raise, not this
    function's to resolve. Replacing the user's approved words with the
    newer Japanese, or dropping the entry, would both be this module
    deciding something FR-023 gives to the user. The snapshot records the
    English actually used, so what was sent stays inspectable either way
    (R-010).
    """
    approved = Approved(translations, language=language)

    return ResumeContent(
        contact=Contact(
            full_name=identity.full_name_latin,
            email=identity.email,
            phone=identity.phone,
            source_entry_id=identity.id,
        ),
        experiences=tuple(
            ExperienceEntry(
                employer=_supplied_or_recorded(
                    getattr(entry, "employer_name_english", None), entry.employer_name
                )
                or entry.employer_name,
                job_title=approved.text(
                    TranslatableEntry.work_experience, entry.id, "job_title", entry.job_title
                )
                or entry.job_title,
                started_on=entry.started_on,
                ended_on=entry.ended_on,
                description=approved.text(
                    TranslatableEntry.work_experience, entry.id, "description", entry.description
                )
                or "",
                source_entry_id=entry.id,
            )
            for entry in _newest_first(experiences)
        ),
        education=tuple(
            EducationEntry(
                institution=_supplied_or_recorded(
                    getattr(entry, "institution_english", None), entry.institution
                )
                or entry.institution,
                qualification=approved.text(
                    TranslatableEntry.education, entry.id, "qualification", entry.qualification
                ),
                field_of_study=approved.text(
                    TranslatableEntry.education, entry.id, "field_of_study", entry.field_of_study
                ),
                started_on=entry.started_on,
                ended_on=entry.ended_on,
                source_entry_id=entry.id,
            )
            for entry in _newest_first(education)
        ),
        skills=tuple(
            SkillEntry(
                name=approved.text(TranslatableEntry.skill, entry.id, "name", entry.name)
                or entry.name,
                level=entry.level.value if entry.level else None,
                source_entry_id=entry.id,
            )
            for entry in skills
        )
        if include_skills
        else (),
        certifications=tuple(
            CertificationEntry(
                name=_supplied_or_recorded(getattr(entry, "name_english", None), entry.name)
                or entry.name,
                issuer=_supplied_or_recorded(getattr(entry, "issuer_english", None), entry.issuer),
                issued_on=entry.issued_on,
                source_entry_id=entry.id,
            )
            for entry in _newest_first(certifications, key="issued_on")
        ),
    )


def _newest_first(entries: Sequence[Any], key: str = "started_on") -> list[Any]:
    """Most recent first, with undated entries last.

    `ended_on` is not the sort key for a role: an ongoing one has none, and
    sorting by it would bury the user's current job beneath every job they
    have left. The start date is what the profile actually states about when
    an entry belongs.

    An entry with no date at all sorts last rather than first. Reading a
    missing date as "most recent" would put an entry at the top of the
    document on the strength of something the profile does not say.
    """
    return sorted(
        entries,
        key=lambda e: (getattr(e, key) is not None, getattr(e, key) or date.min),
        reverse=True,
    )
