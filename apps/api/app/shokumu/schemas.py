"""Request and response models, matching contracts/openapi.yaml.

Feature 004's own, rather than imported from feature 003. The two documents
share their machinery — the font, the paper, the page that knows when it is
full — but each publishes its own contract, and a client generated from one
must not change because the other's enum moved.
"""

import enum

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
