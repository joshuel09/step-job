"""Drawing the English resume.

The only module here that knows a PDF exists. It is given the frozen
dataclasses from `sections.py` and nothing else — no session, no profile, no
`JapanProfile` — so FR-009 and FR-010 hold because there is nothing to leak
rather than because a filter caught something on the way past.

The font, the paper sizes and the page-flow class come from `app/documents`,
shared with the two Japanese documents. The dates come from
`app/documents/dates.py`, which cannot reach the era table (R-006).

Every word on the page is either a value the user recorded, an English
version they approved, or this module's own fixed vocabulary below. Nothing
is translated, rephrased or inferred here, and no provider is reachable from
this package at all (R-005).
"""

from io import BytesIO

from reportlab.pdfgen.canvas import Canvas

from app.documents.dates import format_month, format_period
from app.documents.typography import (
    HEADING_SIZE,
    TITLE_SIZE,
    Page,
    page_size,
    register_font,
)
from app.resume.sections import ResumeContent

# The document's own headings. Unlike the 履歴書, a section with nothing under
# it is absent rather than labelled: a 履歴書's blank 賞罰 is a statement, and
# an empty Certifications heading on a resume says the applicant tried to
# think of one and failed (FR-011).
EXPERIENCE = "Experience"
EDUCATION = "Education"
SKILLS = "Skills"
CERTIFICATIONS = "Certifications"

# What a section carried over a page break is marked with. The shared default
# is （続き）, which belongs to a 履歴書.
CONTINUED = " (continued)"

#: Separates a title from its employer, and a qualification from its field.
#: An en dash with spaces, as English typography takes it.
JOIN = " – "


def render_resume(content: ResumeContent, *, paper: str = "letter") -> tuple[bytes, int]:
    """Lay out the resume. Returns the file and how many pages it ran to.

    The page count is returned rather than capped. A long career produces
    more pages; shortening is the user's choice through `include_skills`,
    never this function's (FR-007).
    """
    register_font()
    buffer = BytesIO()
    size = page_size(paper)
    canvas = Canvas(buffer, pagesize=size)
    page = Page(canvas, size, continued=CONTINUED)

    _contact(page, content)
    _experience(page, content)
    _education(page, content)
    _skills(page, content)
    _certifications(page, content)

    page.finish()
    canvas.save()
    return buffer.getvalue(), page.pages


def _contact(page: Page, content: ResumeContent) -> None:
    """The name, and the two ways to reach the person.

    No address, no date of birth, no photograph: the dataclass has nowhere
    to carry them, so this is not a decision taken here so much as the only
    thing available (FR-009).
    """
    page.line(content.contact.full_name, size=TITLE_SIZE)

    reachable = [part for part in (content.contact.email, content.contact.phone) if part]
    if reachable:
        page.line("  |  ".join(reachable))
    page.gap()


def _experience(page: Page, content: ResumeContent) -> None:
    if not content.experiences:
        return

    page.heading(EXPERIENCE)
    for entry in content.experiences:
        page.line(f"{entry.job_title}{JOIN}{entry.employer}", size=HEADING_SIZE)

        period = format_period(entry.started_on, entry.ended_on)
        if period:
            page.line(period)
        if entry.description:
            page.line(entry.description)
        page.gap(0.4)


def _education(page: Page, content: ResumeContent) -> None:
    if not content.education:
        return

    page.heading(EDUCATION)
    for entry in content.education:
        page.line(entry.institution, size=HEADING_SIZE)

        study = JOIN.join(part for part in (entry.qualification, entry.field_of_study) if part)
        if study:
            page.line(study)
        period = format_period(entry.started_on, entry.ended_on)
        if period:
            page.line(period)
        page.gap(0.4)


def _skills(page: Page, content: ResumeContent) -> None:
    """One line, comma-separated.

    A resume lists skills; it does not table them. The level is shown in
    brackets where the user recorded one, and omitted where they did not —
    an absent level is not "beginner".
    """
    if not content.skills:
        return

    page.heading(SKILLS)
    page.line(
        ", ".join(
            f"{entry.name} ({entry.level})" if entry.level else entry.name
            for entry in content.skills
        )
    )
    page.gap()


def _certifications(page: Page, content: ResumeContent) -> None:
    if not content.certifications:
        return

    page.heading(CERTIFICATIONS)
    for entry in content.certifications:
        parts = [entry.name]
        if entry.issuer:
            parts.append(entry.issuer)
        line = JOIN.join(parts)

        if entry.issued_on:
            line = f"{line}{JOIN}{format_month(entry.issued_on)}"
        page.line(line)
    page.gap()
