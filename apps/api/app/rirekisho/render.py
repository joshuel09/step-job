"""Drawing the 履歴書.

The only module here that knows a PDF exists. Everything upstream — the table
projection, the disclosure filter, the date conventions — produces plain values,
so a layout problem stays a layout problem and a rule can be tested without
rendering anything.

The font, the paper sizes and the page-flow class live in app/documents:
the 職務経歴書 needs the same ones, and two copies would be two chances for
them to disagree. What stays here is what this document decides for itself —
its sections, its labels, and the photograph frame it keeps text clear of.
"""

# --- the document ------------------------------------------------------------
from datetime import date
from io import BytesIO

from reportlab.pdfgen.canvas import Canvas

from app.documents.typography import (  # noqa: F401 - re-exported for callers
    BODY_SIZE,
    CONTINUED,
    FONT_NAME,
    FONT_PATH,
    HEADING_SIZE,
    LINE_HEIGHT,
    MARGIN,
    PAGE_SIZES,
    TITLE_SIZE,
    FontUnavailable,
    Page,
    page_size,
    register_font,
)
from app.imports.dates import format_japanese_date, format_year_month
from app.rirekisho.rows import Row, RowEvent

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
    page = Page(canvas, size)

    page.line("履歴書", size=TITLE_SIZE)
    page.gap()

    # The frame below is drawn after the identity block, but the block has to
    # know about it before it is wrapped, or a long line runs underneath it
    # and the photograph covers it (#106).
    page.reserve_top_right(PHOTO_WIDTH, PHOTO_HEIGHT, PHOTO_GAP)

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
