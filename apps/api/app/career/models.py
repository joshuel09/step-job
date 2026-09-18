"""Career module entities.

See specs/001-master-career-profile/data-model.md for the rules these encode.
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from app.db import soft_delete  # noqa: F401 - registers the read filter
from app.db.base import Entity


class Locale(enum.StrEnum):
    """Interface language, and the language an entry was authored in.

    The two are independent (FR-023): changing the interface never re-languages
    stored content.
    """

    en = "en"
    ja = "ja"


class CareerProfile(Entity):
    __tablename__ = "career_profile"

    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), unique=True, nullable=False)
    interface_locale: Mapped[Locale] = mapped_column(
        Enum(Locale, name="locale"), default=Locale.en, nullable=False
    )

    # Deletion splits in two (FR-024, FR-025). The immediately-erased fields are
    # destroyed on the request path; what remains is soft deleted until purge_after.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # Indexed because the purge job sweeps by this column.
    purge_after: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, index=True
    )

    # Every section cascades from the root, so deleting a profile removes its
    # entries, stories and snapshots together (FR-031 and the deletion edge case).
    snapshots: Mapped[list["EntrySnapshot"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    identity: Mapped["Identity | None"] = relationship(cascade="all, delete-orphan", uselist=False)
    japan: Mapped["JapanProfile | None"] = relationship(cascade="all, delete-orphan", uselist=False)
    preferences: Mapped["CareerPreference | None"] = relationship(
        cascade="all, delete-orphan", uselist=False
    )
    experiences: Mapped[list["WorkExperience"]] = relationship(cascade="all, delete-orphan")
    education: Mapped[list["Education"]] = relationship(cascade="all, delete-orphan")
    certifications: Mapped[list["Certification"]] = relationship(cascade="all, delete-orphan")
    skills: Mapped[list["Skill"]] = relationship(cascade="all, delete-orphan")
    languages: Mapped[list["Language"]] = relationship(cascade="all, delete-orphan")
    stories: Mapped[list["CareerStory"]] = relationship(cascade="all, delete-orphan")

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class EntrySnapshot(Entity):
    """An immutable copy of the entries a generated document drew on.

    Insert-only by contract (FR-029). Nothing in the application updates a
    snapshot after creation, which is what keeps a generated document's claims
    traceable once the entries behind them are edited or deleted (FR-028, and
    constitution Principle IV).
    """

    __tablename__ = "entry_snapshot"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("career_profile.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Kept alongside the content so a claim can be traced both to what it said at
    # the time and back to the live entry, where that entry still exists (FR-010).
    captured_entry_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)), nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    profile: Mapped[CareerProfile] = relationship(back_populates="snapshots")


class EmploymentType(enum.StrEnum):
    permanent = "permanent"
    contract = "contract"
    part_time = "part_time"
    internship = "internship"
    freelance = "freelance"


class SkillLevel(enum.StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class LanguageProficiency(enum.StrEnum):
    native = "native"
    business = "business"
    conversational = "conversational"
    basic = "basic"


class WorkingArrangement(enum.StrEnum):
    onsite = "onsite"
    hybrid = "hybrid"
    remote = "remote"


class ProfileOwned:
    """Mixin for entities that belong to exactly one profile."""

    @declared_attr
    def profile_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            ForeignKey("career_profile.id", ondelete="CASCADE"), nullable=False, index=True
        )


class Identity(Entity, ProfileOwned):
    """Names and contact details.

    One name string rather than separate given and family fields: a single-part
    name, or a name that does not split that way, must be valid (spec edge cases).
    """

    __tablename__ = "identity"

    full_name_latin: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name_japanese: Mapped[str | None] = mapped_column(String(255), default=None)
    furigana: Mapped[str | None] = mapped_column(String(255), default=None)
    email: Mapped[str | None] = mapped_column(String(320), default=None)
    phone: Mapped[str | None] = mapped_column(String(50), default=None)


class JapanProfile(Entity, ProfileOwned):
    """Japan-specific hiring circumstances.

    Every field is optional (FR-005) and every disclosure flag defaults to false
    **in the schema**, not merely in the interface (FR-006, constitution gate G5).
    These fields carry discrimination risk, so the closed default is the point.

    The first four are erased immediately and unrecoverably when a profile is
    deleted (FR-024); see deletion.py.
    """

    __tablename__ = "japan_profile"

    residence_status: Mapped[str | None] = mapped_column(String(255), default=None)
    nationality: Mapped[str | None] = mapped_column(String(255), default=None)
    visa_type: Mapped[str | None] = mapped_column(String(255), default=None)
    visa_expires_on: Mapped[date | None] = mapped_column(Date, default=None)
    work_authorisation: Mapped[bool | None] = mapped_column(Boolean, default=None)
    japanese_qualification: Mapped[str | None] = mapped_column(String(255), default=None)

    disclose_residence_status: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    disclose_nationality: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    disclose_visa: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    disclose_work_authorisation: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    disclose_japanese_qualification: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Erased on the request path when a profile is deleted, never soft deleted.
    IMMEDIATELY_ERASED = (
        "residence_status",
        "nationality",
        "visa_type",
        "visa_expires_on",
    )


# Skills record where they were used; the join carries no attributes of its own.
skill_experience = Table(
    "skill_experience",
    Entity.metadata,
    Column("skill_id", ForeignKey("skill.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "work_experience_id",
        ForeignKey("work_experience.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class WorkExperience(Entity, ProfileOwned):
    """One role at one employer over a period.

    A null `ended_on` means the role is ongoing, and counts as extending to the
    present when ranges are compared (research.md R-004). Overlapping experiences
    are legitimate — concurrent roles and contract work — and are accepted without
    warning.
    """

    __tablename__ = "work_experience"

    employer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Derived, never shown. Exists so two sources writing the employer slightly
    # differently still match during duplicate detection.
    employer_name_normalised: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        Enum(EmploymentType, name="employment_type"), default=None
    )
    started_on: Mapped[date] = mapped_column(Date, nullable=False)
    ended_on: Mapped[date | None] = mapped_column(Date, default=None)
    description: Mapped[str] = mapped_column(Text, default="")
    source_language: Mapped[Locale] = mapped_column(
        Enum(Locale, name="locale"), default=Locale.en, nullable=False
    )

    skills: Mapped[list["Skill"]] = relationship(
        secondary=skill_experience, back_populates="experiences"
    )
    stories: Mapped[list["CareerStory"]] = relationship(back_populates="experience")

    @property
    def is_ongoing(self) -> bool:
        return self.ended_on is None


class Education(Entity, ProfileOwned):
    __tablename__ = "education"

    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    qualification: Mapped[str | None] = mapped_column(String(255), default=None)
    field_of_study: Mapped[str | None] = mapped_column(String(255), default=None)
    started_on: Mapped[date | None] = mapped_column(Date, default=None)
    ended_on: Mapped[date | None] = mapped_column(Date, default=None)
    source_language: Mapped[Locale] = mapped_column(
        Enum(Locale, name="locale"), default=Locale.en, nullable=False
    )


class Certification(Entity, ProfileOwned):
    __tablename__ = "certification"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(255), default=None)
    issued_on: Mapped[date | None] = mapped_column(Date, default=None)
    expires_on: Mapped[date | None] = mapped_column(Date, default=None)
    source_language: Mapped[Locale] = mapped_column(
        Enum(Locale, name="locale"), default=Locale.en, nullable=False
    )


class Skill(Entity, ProfileOwned):
    __tablename__ = "skill"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[SkillLevel | None] = mapped_column(
        Enum(SkillLevel, name="skill_level"), default=None
    )

    experiences: Mapped[list[WorkExperience]] = relationship(
        secondary=skill_experience, back_populates="skills"
    )


class Language(Entity, ProfileOwned):
    """A language and how well the user speaks it.

    Proficiency is a typed enumeration rather than free text (constitution gate G9).
    """

    __tablename__ = "language"

    language: Mapped[str] = mapped_column(String(100), nullable=False)
    proficiency: Mapped[LanguageProficiency] = mapped_column(
        Enum(LanguageProficiency, name="language_proficiency"), nullable=False
    )
    qualification: Mapped[str | None] = mapped_column(String(255), default=None)


class CareerPreference(Entity, ProfileOwned):
    __tablename__ = "career_preference"

    desired_roles: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    desired_locations: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    working_arrangement: Mapped[WorkingArrangement | None] = mapped_column(
        Enum(WorkingArrangement, name="working_arrangement"), default=None
    )
    salary_min: Mapped[int | None] = mapped_column(Integer, default=None)
    salary_max: Mapped[int | None] = mapped_column(Integer, default=None)
    currency: Mapped[str | None] = mapped_column(String(3), default=None)
    source_language: Mapped[Locale] = mapped_column(
        Enum(Locale, name="locale"), default=Locale.en, nullable=False
    )


class CareerStory(Entity, ProfileOwned):
    """A structured accomplishment, reusable as a STAR example (FR-007).

    Defined here rather than with User Story 2 because profile deletion must
    cascade to stories, and that rule lives in this story.
    """

    __tablename__ = "career_story"

    work_experience_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("work_experience.id", ondelete="SET NULL"), default=None, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    challenge: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    source_language: Mapped[Locale] = mapped_column(
        Enum(Locale, name="locale"), default=Locale.en, nullable=False
    )

    experience: Mapped[WorkExperience | None] = relationship(back_populates="stories")
