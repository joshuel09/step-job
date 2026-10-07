"""Which Japan-specific fields may appear in a document.

A pure function from the Japan profile to the fields the user opted in to. It
runs before rendering, so an undisclosed value never reaches the renderer at
all: a field that is never passed in cannot be drawn by a later layout change
(gate G5).

The disclosure flags have defaulted closed since feature 001. This is the
first code that reads them, so it is written as an allowlist: a field appears
only if it is named below and its own flag is set. A Japan-specific field added
later stays out of every document until someone decides which flag governs it.

Labels and formatting belong to the renderer. This module decides only whether
a value may appear, never how it reads.
"""

from datetime import date
from typing import Any

# Profile field, and the flag that must be set for it to appear. One flag can
# govern more than one field: the visa's type and expiry are disclosed together,
# because an expiry date on its own still says the holder needs a visa.
GOVERNED_BY: dict[str, str] = {
    "residence_status": "disclose_residence_status",
    "nationality": "disclose_nationality",
    "visa_type": "disclose_visa",
    "visa_expires_on": "disclose_visa",
    "work_authorisation": "disclose_work_authorisation",
    "japanese_qualification": "disclose_japanese_qualification",
}

DisclosedValue = str | date | bool


def disclosed_fields(japan: Any | None) -> dict[str, DisclosedValue]:
    """The fields that may appear, in the order the table above lists them.

    Only a flag that is exactly `True` discloses. An unsaved record carries
    `None` until the schema default is applied, and anything other than an
    explicit opt-in is a withheld field (FR-020).

    A disclosed field with no value is left out rather than drawn blank: there
    is nothing the user chose to show (FR-013). `False` is a value — a user can
    choose to say they lack work authorisation — so only `None` and empty text
    count as missing.
    """
    if japan is None:
        return {}

    fields: dict[str, DisclosedValue] = {}
    for field, flag in GOVERNED_BY.items():
        if getattr(japan, flag, None) is not True:
            continue

        value = getattr(japan, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue

        fields[field] = value
    return fields
