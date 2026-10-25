"""The typographic base both Japanese documents draw on.

The 履歴書 (feature 003) and the 職務経歴書 (feature 004) are different
documents with the same mechanics: one embedded Japanese typeface, the same
two paper sizes, and the same need to know when a page is full and start
another one. Keeping those in one place is what stops them drifting — a font
registered twice under one name, or two page classes that disagree about
where the bottom of the paper is.

What belongs here is anything a second document would otherwise copy. What
does not is anything either document decides for itself: its margins are
shared, but its sections, its headings and what it reserves space for are
its own.

The font is registered at import rather than at render. A missing Japanese
typeface is the quiet failure in both features: the document is produced at
the right size with every character a hollow box, and a developer whose
machine has Japanese system fonts may never see it. Failing when the
application starts turns that into an obvious problem rather than a subtle
one.
"""

import logging
from pathlib import Path

from reportlab.lib.pagesizes import A4, B5
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

logger = logging.getLogger(__name__)

FONT_NAME = "IPAexGothic"
FONT_PATH = Path(__file__).parent / "fonts" / "ipaexg.ttf"

# Both documents are conventionally B5 or A4; the user chooses (FR-018).
PAGE_SIZES = {"a4": A4, "b5": B5}

MARGIN = 40
TITLE_SIZE = 18
HEADING_SIZE = 11
BODY_SIZE = 10
LINE_HEIGHT = 18

# Marks a section that carries on from the previous page.
CONTINUED = "（続き）"


class FontUnavailable(RuntimeError):
    """The Japanese font could not be loaded.

    Raised at startup rather than swallowed, because the alternative is a
    document full of hollow boxes that looks fine to anything checking sizes.
    """


def register_font() -> None:
    """Make the Japanese font available, or refuse to start.

    Idempotent: registering twice is harmless, which matters because the
    application and the tests both arrive here, and now two features do.
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
# request.
register_font()


def wrap(text: str, first: float, rest: float, size: int, keep: int = 0) -> list[str]:
    """Split text into lines no wider than the space each one has.

    Every character is kept: a long name moves onto more lines, it is never cut
    to fit (FR-018a). Japanese breaks between any two characters. Where a break
    would split an English word, it moves back to the last space instead — but
    never into the first `keep` characters, the date column or label, which is
    padded with spaces and must stay on the first line with what follows it.
    """
    lines: list[str] = []
    width, floor = first, keep
    while stringWidth(text, FONT_NAME, size) > width:
        cut = floor + 1
        while cut < len(text) and stringWidth(text[: cut + 1], FONT_NAME, size) <= width:
            cut += 1

        if _mid_word(text, cut):
            space = text.rfind(" ", floor + 1, cut)
            if space > floor:
                cut = space + 1

        lines.append(text[:cut].rstrip(" "))
        text = text[cut:].lstrip(" ")
        width, floor = rest, 0
    lines.append(text)
    return lines


def _mid_word(text: str, cut: int) -> bool:
    """Whether a break at `cut` would split a word of Latin letters or digits."""
    if not 0 < cut < len(text):
        return False
    before, after = text[cut - 1], text[cut]
    return before.isascii() and after.isascii() and before.isalnum() and after.isalnum()


class Page:
    """A page that knows when it is full.

    A history longer than the conventional length produces more pages rather
    than losing entries (FR-018a). Only the user can judge which roles matter,
    so a renderer never makes that choice for them.

    A page that starts partway through a section says which section it is, so
    page two can be read on its own: an employer may well hold the pages apart.
    """

    def __init__(self, canvas: Canvas, size: tuple[float, float]) -> None:
        self.canvas = canvas
        self.width, self.height = size
        self.y = self.height - MARGIN
        self.pages = 1
        self.section: str | None = None
        self._pending: str | None = None
        # A box in the top-right corner that text must keep out of, as
        # (width, height), or None where nothing is in the way. The 履歴書 has
        # a photograph frame there; the 職務経歴書 has nothing.
        self._reserved: tuple[float, float] | None = None

    def reserve_top_right(self, width: float, height: float, gap: float) -> None:
        """Keep text clear of a box in the top-right corner of this page.

        Text that runs under it survives in the file and is covered on the
        page that gets handed over, which is the copy that matters (#106).
        """
        self._reserved = (width + gap, self.height - MARGIN - height)

    def _right(self) -> float:
        """How far right text may reach at the height it is about to be drawn."""
        if self._reserved is not None and self.y > self._reserved[1]:
            return self.width - MARGIN - self._reserved[0]
        return self.width - MARGIN

    def space_for(self, lines: int = 1) -> None:
        """Make room for `lines` lines, and for a heading still waiting to be drawn.

        A heading waits for its first row so the two land on the same page,
        however many lines that row wraps to (#105).
        """
        needed = lines + (1 if self._pending else 0)
        if self.y - needed * LINE_HEIGHT < MARGIN:
            self.canvas.showPage()
            self.canvas.setFont(FONT_NAME, BODY_SIZE)
            self.y = self.height - MARGIN
            self.pages += 1
            # Whatever was in the way was on that page, not this one.
            self._reserved = None
            if self.section and not self._pending:
                self._draw(f"{self.section}{CONTINUED}", MARGIN, HEADING_SIZE)

        if self._pending:
            self._draw(self._pending, MARGIN, HEADING_SIZE)
            self.section, self._pending = self._pending, None

    def heading(self, text: str) -> None:
        """A section title, kept on the same page as its first row.

        Drawn when that row arrives, since only then is its height known. A
        section with no rows has its heading drawn before whatever comes next.
        """
        self.finish()
        self.section = None
        self._pending = text

    def finish(self) -> None:
        """Draw a heading still waiting for a row that never came."""
        if self._pending:
            self.space_for(0)

    def line(self, text: str, x: float = MARGIN, size: int = BODY_SIZE, hang: str = "") -> None:
        """One entry, wrapped onto as many lines as it needs and kept together.

        Continuation lines start under the text after `hang` — the date column,
        or a label — so a wrapped name still reads as one entry.
        """
        indent = stringWidth(hang, FONT_NAME, size)
        available = self._right() - x
        lines = wrap(text, available, available - indent, size, keep=len(hang))

        self.space_for(len(lines))
        for number, part in enumerate(lines):
            self._draw(part, x if number == 0 else x + indent, size)

    def gap(self, lines: float = 0.5) -> None:
        self.finish()
        self.y -= LINE_HEIGHT * lines

    def _draw(self, text: str, x: float, size: int) -> None:
        self.canvas.setFont(FONT_NAME, size)
        self.canvas.drawString(x, self.y, text)
        self.y -= LINE_HEIGHT
