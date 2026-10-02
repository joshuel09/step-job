"""Drawing the 履歴書.

The only module here that knows a PDF exists. Everything upstream — the table
projection, the disclosure filter, the date conventions — produces plain values,
so a layout problem stays a layout problem and a rule can be tested without
rendering anything.

The font is registered at import rather than at render. A missing Japanese
typeface is the quiet failure in this feature: the document is produced at the
right size with every character a hollow box, and a developer whose machine has
Japanese system fonts may never see it. Failing when the application starts
turns that into an obvious problem rather than a subtle one.
"""

import logging
from pathlib import Path

from reportlab.lib.pagesizes import A4, B5
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

FONT_NAME = "IPAexGothic"
FONT_PATH = Path(__file__).parent / "fonts" / "ipaexg.ttf"

# A 履歴書 is conventionally B5 or A4; the user chooses (FR-018).
PAGE_SIZES = {"a4": A4, "b5": B5}


class FontUnavailable(RuntimeError):
    """The Japanese font could not be loaded.

    Raised at startup rather than swallowed, because the alternative is a
    document full of hollow boxes that looks fine to anything checking sizes.
    """


def register_font() -> None:
    """Make the Japanese font available, or refuse to start.

    Idempotent: registering twice is harmless, which matters because the
    application and the tests both arrive here.
    """
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return

    if not FONT_PATH.is_file():
        raise FontUnavailable(
            f"The Japanese font is missing from {FONT_PATH}. Without it every "
            "character renders as an empty box, so the application refuses to "
            "start rather than produce unreadable documents."
        )

    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
    except Exception as error:  # pragma: no cover - a corrupt font file
        raise FontUnavailable(f"The Japanese font at {FONT_PATH} could not be loaded.") from error

    logger.info("japanese font registered", extra={"outcome": FONT_NAME})


def page_size(name: str):
    """The page dimensions for a chosen size."""
    try:
        return PAGE_SIZES[name.lower()]
    except KeyError:
        raise ValueError(f"Unknown paper size: {name!r}. Use 'a4' or 'b5'.") from None


# Registered at import so a missing font stops the application rather than one
# request. The layout itself arrives with User Story 1.
register_font()
