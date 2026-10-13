"""Quickstart Scenario 6 — a long history keeps every entry.

FR-018a: where a career does not fit the conventional two pages, the document
runs longer. It never drops, shortens or summarises an entry to fit; losing
someone's career to a layout constraint is worse than a third page.

Two ways an entry can be lost without leaving the file. It can be missing, or
it can be drawn past the edge of the paper, where text extraction still finds
it and a printer does not. So these tests count entries in and out, and also
check that every line lies within the page.
"""

import io
import re
from datetime import date

import pytest
from pypdf import PdfReader
from reportlab.pdfbase.pdfmetrics import stringWidth

PATH = "/api/v1/profile/documents/rirekisho"

ROLES = 45
SCHOOLS = 4

# Long enough that no paper size has room for it on one line.
LONG_EMPLOYER = (
    "国立研究開発法人新エネルギー・産業技術総合開発機構ロボット・ＡＩ部先端技術研究センター"
)
LONG_SCHOOL = (
    "The Graduate School of Advanced Interdisciplinary Studies in Engineering and Public Policy"
)
LONG_ADDRESS = (
    "東京都千代田区丸の内一丁目九番二号グラントウキョウサウスタワー四十一階サンプル株式会社気付"
)


def _employer(i: int) -> str:
    return f"株式会社ロングヒストリー{i:02d}"


@pytest.fixture
def long_profile(session, user_id):
    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)
    session.add(
        models.Identity(
            profile_id=profile.id,
            full_name_latin="Taro Yamada",
            full_name_japanese="山田太郎",
            address=LONG_ADDRESS,
        )
    )
    for i in range(SCHOOLS):
        session.add(
            models.Education(
                profile_id=profile.id,
                institution=LONG_SCHOOL if i == 0 else f"サンプル学院{i}",
                started_on=date(1980 + i * 2, 4, 1),
                ended_on=date(1982 + i * 2, 3, 31),
            )
        )
    for i in range(ROLES):
        session.add(
            models.WorkExperience(
                profile_id=profile.id,
                employer_name=LONG_EMPLOYER if i == ROLES - 1 else _employer(i),
                employer_name_normalised=f"long{i}",
                job_title="エンジニア",
                started_on=date(1990 + i // 2, 1 + (i % 2) * 6, 1),
                # The last role is ongoing, so the table ends with 現在に至る.
                ended_on=None if i == ROLES - 1 else date(1990 + i // 2, 5 + (i % 2) * 6, 30),
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


def _page_lines(pdf: bytes) -> list[list[str]]:
    return [
        [line.strip() for line in (p.extract_text() or "").splitlines() if line.strip()]
        for p in PdfReader(io.BytesIO(pdf)).pages
    ]


def _overflowing(pdf: bytes) -> list[str]:
    """Every drawn string whose right edge passes the page's right margin."""
    from app.rirekisho.render import FONT_NAME, MARGIN

    found: list[str] = []
    for page in PdfReader(io.BytesIO(pdf)).pages:
        limit = float(page.mediabox.width) - MARGIN + 0.5

        def visit(text, cm, tm, font, size, limit=limit):
            text = text.rstrip("\n")
            if text.strip() and tm[4] + stringWidth(text, FONT_NAME, size) > limit:
                found.append(text)

        page.extract_text(visitor_text=visit)
    return found


PAPERS = pytest.mark.parametrize("paper", ["a4", "b5"])


@PAPERS
class TestNothingIsLost:
    def test_it_runs_past_two_pages_and_says_so(self, client, auth_headers, long_profile, paper):
        response = _generate(client, auth_headers, paper)
        pages = len(PdfReader(io.BytesIO(response.content)).pages)

        assert pages > 2
        assert int(response.headers["X-Document-Pages"]) == pages

    def test_every_role_has_its_joining_row(self, client, auth_headers, long_profile, paper):
        """Scenario 6's own check: 入社 rows in equal roles in."""
        text = _squashed(_generate(client, auth_headers, paper).content)
        assert text.count("入社") == ROLES
        assert text.count("退社") == ROLES - 1
        assert text.count("現在に至る") == 1

    def test_every_school_has_both_rows(self, client, auth_headers, long_profile, paper):
        text = _squashed(_generate(client, auth_headers, paper).content)
        assert text.count("入学") == SCHOOLS
        assert text.count("卒業") == SCHOOLS

    def test_every_name_appears_whole(self, client, auth_headers, long_profile, paper):
        """Not truncated, not abbreviated — including the ones that wrap."""
        text = _squashed(_generate(client, auth_headers, paper).content)
        names = [_employer(i) for i in range(ROLES - 1)] + [LONG_EMPLOYER, LONG_SCHOOL]
        missing = [n for n in names if re.sub(r"\s+", "", n) not in text]
        assert missing == []

    def test_a_long_address_appears_whole(self, client, auth_headers, long_profile, paper):
        assert LONG_ADDRESS in _squashed(_generate(client, auth_headers, paper).content)

    def test_roles_keep_their_order_across_the_breaks(
        self, client, auth_headers, long_profile, paper
    ):
        text = _squashed(_generate(client, auth_headers, paper).content)
        positions = [text.index(_employer(i)) for i in range(ROLES - 1)]
        assert positions == sorted(positions)

    def test_nothing_is_drawn_off_the_page(self, client, auth_headers, long_profile, paper):
        """A line past the edge survives text extraction and is lost in print."""
        assert _overflowing(_generate(client, auth_headers, paper).content) == []


@PAPERS
class TestLaterPagesReadOnTheirOwn:
    def test_a_page_starting_mid_table_says_which_table(
        self, client, auth_headers, long_profile, paper
    ):
        pages = _page_lines(_generate(client, auth_headers, paper).content)
        headings = ("学歴・職歴", "免許・資格", "本人希望記入欄", "志望の動機")

        for number, lines in enumerate(pages[1:], start=2):
            assert lines[0].startswith(headings), f"page {number} opens with {lines[0]!r}"

    def test_the_history_continues_under_a_continued_heading(
        self, client, auth_headers, long_profile, paper
    ):
        pages = _page_lines(_generate(client, auth_headers, paper).content)
        assert pages[1][0] == "学歴・職歴（続き）"

    def test_no_page_ends_on_a_bare_heading(self, client, auth_headers, long_profile, paper):
        """A heading at the foot of a page, with its rows overleaf, reads as empty."""
        pages = _page_lines(_generate(client, auth_headers, paper).content)
        for lines in pages[:-1]:
            assert lines[-1] not in ("学歴・職歴", "免許・資格", "本人希望記入欄")


def test_the_guard_sees_a_line_off_the_page():
    """Guards the guard: a string drawn past the margin is reported."""
    from io import BytesIO

    from app.rirekisho.render import FONT_NAME, register_font
    from reportlab.lib.pagesizes import B5
    from reportlab.pdfgen.canvas import Canvas

    register_font()
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=B5)
    canvas.setFont(FONT_NAME, 10)
    canvas.drawString(40, 400, LONG_EMPLOYER * 2)
    canvas.save()

    assert _overflowing(buffer.getvalue()) != []
