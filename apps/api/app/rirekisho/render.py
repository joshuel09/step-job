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


# --- the document ------------------------------------------------------------

from datetime import date  # noqa: E402
from io import BytesIO  # noqa: E402

from reportlab.pdfgen.canvas import Canvas  # noqa: E402

from app.imports.dates import format_japanese_date, format_year_month  # noqa: E402
from app.rirekisho.rows import Row, RowEvent  # noqa: E402

MARGIN = 40
TITLE_SIZE = 18
HEADING_SIZE = 11
BODY_SIZE = 10
LINE_HEIGHT = 18


def _format(value: date | None, *, era: bool) -> str:
    """A date as the table writes it, or nothing where there is none."""
    return "" if value is None else format_year_month(value, era=era)


class _Page:
    """A page that knows when it is full.

    A history longer than the conventional length produces more pages rather
    than losing entries (FR-018a). Only the user can judge which roles matter,
    so the renderer never makes that choice for them.
    """

    def __init__(self, canvas: Canvas, size: tuple[float, float]) -> None:
        self.canvas = canvas
        self.width, self.height = size
        self.y = self.height - MARGIN
        self.pages = 1

    def space_for(self, lines: int = 1) -> None:
        if self.y - lines * LINE_HEIGHT < MARGIN:
            self.canvas.showPage()
            self.canvas.setFont(FONT_NAME, BODY_SIZE)
            self.y = self.height - MARGIN
            self.pages += 1

    def line(self, text: str, x: float = MARGIN, size: int = BODY_SIZE) -> None:
        self.space_for()
        self.canvas.setFont(FONT_NAME, size)
        self.canvas.drawString(x, self.y, text)
        self.y -= LINE_HEIGHT

    def gap(self, lines: float = 0.5) -> None:
        self.y -= LINE_HEIGHT * lines


def render_rirekisho(
    *,
    identity: dict[str, str | date | None],
    rows: list[Row],
    certifications: list[tuple[date | None, str]] | None = None,
    disclosed: dict[str, str] | None = None,
    era: bool = False,
    paper: str = "a4",
) -> tuple[bytes, int]:
    """Draw the document. Returns the file and how many pages it runs to.

    Every value here comes from the profile. A field the profile does not hold
    is drawn as an empty label rather than filled with something plausible
    (FR-013), and nothing is translated on the way in (FR-014a).
    """
    register_font()
    size = page_size(paper)

    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=size)
    page = _Page(canvas, size)

    page.line("履歴書", size=TITLE_SIZE)
    page.gap()

    # Identity. Each label is drawn whether or not it has a value, so a user can
    # see what is blank rather than discovering it after printing (FR-022c).
    page.line(f"ふりがな　{identity.get('furigana') or ''}")
    display_name = identity.get("full_name_japanese") or identity.get("full_name_latin") or ""
    page.line(f"氏名　　　{display_name}")
    # In the chosen convention like every other date, or the document would mix
    # the two (FR-019).
    born = identity.get("date_of_birth")
    page.line(f"生年月日　{format_japanese_date(born, era=era) if isinstance(born, date) else ''}")
    page.line(f"現住所　　{identity.get('address') or ''}")
    page.line(f"電話　　　{identity.get('phone') or ''}")
    page.line(f"メール　　{identity.get('email') or ''}")
    page.gap()

    # The photograph frame, drawn where convention places it and left empty.
    # The product stores no photograph (FR-022a).
    canvas.rect(page.width - MARGIN - 90, page.height - MARGIN - 120, 90, 120)
    canvas.setFont(FONT_NAME, 8)
    canvas.drawString(page.width - MARGIN - 86, page.height - MARGIN - 134, "写真貼付欄")

    page.line("学歴・職歴", size=HEADING_SIZE)
    for row in rows:
        if row.event is RowEvent.end:
            # 以上 sits at the right, as convention places it.
            page.space_for()
            canvas.setFont(FONT_NAME, BODY_SIZE)
            canvas.drawRightString(page.width - MARGIN, page.y, str(RowEvent.end))
            page.y -= LINE_HEIGHT
            continue

        when = _format(row.date, era=era)
        page.line(f"{when:<14}{row.institution}　{row.event}")

    page.gap()
    page.line("免許・資格", size=HEADING_SIZE)
    for when, name in certifications or []:
        page.line(f"{_format(when, era=era):<14}{name}")

    page.gap()
    page.line("本人希望記入欄", size=HEADING_SIZE)
    # Only fields the user marked includable reach this far; the filter runs
    # before rendering, so an undisclosed value is never passed in (gate G5).
    for label, value in (disclosed or {}).items():
        page.line(f"{label}　{value}")

    page.gap()
    page.line("志望の動機", size=HEADING_SIZE)
    # Written for a particular employer rather than held as career history, so
    # the section is labelled and left for the user (FR-022b).

    canvas.save()
    return buffer.getvalue(), page.pages
