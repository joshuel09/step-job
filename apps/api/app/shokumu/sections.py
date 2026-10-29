"""The shape of a career history, projected from the profile's entries.

A pure function from entries to an ordered structure, knowing nothing about
PDFs — the discipline `rirekisho/rows.py` established, applied to a document
with a different shape (research.md R-002). A 履歴書 row is a date and one
event; a 職務経歴書 section is an employer with structure underneath it, so
this nests where that one flattens.

Every element carries the id of the entry that produced it. That is what makes
FR-016 checkable: for any statement in the document, the entry behind it can be
named. Nothing here rephrases, summarises or reconciles — the user's words
arrive at the page as they were recorded.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class Achievement:
    """A career story, as the user wrote it."""

    title: str
    challenge: str
    action: str
    result: str
    source_entry_id: uuid.UUID


@dataclass(frozen=True)
class EmployerSection:
    """One employer, with the period, the role and what was achieved there."""

    employer: str
    job_title: str
    employment_type: str | None
    started_on: date | None
    ended_on: date | None
    """None means the role is ongoing. It is never read as "unknown": the
    profile says so and the document says 現在, as the 履歴書 does."""
    description: str
    source_entry_id: uuid.UUID
    achievements: tuple[Achievement, ...] = ()


@dataclass(frozen=True)
class SkillLine:
    name: str
    level: str | None
    source_entry_id: uuid.UUID


@dataclass(frozen=True)
class LanguageLine:
    language: str
    proficiency: str
    qualification: str | None
    source_entry_id: uuid.UUID


@dataclass(frozen=True)
class CertificationLine:
    name: str
    issuer: str | None
    issued_on: date | None
    source_entry_id: uuid.UUID


@dataclass(frozen=True)
class CareerHistory:
    """Everything the document draws, in the order it draws it."""

    sections: tuple[EmployerSection, ...] = ()
    unattached: tuple[Achievement, ...] = ()
    """Achievements recorded against no employer, which close the document
    rather than being attached to the nearest one by date (R-005). Guessing a
    relationship the user did not record is the failure Principle IV names."""
    skills: tuple[SkillLine, ...] = ()
    languages: tuple[LanguageLine, ...] = ()
    certifications: tuple[CertificationLine, ...] = ()

    def entry_ids(self) -> list[uuid.UUID]:
        """Every entry this history was built from, in the order it is drawn.

        What the snapshot records, so the document stays traceable after the
        entries change (FR-017).
        """
        ids: list[uuid.UUID] = []
        for section in self.sections:
            ids.append(section.source_entry_id)
            ids += [a.source_entry_id for a in section.achievements]
        ids += [a.source_entry_id for a in self.unattached]
        ids += [line.source_entry_id for line in self.skills]
        ids += [line.source_entry_id for line in self.languages]
        ids += [line.source_entry_id for line in self.certifications]
        return ids


def build_history(
    experiences: Sequence[Any],
    stories: Sequence[Any] = (),
    *,
    skills: Sequence[Any] = (),
    languages: Sequence[Any] = (),
    certifications: Sequence[Any] = (),
    newest_first: bool = True,
) -> CareerHistory:
    """The whole document's content, in the order it is drawn.

    `newest_first` is the arrangement the user chose. It changes the order of
    the employer sections and nothing else: every arrangement carries the
    identical set of entries, none gained, lost, merged or shortened (FR-008).
    """
    by_employer = _achievements_by_employer(stories)
    known = {entry.id for entry in experiences}

    sections = tuple(
        EmployerSection(
            employer=entry.employer_name,
            job_title=entry.job_title,
            employment_type=None if entry.employment_type is None else str(entry.employment_type),
            started_on=entry.started_on,
            ended_on=entry.ended_on,
            description=entry.description or "",
            source_entry_id=entry.id,
            achievements=tuple(by_employer.get(entry.id, ())),
        )
        for entry in _ordered(experiences, newest_first=newest_first)
    )

    # A story pointing at an employer this history does not hold would
    # otherwise vanish between the two loops. Nothing recorded is dropped
    # (FR-021), so it closes the document instead.
    unattached = tuple(
        _achievement(story)
        for story in stories
        if story.work_experience_id is None or story.work_experience_id not in known
    )

    return CareerHistory(
        sections=sections,
        unattached=unattached,
        skills=tuple(
            SkillLine(
                name=entry.name,
                level=None if entry.level is None else str(entry.level),
                source_entry_id=entry.id,
            )
            for entry in skills
        ),
        languages=tuple(
            LanguageLine(
                language=entry.language,
                proficiency=str(entry.proficiency),
                qualification=entry.qualification,
                source_entry_id=entry.id,
            )
            for entry in languages
        ),
        certifications=tuple(
            CertificationLine(
                name=entry.name,
                issuer=entry.issuer,
                issued_on=entry.issued_on,
                source_entry_id=entry.id,
            )
            for entry in certifications
        ),
    )


def _achievement(story: Any) -> Achievement:
    return Achievement(
        title=story.title,
        challenge=story.challenge,
        action=story.action,
        result=story.result,
        source_entry_id=story.id,
    )


def _achievements_by_employer(stories: Sequence[Any]) -> dict[uuid.UUID, list[Achievement]]:
    """Stories grouped under the employer they were recorded against.

    Recorded order is kept: the profile does not rank achievements and neither
    does this.
    """
    grouped: dict[uuid.UUID, list[Achievement]] = {}
    for story in stories:
        if story.work_experience_id is not None:
            grouped.setdefault(story.work_experience_id, []).append(_achievement(story))
    return grouped


def _ordered(experiences: Sequence[Any], *, newest_first: bool) -> list[Any]:
    """Employers in the chosen arrangement, with undated entries last.

    Undated last in *both* arrangements, which is why this cannot simply
    reverse a sorted list: an entry whose start date the profile does not hold
    is still part of someone's history, and it belongs at the end rather than
    at the front of the newest-first order.

    Overlapping employment produces two sections, unreconciled. Concurrent
    roles are legitimate and the document does not tidy them away (FR-011).
    """
    dated = [entry for entry in experiences if entry.started_on is not None]
    undated = [entry for entry in experiences if entry.started_on is None]
    dated.sort(key=lambda entry: entry.started_on, reverse=newest_first)
    return dated + undated
