"""Request and response models, matching contracts/openapi.yaml."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.imports.models import FailureReason, ImportStatus, SourceKind


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PasteImportIn(BaseModel):
    text: str = Field(min_length=1, description="Any free text describing the user's career")


class ImportOut(ORMModel):
    """The record kept after review.

    Carries no filename, by decision: a name such as the company someone was
    applying to reveals their job search, and nothing needs it once extraction
    is done (FR-019b).
    """

    id: uuid.UUID
    source_kind: SourceKind
    status: ImportStatus
    failure_reason: FailureReason | None = None
    started_at: datetime
    completed_at: datetime | None = None
    entry_count: int


class ExtractionOutcomeOut(BaseModel):
    found: dict[str, int] = {}
    not_found: list[str] = []
    message: str = ""


class ImportDetailOut(ImportOut):
    outcome: ExtractionOutcomeOut | None = None
