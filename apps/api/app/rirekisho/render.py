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

from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: E402
from reportlab.pdfgen.canvas import Canvas  # noqa: E402

from app.imports.dates import format_japanese_date, format_year_month  # noqa: E402
from app.rirekisho.rows import Row, RowEvent  # noqa: E402

MARGIN = 40
TITLE_SIZE = 18
HEADING_SIZE = 11
BODY_SIZE = 10
LINE_HEIGHT = 18

# Marks a section that carries on from the previous page.
CONTINUED = "（続き）"

# The photograph frame, drawn empty at the top right of page 1 where
# convention places it. Text beside it has to stop short of its left edge: a
# line that runs under the frame survives in the file and is covered by the
# photograph on the page that gets handed over (#106).
PHOTO_WIDTH = 90
PHOTO_HEIGHT = 120
PHOTO_GAP = 10

# How each Japan-specific field is labelled in 本人希望記入欄. Keyed by the
# profile field, as the disclosure filter returns them. A field missing here is
# refused rather than drawn under its raw name.
DISCLOSED_LABELS = {
    "residence_status": "在留資格",
    "nationality": "国籍",
    "visa_type": "ビザの種類",
    "visa_expires_on": "在留期限",
    "work_authorisation": "就労資格",
    "japanese_qualification": "日本語能力",
}


def _format(value: date | None, *, era: bool) -> str:
    """A date as the table writes it, or nothing where there is none."""
    return "" if value is None else format_year_month(value, era=era)


def _wrap(text: str, first: float, rest: float, size: int, keep: int = 0) -> list[str]:
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


def _disclosed_value(value: str | date | bool, *, era: bool) -> str:
    """A disclosed value as the document writes it.

    A date follows the document's convention like every other date (FR-019).
    Work authorisation is recorded as yes or no, and written as such.
    """
    if isinstance(value, bool):
        return "あり" if value else "なし"
    if isinstance(value, date):
        return format_japanese_date(value, era=era)
    return value


class _Page:
    """A page that knows when it is full.

    A history longer than the conventional length produces more pages rather
    than losing entries (FR-018a). Only the user can judge which roles matter,
    so the renderer never makes that choice for them.

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
        # The height above which the photograph frame stands in the way, or
        # None where nothing does.
        self.keep_clear: float | None = None

    def reserve_photo(self) -> None:
        """Keep text clear of the photograph frame while it is beside it."""
        self.keep_clear = self.height - MARGIN - PHOTO_HEIGHT

    def _right(self) -> float:
        """How far right text may reach at the height it is about to be drawn."""
        if self.keep_clear is not None and self.y > self.keep_clear:
            return self.width - MARGIN - PHOTO_WIDTH - PHOTO_GAP
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
            # The frame is on page 1 only; later pages have their full width.
            self.keep_clear = None
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
        lines = _wrap(text, available, available - indent, size, keep=len(hang))

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


def render_rirekisho(
    *,
    identity: dict[str, str | date | None],
    rows: list[Row],
    certifications: list[tuple[date | None, str]] | None = None,
    disclosed: dict[str, str | date | bool] | None = None,
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

    # The frame below is drawn after the identity block, but the block has to
    # know about it before it is wrapped, or a long line runs underneath it
    # and the photograph covers it (#106).
    page.reserve_photo()

    # Identity. Each label is drawn whether or not it has a value, so a user can
    # see what is blank rather than discovering it after printing (FR-022c).
    page.line(f"ふりがな　{identity.get('furigana') or ''}", hang="ふりがな　")
    display_name = identity.get("full_name_japanese") or identity.get("full_name_latin") or ""
    page.line(f"氏名　　　{display_name}", hang="氏名　　　")
    # In the chosen convention like every other date, or the document would mix
    # the two (FR-019).
    born = identity.get("date_of_birth")
    page.line(f"生年月日　{format_japanese_date(born, era=era) if isinstance(born, date) else ''}")
    page.line(f"現住所　　{identity.get('address') or ''}", hang="現住所　　")
    page.line(f"電話　　　{identity.get('phone') or ''}")
    page.line(f"メール　　{identity.get('email') or ''}", hang="メール　　")
    page.gap()

    # The photograph frame, drawn where convention places it and left empty.
    # The product stores no photograph (FR-022a).
    canvas.rect(
        page.width - MARGIN - PHOTO_WIDTH,
        page.height - MARGIN - PHOTO_HEIGHT,
        PHOTO_WIDTH,
        PHOTO_HEIGHT,
    )
    canvas.setFont(FONT_NAME, 8)
    canvas.drawString(
        page.width - MARGIN - PHOTO_WIDTH + 4,
        page.height - MARGIN - PHOTO_HEIGHT - 14,
        "写真貼付欄",
    )

    page.heading("学歴・職歴")
    for row in rows:
        if row.event is RowEvent.end:
            # 以上 sits at the right, as convention places it.
            page.space_for()
            canvas.setFont(FONT_NAME, BODY_SIZE)
            canvas.drawRightString(page.width - MARGIN, page.y, str(RowEvent.end))
            page.y -= LINE_HEIGHT
            continue

        column = f"{_format(row.date, era=era):<14}"
        page.line(f"{column}{row.institution}　{row.event}", hang=column)

    page.gap()
    page.heading("免許・資格")
    for when, name in certifications or []:
        column = f"{_format(when, era=era):<14}"
        page.line(f"{column}{name}", hang=column)

    page.gap()
    page.heading("本人希望記入欄")
    # Only fields the user marked includable reach this far; the filter runs
    # before rendering, so an undisclosed value is never passed in (gate G5).
    # Neither is its label: an undisclosed field leaves no trace, not a blank.
    for field, value in (disclosed or {}).items():
        label = f"{DISCLOSED_LABELS[field]}　"
        page.line(f"{label}{_disclosed_value(value, era=era)}", hang=label)

    page.gap()
    page.heading("志望の動機")
    # Written for a particular employer rather than held as career history, so
    # the section is labelled and left for the user (FR-022b).

    page.finish()
    canvas.save()
    return buffer.getvalue(), page.pages
