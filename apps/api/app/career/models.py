"""Career module entities.

Only the profile root and the snapshot are defined here for now; the typed
sections arrive with User Story 1. See specs/001-master-career-profile/data-model.md.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    snapshots: Mapped[list["EntrySnapshot"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

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
        ForeignKey("career_profile.id", ondelete="CASCADE"), nullable=False
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
