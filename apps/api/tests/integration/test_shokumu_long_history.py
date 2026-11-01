"""Quickstart Scenario 9 — a long career keeps every entry.

FR-011: where a career does not fit the conventional length, the document
runs longer. It never drops, shortens or summarises an entry to fit. Only
the user can judge which roles matter, and losing one to a layout constraint
is worse than another page.

Two ways an entry can be lost without leaving the file. It can be missing,
or it can be drawn past the edge of the paper, where text extraction still
finds it and a printer does not. So these count entries in and out, and
check that every line lies within the page.
"""

import io
import re
from datetime import date

import pytest
from pypdf import PdfReader
from reportlab.pdfbase.pdfmetrics import stringWidth

PATH = "/api/v1/profile/documents/shokumu-keirekisho"

EMPLOYERS = 12
STORIES_PER_EMPLOYER = 2

# Long enough that no paper size has room for it on one line.
LONG_EMPLOYER = (
    "国立研究開発法人新エネルギー・産業技術総合開発機構ロボット・ＡＩ部先端技術研究センター"
)
LONG_DESCRIPTION = (
    "社内の基幹システムの設計、開発、運用、保守および関連する社内外の調整業務を担当し、"
    "あわせて新規参画メンバーの受け入れと技術的な助言を行いました。"
)


def _employer(i: int) -> str:
    return f"株式会社ロングキャリア{i:02d}"


def _title(employer: int, story: int) -> str:
    return f"実績{employer:02d}-{story}"


@pytest.fixture
def long_career(session, user_id):
    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)
    session.add(
        models.Identity(
            profile_id=profile.id, full_name_latin="Taro Yamada", full_name_japanese="山田太郎"
        )
    )

    for i in range(EMPLOYERS):
        experience = models.WorkExperience(
            profile_id=profile.id,
            employer_name=LONG_EMPLOYER if i == EMPLOYERS - 1 else _employer(i),
            employer_name_normalised=f"long{i}",
            job_title="エンジニア",
            started_on=date(2000 + i, 4, 1),
            # The last role is ongoing, so the document ends at 現在.
            ended_on=None if i == EMPLOYERS - 1 else date(2000 + i, 12, 31),
            description=LONG_DESCRIPTION if i == 0 else "担当業務を行いました。",
        )
        session.add(experience)
        session.flush()

        for s in range(STORIES_PER_EMPLOYER):
            session.add(
                models.CareerStory(
                    profile_id=profile.id,
                    work_experience_id=experience.id,
                    title=_title(i, s),
                    challenge="課題があった。",
                    action="対応した。",
                    result="解決した。",
                )
            )
    session.flush()
    return profile


def _generate(client, auth_headers, paper: str):
    response = client.post(PATH, headers=auth_headers, json={"paper_size": paper})
    assert response.status_code == 200, response.text
    return response


def _squashed(pdf: bytes) -> str:
    """All the text with every space and line break removed.

    A wrapped name continues on the next line; comparing without whitespace
    finds it whole wherever the line broke.
    """
    text = "".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
    return re.sub(r"[\s　]+", "", text)


def _content(pdf: bytes) -> str:
    """Everything the document says, with pagination taken out.

    The continuation headings go whole, because they belong to where the
    pages fell rather than to what was recorded. What is left is compared
    without whitespace, since a narrower page wraps the same sentence in a
    different place.
    """
    from app.documents.typography import CONTINUED

    lines = [
        line.strip()
        for page in PdfReader(io.BytesIO(pdf)).pages
        for line in (page.extract_text() or "").splitlines()
        if line.strip() and not line.strip().endswith(CONTINUED)
    ]
    return re.sub(r"[\s　]+", "", "".join(lines))


def _overflowing(pdf: bytes) -> list[str]:
    """Every drawn string whose right edge passes the page's right margin."""
    from app.documents.typography import FONT_NAME, MARGIN

    found: list[str] = []
    for page in PdfReader(io.BytesIO(pdf)).pages:
        limit = float(page.mediabox.width) - MARGIN + 0.5

        def visit(text, cm, tm, font, size, limit=limit):
            text = text.rstrip("\n")
            if text.strip() and tm[4] + stringWidth(text, FONT_NAME, size) > limit:
                found.append(text)

        page.extract_text(visitor_text=visit)
    return found


def _below_the_margin(pdf: bytes) -> list[str]:
    """Every drawn string whose baseline falls below the bottom margin."""
    from app.documents.typography import MARGIN

    found: list[str] = []
    for page in PdfReader(io.BytesIO(pdf)).pages:

        def visit(text, cm, tm, font, size):
            if text.strip() and tm[5] < MARGIN - 0.5:
                found.append(text.rstrip("\n"))

        page.extract_text(visitor_text=visit)
    return found


PAPERS = pytest.mark.parametrize("paper", ["a4", "b5"])


@PAPERS
class TestNothingIsLost:
    def test_it_runs_to_more_than_one_page_and_says_so(
        self, client, auth_headers, long_career, paper
    ):
        response = _generate(client, auth_headers, paper)
        pages = len(PdfReader(io.BytesIO(response.content)).pages)

        assert pages > 1
        assert int(response.headers["X-Document-Pages"]) == pages

    def test_every_employer_appears(self, client, auth_headers, long_career, paper):
        text = _squashed(_generate(client, auth_headers, paper).content)
        names = [_employer(i) for i in range(EMPLOYERS - 1)] + [LONG_EMPLOYER]
        assert [n for n in names if n not in text] == []

    def test_every_achievement_appears(self, client, auth_headers, long_career, paper):
        """Counted, not sampled: twelve employers times two is twenty-four."""
        text = _squashed(_generate(client, auth_headers, paper).content)
        titles = [_title(i, s) for i in range(EMPLOYERS) for s in range(STORIES_PER_EMPLOYER)]
        assert len(titles) == EMPLOYERS * STORIES_PER_EMPLOYER
        assert [t for t in titles if t not in text] == []

    def test_the_long_description_survives_whole(self, client, auth_headers, long_career, paper):
        text = _squashed(_generate(client, auth_headers, paper).content)
        assert re.sub(r"[\s　]+", "", LONG_DESCRIPTION) in text

    def test_the_employers_keep_their_order_across_the_breaks(
        self, client, auth_headers, long_career, paper
    ):
        """Newest first by default, and a page break does not reshuffle them."""
        text = _squashed(_generate(client, auth_headers, paper).content)
        positions = [text.index(_employer(i)) for i in range(EMPLOYERS - 1)]
        assert positions == sorted(positions, reverse=True)

    def test_the_document_still_ends_where_it_should(
        self, client, auth_headers, long_career, paper
    ):
        text = _squashed(_generate(client, auth_headers, paper).content)
        assert text.endswith("自己PR以上")


@PAPERS
class TestNothingRunsOffThePaper:
    def test_no_line_passes_the_right_margin(self, client, auth_headers, long_career, paper):
        """The other way to lose an entry: still in the file, off the page."""
        assert _overflowing(_generate(client, auth_headers, paper).content) == []

    def test_no_line_falls_below_the_bottom_margin(self, client, auth_headers, long_career, paper):
        assert _below_the_margin(_generate(client, auth_headers, paper).content) == []

    def test_the_overflow_check_can_see_an_overflow(self, client, auth_headers, long_career, paper):
        """Otherwise the two tests above pass on a check of nothing."""
        from app.documents.typography import MARGIN

        pdf = _generate(client, auth_headers, paper).content
        page = PdfReader(io.BytesIO(pdf)).pages[0]
        limit = float(page.mediabox.width) - MARGIN

        widest = 0.0

        def visit(text, cm, tm, font, size):
            nonlocal widest
            if text.strip():
                widest = max(widest, tm[4] + stringWidth(text.rstrip("\n"), "IPAexGothic", size))

        page.extract_text(visitor_text=visit)
        assert 0 < widest <= limit + 0.5, "nothing was measured"


@PAPERS
class TestASmallerPageMeansMorePages:
    def test_b5_needs_at_least_as_many_pages_as_a4(self, client, auth_headers, long_career, paper):
        a4 = int(_generate(client, auth_headers, "a4").headers["X-Document-Pages"])
        b5 = int(_generate(client, auth_headers, "b5").headers["X-Document-Pages"])
        assert b5 >= a4

    def test_and_carries_the_same_entries(self, client, auth_headers, long_career, paper):
        """Compared with the continuation headings dropped whole.

        Removing only the （続き） marker leaves the heading behind it, and a
        heading repeated on one size and not the other is a difference in
        where the pages fell, not in what the document says.
        """
        a4 = _content(_generate(client, auth_headers, "a4").content)
        b5 = _content(_generate(client, auth_headers, "b5").content)
        assert a4 == b5
