"""Request and response models, matching contracts/openapi.yaml."""

import enum
import uuid

from pydantic import BaseModel


class DateConvention(enum.StrEnum):
    """Which calendar the dates are written in.

    One convention throughout a document; the two never appear together
    (FR-019).
    """

    seireki = "seireki"
    wareki = "wareki"


class PaperSize(enum.StrEnum):
    a4 = "a4"
    b5 = "b5"


class RirekishoRequest(BaseModel):
    """What the user chose for this document.

    Neither field affects what the document says, only how it reads.
    """

    date_convention: DateConvention = DateConvention.seireki
    paper_size: PaperSize = PaperSize.a4


class EnglishEntry(BaseModel):
    """An entry that will appear in English, because that is how it was written."""

    entry_id: uuid.UUID
    entry_type: str
    label: str


class ReadinessReport(BaseModel):
    """What a document would lack.

    Separates what cannot be left out from what will simply be blank, because
    the two need different responses from the user.
    """

    can_generate: bool
    missing_required: list[str] = []
    missing_optional: list[str] = []
    entries_without_japanese: list[EnglishEntry] = []
