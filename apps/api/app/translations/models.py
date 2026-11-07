"""Where an approved English version lives.

Features 003 and 004 read the profile and wrote one snapshot row between
them. This one has to store something new: FR-017 needs an English version
per entry, and Principle I puts that on the profile rather than inside the
generator, so the same approved words serve every document that needs them.

Two kinds of English are kept apart on purpose, because they are different
kinds of fact:

- A **rendering** is the product's draft of something the user wrote, which
  the user then approved. It lives in `entry_translation`, with a digest of
  the source as it read at the moment of approval, so the approval can be
  seen to have gone stale when the source changes (FR-023).
- A **name** is a fact the user states. 株式会社サンプル's English name is
  whatever that company calls itself, and nothing drafts it. Those live as
  columns on the entry they belong to, and an absent one means the user has
  not supplied it — never a guess (FR-021).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.career.models import Locale, ProfileOwned
from app.db.base import Entity


class TranslatableEntry(enum.StrEnum):
    """What the product may draft an English rendering of.

    A certification is absent deliberately. It holds a name, an issuer and
    two dates: the first two are proper nouns and the last two are not words,
    so there is nothing on it a model could draft. "Japan
    Information-Technology Engineers Examination" is the body's own English
    name or it is a guess, and an invented issuer on a resume is the kind of
    claim the applicant has to answer for (research.md R-002).
    """

    work_experience = "work_experience"
    education = "education"
    career_story = "career_story"
    skill = "skill"


class NamedEntry(enum.StrEnum):
    """What carries an English name the user supplies.

    Separate from TranslatableEntry rather than overlapping with it, because
    a name the user states and a rendering the product drafted are different
    kinds of fact and only one of them can go stale.
    """

    work_experience = "work_experience"
    education = "education"
    certification = "certification"


class EntryTranslation(Entity, ProfileOwned):
    """One approved English rendering of one field of one entry.

    `entry_id` is not a foreign key and cannot be: it points at one of four
    tables depending on `entry_type`, and PostgreSQL has no referential
    integrity across a discriminated reference. Both consequences are
    handled rather than tolerated — deleting an entry removes its
    translations in the service, with an integration test per entry type
    standing in for the key (FR-024), and deleting a profile is covered by
    the real key on `profile_id`.
    """

    __tablename__ = "entry_translation"
    __table_args__ = (
        # One approved English version per field, replaced rather than
        # accumulated: a second row would make "the approved text" ambiguous.
        UniqueConstraint(
            "profile_id",
            "entry_type",
            "entry_id",
            "field",
            "language",
            name="uq_entry_translation_field",
        ),
        Index("ix_entry_translation_profile_language", "profile_id", "language"),
    )

    entry_type: Mapped[TranslatableEntry] = mapped_column(
        Enum(TranslatableEntry, name="translatable_entry"), nullable=False
    )
    entry_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)

    # `en` today. The column exists so that a third language is a row rather
    # than a migration.
    language: Mapped[Locale] = mapped_column(
        Enum(Locale, name="locale"), nullable=False, default=Locale.en
    )

    approved_text: Mapped[str] = mapped_column(Text, nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # The source as it read when the user approved this. Stored rather than
    # recomputed: a digest taken later from the current source answers a
    # different question, and comparing the two is the only thing that makes
    # staleness detectable (FR-023, R-009).
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


#: The `field` values an approved rendering may be stored under, per entry
#: type. These are the column names on the entry, deliberately: a second
#: vocabulary ("title", "body") would have to be kept in step with the first
#: by everyone who touched either.
#:
#: It lives here rather than beside the first reader of it. The resume's
#: projection reads these to find an entry's approved English; the approval
#: route validates against them, and refusing a field this does not name is
#: what keeps `entry_translation` from accumulating rows for columns that do
#: not exist. One list, or the two would disagree about `field_of_study` on
#: the day someone added it to one of them.
TRANSLATABLE_FIELDS: dict[TranslatableEntry, tuple[str, ...]] = {
    TranslatableEntry.work_experience: ("job_title", "description"),
    TranslatableEntry.education: ("qualification", "field_of_study"),
    TranslatableEntry.skill: ("name",),
    TranslatableEntry.career_story: ("title", "challenge", "action", "result"),
}
