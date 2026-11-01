"""Request and response models, matching contracts/openapi.yaml.

Feature 004's own, rather than imported from feature 003. The two documents
share their machinery — the font, the paper, the page that knows when it is
full — but each publishes its own contract, and a client generated from one
must not change because the other's enum moved.
"""

import enum
import uuid

from pydantic import BaseModel


class Arrangement(enum.StrEnum):
    """The order the employer sections run in.

    Both carry the identical set of entries; only the order differs (FR-008).
    Grouping by project is not offered: the profile holds no project entity,
    and a career story has no client, period or role to build one from.
    """

    reverse_chronological = "reverse_chronological"
    chronological = "chronological"


class DateConvention(enum.StrEnum):
    """Which calendar the dates are written in.

    One convention throughout a document; the two never appear together
    (FR-009).
    """

    seireki = "seireki"
    wareki = "wareki"


class PaperSize(enum.StrEnum):
    a4 = "a4"
    b5 = "b5"


class ShokumuKeirekishoRequest(BaseModel):
    """What the user chose for this document.

    None of it affects what the document says, only how it reads.
    """

    arrangement: Arrangement = Arrangement.reverse_chronological
    date_convention: DateConvention = DateConvention.seireki
    paper_size: PaperSize = PaperSize.a4


class UnattachedAchievement(BaseModel):
    """An achievement recorded against no employer.

    Named so the user can recognise it and attach it to one if that is what
    they meant. It is in the document either way, in the closing section.
    """

    entry_id: uuid.UUID
    title: str


class ReadinessReport(BaseModel):
    """What a document would lack.

    Separates what cannot be left out from what will simply be blank, because
    the two need different responses from the user.
    """

    can_generate: bool
    missing_required: list[str] = []
    missing_optional: list[str] = []
    unattached_achievements: list[UnattachedAchievement] = []
