"""Verifying that an extracted value came from the document.

This module is the enforcement of Principle IV. The prompt is not.

A model asked not to fabricate will still fabricate sometimes, and no wording
changes that. What changes it is making a fabricated field impossible to
deliver: every value arrives with the passage of source text it was taken from,
and a value the model invented has no such passage. The check below is a string
search, and a string search does not have opinions.

Rules that look like details and are not:

  * Matching is whitespace-normalised, because extracted document text routinely
    differs from the original in line breaks and spacing. A correct extraction
    must not fail over a newline.

  * Matching is otherwise exact. There is no fuzzy matching, no similarity
    threshold, no "close enough". Every one of those reopens the gap this module
    exists to close — a fabricated quote is usually plausible, which is exactly
    what a similarity score rewards.

  * A field that fails verification is dropped, not flagged. A value shown to a
    user with a warning is still a value they might accept (FR-008).
"""

import logging
import re
import unicodedata

from app.ai.schemas import ExtractedEntry, ExtractedField

logger = logging.getLogger(__name__)

# A quote this short matches almost anything and evidences almost nothing.
MINIMUM_QUOTE_LENGTH = 3


def normalise(text: str) -> str:
    """Reduce text to a form where only its characters matter.

    Unicode is normalised so that a full-width character extracted from a
    Japanese document matches the same character in the source, and whitespace
    runs collapse so line breaks introduced by extraction do not defeat a
    correct quote.
    """
    folded = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", folded).strip().casefold()


def quote_is_supported(quote: str, source: str) -> bool:
    """Does this passage actually appear in the source?"""
    if not quote or len(quote.strip()) < MINIMUM_QUOTE_LENGTH:
        return False
    return normalise(quote) in normalise(source)


def verify_fields(
    fields: dict[str, ExtractedField], source: str
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """Keep the fields the source supports; drop the rest.

    Returns the surviving values, and the evidence for them. A dropped field
    appears in neither: it is left empty and marked not found by its absence,
    exactly as if the model had reported nothing for it.
    """
    values: dict[str, str] = {}
    evidence: dict[str, dict[str, str]] = {}

    for name, field in fields.items():
        if not quote_is_supported(field.quote, source):
            logger.info(
                "dropped unverifiable field",
                extra={"entry_type": name, "outcome": "unverified"},
            )
            continue

        values[name] = field.value
        evidence[name] = {"quote": field.quote, "verified": True}

    return values, evidence


def verify_entry(
    entry: ExtractedEntry, source: str
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    return verify_fields(entry.fields, source)
