"""Drawing the 職務経歴書.

The only module here that knows a PDF exists. The projection, the summary and
the date conventions all produce plain values, so a layout problem stays a
layout problem and a rule can be tested without rendering anything.

The font, the paper sizes and the page-flow class come from app/documents,
shared with the 履歴書. What stays here is what this document decides for
itself: its sections, its labels, and the fact that it reserves nothing in the
top-right corner — a 職務経歴書 carries no photograph.

Every word on the page is either a value the user recorded or this module's
own fixed vocabulary. Nothing is translated, rephrased or inferred (FR-015).
"""

from datetime import date
from io import BytesIO

from reportlab.pdfgen.canvas import Canvas

from app.documents.typography import (
    BODY_SIZE,
    FONT_NAME,
    LINE_HEIGHT,
    MARGIN,
    TITLE_SIZE,
    Page,
    page_size,
    register_font,
)
from app.imports.dates import format_japanese_date, format_year_month
from app.shokumu import summary as summary_module
from app.shokumu.sections import CareerHistory, EmployerSection
from app.shokumu.summary import ONGOING, Summary

# The document's own headings, in the order they are drawn. A section with
# nothing under it is still labelled, so a blank reads as a decision rather
# than a defect (FR-013, FR-014).
SUMMARY = "職務要約"
HISTORY = "職務経歴"
UNATTACHED = "実績"
SKILLS = "活かせる経験・知識・技術"
LANGUAGES = "語学"
CERTIFICATIONS = "免許・資格"
SELF_PR = "自己PR"
END = "以上"

# The labels inside an employer section.
PERIOD = "期間　"
ROLE = "職種　"
EMPLOYMENT = "雇用形態　"
ACHIEVEMENTS = "実績"
CHALLENGE = "課題　"
ACTION = "取組　"
RESULT = "成果　"
NAME = "氏名　"
WRITTEN_ON = "作成日　"

# A value the profile stores as an enumeration is the product's vocabulary,
# not the user's words, so it is written in the document's language. A member
# missing from one of these maps is refused rather than drawn under its raw
# English name — the failure would otherwise be a Japanese document with
# "part_time" in it.
EMPLOYMENT_LABELS = {
    "permanent": "正社員",
    "contract": "契約社員",
    "part_time": "アルバイト・パート",
    "internship": "インターン",
    "freelance": "業務委託",
}

SKILL_LABELS = {
    "beginner": "初級",
    "intermediate": "中級",
    "advanced": "上級",
    "expert": "エキスパート",
}

PROFICIENCY_LABELS = {
    "native": "母語",
    "business": "ビジネスレベル",
    "conversational": "日常会話レベル",
    "basic": "基礎レベル",
}


def _label(labels: dict[str, str], value: str, kind: str) -> str:
    try:
        return labels[value]
    except KeyError:
        raise ValueError(
            f"No Japanese label for {kind} {value!r}. A document would otherwise "
            "carry the stored English name."
        ) from None


def _period(section: EmployerSection, *, era: bool) -> str:
    """The employer's period, with 現在 where the role is ongoing.

    An absent start date is written as nothing rather than guessed at: the
    entry is still drawn, which is the point (FR-011).
    """
    start = "" if section.started_on is None else format_year_month(section.started_on, era=era)
    end = ONGOING if section.ended_on is None else format_year_month(section.ended_on, era=era)
    return f"{start}〜{end}"


def render_shokumu_keirekisho(
    *,
    name: str,
    history: CareerHistory,
    summary: Summary,
    era: bool = False,
    paper: str = "a4",
    today: date | None = None,
) -> tuple[bytes, int]:
    """Draw the document. Returns the file and how many pages it runs to.

    `today` is a parameter rather than a call to the clock, so a document can
    be rendered twice and compared.
    """
    register_font()
    size = page_size(paper)
    today = today or date.today()

    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=size)
    page = Page(canvas, size)

    page.line(HISTORY + "書", size=TITLE_SIZE)
    page.gap()
    page.line(f"{NAME}{name}", hang=NAME)
    page.line(f"{WRITTEN_ON}{format_japanese_date(today, era=era)}", hang=WRITTEN_ON)
    page.gap()

    # Facts that can be counted, and nothing else (R-003). A profile too thin
    # to summarise produces fewer lines rather than a reaching sentence.
    page.heading(SUMMARY)
    for line in summary_module.lines(summary, era=era, today=today):
        page.line(line)

    page.gap()
    page.heading(HISTORY)
    for section in history.sections:
        _employer(page, section, era=era)

    # Achievements recorded against no employer close the document rather than
    # being attached to the nearest one by date (R-005).
    if history.unattached:
        page.gap()
        page.heading(UNATTACHED)
        for achievement in history.unattached:
            _achievement(page, achievement)

    page.gap()
    page.heading(SKILLS)
    for skill in history.skills:
        level = ""
        if skill.level is not None:
            level = f"（{_label(SKILL_LABELS, skill.level, 'skill level')}）"
        page.line(f"・{skill.name}{level}")

    page.gap()
    page.heading(LANGUAGES)
    for language in history.languages:
        proficiency = _label(PROFICIENCY_LABELS, language.proficiency, "proficiency")
        qualification = "" if not language.qualification else f"（{language.qualification}）"
        page.line(f"・{language.language}　{proficiency}{qualification}")

    page.gap()
    page.heading(CERTIFICATIONS)
    for certification in history.certifications:
        when = (
            ""
            if certification.issued_on is None
            else f"{format_year_month(certification.issued_on, era=era)}　"
        )
        issuer = "" if not certification.issuer else f"（{certification.issuer}）"
        page.line(f"・{when}{certification.name}{issuer}", hang="・")

    page.gap()
    page.heading(SELF_PR)
    # A claim about what kind of worker someone is, which no set of dates and
    # titles evidences. Labelled and left to the user (FR-020, R-007).
    page.finish()

    page.gap()
    page.space_for()
    canvas.setFont(FONT_NAME, BODY_SIZE)
    canvas.drawRightString(page.width - MARGIN, page.y, END)
    page.y -= LINE_HEIGHT

    canvas.save()
    return buffer.getvalue(), page.pages


def _employer(page: Page, section: EmployerSection, *, era: bool) -> None:
    """One employer: who, when, as what, and what was achieved there."""
    page.line(section.employer)

    employment = ""
    if section.employment_type is not None:
        kind = _label(EMPLOYMENT_LABELS, section.employment_type, "employment type")
        employment = f"　{EMPLOYMENT}{kind}"
    page.line(f"{PERIOD}{_period(section, era=era)}{employment}", hang=PERIOD)
    page.line(f"{ROLE}{section.job_title}", hang=ROLE)

    # An employer with no recorded description gets its period and name and no
    # invented narrative (FR-013).
    if section.description:
        page.line(section.description)

    if section.achievements:
        page.line(ACHIEVEMENTS)
        for achievement in section.achievements:
            _achievement(page, achievement)

    page.gap()


def _achievement(page: Page, achievement) -> None:
    """A career story, in the user's own words (FR-004)."""
    page.line(f"・{achievement.title}", hang="・")
    page.line(f"　{CHALLENGE}{achievement.challenge}", hang=f"　{CHALLENGE}")
    page.line(f"　{ACTION}{achievement.action}", hang=f"　{ACTION}")
    page.line(f"　{RESULT}{achievement.result}", hang=f"　{RESULT}")
