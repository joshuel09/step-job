"""What a resume would lack, said before it is produced rather than after.

A pure function from what the profile holds to a report, in four parts that
need four different responses from the user:

- **missing_required**: without these there is no document. Generation
  refuses by this same list, so the report a user reads and the refusal
  they would meet cannot disagree (FR-006).
- **needs_english**: entries recorded in Japanese with no approved English.
  Each can be drafted. None of them stops the document: the entry appears
  as recorded, and that is why this is a report and not a gate (FR-017).
- **untranslated_names**: organisations with no English name supplied.
  Nothing drafts these — a company's English name is the one it uses, and a
  transliteration is a guess (FR-021).
- **stale_translations**: approvals whose source has changed since. Kept,
  used, and reported (FR-023).

**Career stories are absent, deliberately.** They are translatable and the
職務経歴書 prints them; an English resume does not have a section for them.
Reporting one here would tell a user that a resume lacks something it would
not have shown either way, and the work they did in response would change
nothing on the page.

It takes rows and returns a report. No session, no query, no PDF — so every
case can be made by hand in a test, which is how the combinations that
matter get covered at all.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from app.core.text import has_japanese
from app.resume.schemas import (
    ResumeReadinessReport,
    StoredTranslation,
    UntranslatedField,
    UntranslatedName,
)
from app.translations.models import NamedEntry, TranslatableEntry

#: The fields this document prints and a model may draft, per entry type,
#: with how to name the entry to the user.
#:
#: A subset of `TRANSLATABLE_FIELDS`, and the subset is the point: that
#: dictionary says what *may* be stored, and this says what *this document
#: shows*. Career stories are translatable and are not on a resume.
RENDERED_FIELDS: dict[TranslatableEntry, tuple[str, ...]] = {
    TranslatableEntry.work_experience: ("job_title", "description"),
    TranslatableEntry.education: ("qualification", "field_of_study"),
    TranslatableEntry.skill: ("name",),
}

#: How to name an entry of each type to the user, as an attribute on it.
LABELS = {
    TranslatableEntry.work_experience: "employer_name",
    TranslatableEntry.education: "institution",
    TranslatableEntry.skill: "name",
}

#: The names the user supplies, as (recorded, supplied) attribute pairs.
#: A certification has two, which is why `field` is on the report at all.
SUPPLIED_NAMES: dict[NamedEntry, tuple[tuple[str, str], ...]] = {
    NamedEntry.work_experience: (("employer_name", "employer_name_english"),),
    NamedEntry.education: (("institution", "institution_english"),),
    NamedEntry.certification: (("name", "name_english"), ("issuer", "issuer_english")),
}


def missing_required(identity: Any | None, experiences: Sequence[Any]) -> list[str]:
    """The two things a resume is not a resume without.

    A missing English version is **not** here. An entry with no approved
    translation renders as recorded, in Japanese, and the report says so —
    refusing to produce the document would be telling the user about a gap
    at the moment they can least do anything about it (FR-017, FR-020).
    """
    missing = []
    if identity is None or not (getattr(identity, "full_name_latin", "") or "").strip():
        missing.append("identity")
    if not experiences:
        missing.append("experiences")
    return missing


def build_report(
    identity: Any | None,
    *,
    experiences: Sequence[Any] = (),
    education: Sequence[Any] = (),
    skills: Sequence[Any] = (),
    certifications: Sequence[Any] = (),
    stored: Sequence[StoredTranslation] = (),
) -> ResumeReadinessReport:
    """Everything the user should know before asking for the document."""
    required = missing_required(identity, experiences)
    approved = {(row.entry_type, row.entry_id, row.field) for row in stored}

    sections = {
        TranslatableEntry.work_experience: experiences,
        TranslatableEntry.education: education,
        TranslatableEntry.skill: skills,
    }
    named = {
        NamedEntry.work_experience: experiences,
        NamedEntry.education: education,
        NamedEntry.certification: certifications,
    }

    return ResumeReadinessReport(
        can_generate=not required,
        missing_required=required,
        needs_english=[
            item
            for entry_type, entries in sections.items()
            for item in _needing_english(entry_type, entries, approved)
        ],
        untranslated_names=[
            item for entry_type, entries in named.items() for item in _unnamed(entry_type, entries)
        ],
        stale_translations=[row for row in stored if row.is_stale],
    )


def _needing_english(
    entry_type: TranslatableEntry,
    entries: Sequence[Any],
    approved: set[tuple[TranslatableEntry, uuid.UUID, str]],
) -> list[UntranslatedField]:
    """Fields written in Japanese that have no approved English.

    Judged from the text rather than from the entry's recorded source
    language, which defaults to English — trusting that field would report
    nothing for a profile typed in Japanese without it being set, which is
    most of them.

    A field already written in English is not reported. There is nothing to
    draft: the text is its own English version, and asking for one would
    invite a model to improve the wording.
    """
    return [
        UntranslatedField(
            entry_type=entry_type,
            entry_id=entry.id,
            field=field,
            label=getattr(entry, LABELS[entry_type], "") or "",
            source_text=text,
        )
        for entry in entries
        for field in RENDERED_FIELDS[entry_type]
        if (text := (getattr(entry, field, None) or ""))
        and has_japanese(text)
        and (entry_type, entry.id, field) not in approved
    ]


def _unnamed(entry_type: NamedEntry, entries: Sequence[Any]) -> list[UntranslatedName]:
    """Organisations recorded in Japanese with no English name supplied."""
    return [
        UntranslatedName(
            entry_type=entry_type,
            entry_id=entry.id,
            field=recorded,
            recorded_name=name,
        )
        for entry in entries
        for recorded, supplied in SUPPLIED_NAMES[entry_type]
        if (name := (getattr(entry, recorded, None) or ""))
        and has_japanese(name)
        and not (getattr(entry, supplied, None) or "").strip()
    ]
