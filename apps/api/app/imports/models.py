"""Import entities.

See specs/002-ai-resume-import/data-model.md for the rules these encode.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.career.models import ProfileOwned
from app.db.base import Entity


class SourceKind(enum.StrEnum):
    pasted_text = "pasted_text"
    pdf = "pdf"
    docx = "docx"


class ImportStatus(enum.StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class FailureReason(enum.StrEnum):
    """Why an import failed.

    These are separate values because they look alike to a user and are not
    alike at all. A document with no text layer will never succeed however many
    times it is tried; an unavailable service very likely will. Collapsing them
    would leave the interface unable to tell someone whether coming back later
    is worth their time (FR-017b).
    """

    unreadable_document = "unreadable_document"
    unsupported_format = "unsupported_format"
    no_career_information = "no_career_information"
    service_unavailable = "service_unavailable"
    extraction_failed = "extraction_failed"


class Import(Entity, ProfileOwned):
    """One attempt to bring career information in from a source."""

    __tablename__ = "import"

    source_kind: Mapped[SourceKind] = mapped_column(
        Enum(SourceKind, name="import_source_kind"), nullable=False
    )
    status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, name="import_status"),
        default=ImportStatus.pending,
        server_default="pending",
        nullable=False,
        index=True,
    )
    failure_reason: Mapped[FailureReason | None] = mapped_column(
        Enum(FailureReason, name="import_failure_reason"), default=None
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # What was found, and what was looked for and not found, so a user can see
    # what the document lacked rather than assume something was lost (FR-016).
    outcome: Mapped[dict | None] = mapped_column(JSONB, default=None)

    # Proposals produced. Zero is a valid completed outcome.
    entry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    # Deliberately absent: the filename.
    #
    # This record survives review, and a name such as the company someone was
    # applying to reveals their job search. Nothing after extraction needs it
    # (FR-019b). Also absent: the document and its text — the bytes are never
    # written at all, and the extracted text lives only as the evidence attached
    # to each proposal, and only until that proposal is reviewed.

    @property
    def is_terminal(self) -> bool:
        return self.status in (ImportStatus.completed, ImportStatus.failed)
