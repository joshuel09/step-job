"""Quickstart Scenario 3 — one convention throughout, at either size.

FR-009 says the two calendars never appear together in one document. The
sharp version of that is not "the date column uses the chosen calendar" but
"no four-digit Western year appears anywhere" — a 和暦 document that says
令和3年 in the table and 2021年 in the summary has mixed them, and the place
it slipped through is always the line nobody thought of.

FR-010 says both paper sizes carry the same content. A smaller page means
more pages, never fewer entries.
"""

import io
import re

import pytest
from pypdf import PdfReader

PATH = "/api/v1/profile/documents/shokumu-keirekisho"

ERAS = ("令和", "平成", "昭和", "大正", "明治")

# Marks a section carried over to another page, which B5 may need where A4
# does not. It is the page's own word rather than content, so it is subtracted
# before the two sizes are compared — written out here rather than imported,
# because the renderer's own constant cannot be the oracle for a test about
# what the renderer draws.
CONTINUED = "（続き）"

# The paper itself, in points: ISO A4 is 210x297mm and B5 is 176x250mm. A
# standard, not a product choice, so the numbers belong to the test.
PAPERS = {"a4": (595.28, 841.89), "b5": (498.90, 708.66)}


def _generate(client, auth_headers, **body) -> bytes:
    response = client.post(PATH, headers=auth_headers, json=body)
    assert response.status_code == 200, response.text
    return response.content


def _text(pdf: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)


def _squashed(pdf: bytes) -> str:
    return re.sub(r"[\s　]+", "", _text(pdf))


@pytest.fixture
def wareki(client, auth_headers, shokumu_profile) -> str:
    return _squashed(_generate(client, auth_headers, date_convention="wareki"))


@pytest.fixture
def seireki(client, auth_headers, shokumu_profile) -> str:
    return _squashed(_generate(client, auth_headers, date_convention="seireki"))


class TestOneCalendarThroughout:
    def test_a_wareki_document_has_no_western_year_anywhere(self, wareki):
        """Not only in the date column — anywhere."""
        assert re.findall(r"(?<!\d)\d{4}(?!\d)", wareki) == []

    def test_a_wareki_document_does_use_eras(self, wareki):
        """Otherwise the test above passes on a document with no dates at all."""
        assert any(era in wareki for era in ERAS)

    def test_a_seireki_document_names_no_era(self, seireki):
        assert [era for era in ERAS if era in seireki] == []

    def test_a_seireki_document_does_use_western_years(self, seireki):
        assert "2013年4月" in seireki
        assert "2021年3月" in seireki

    def test_the_summary_follows_the_same_calendar_as_the_sections(self, wareki):
        """The line most likely to be left behind: it is assembled rather than
        drawn from an entry, so it has its own call to the date formatter."""
        summary = wareki[wareki.index("職務経験年数") : wareki.index("在籍企業数")]
        assert any(era in summary for era in ERAS), summary
        assert re.findall(r"\d{4}", summary) == []

    def test_the_date_the_document_was_made_follows_it_too(self, wareki):
        made = wareki[wareki.index("作成日") : wareki.index("職務要約")]
        assert any(era in made for era in ERAS), made


class TestEitherPaperSize:
    @pytest.fixture
    def papers(self, client, auth_headers, shokumu_profile):
        return {paper: _generate(client, auth_headers, paper_size=paper) for paper in ("a4", "b5")}

    def test_each_size_is_actually_the_size_that_was_asked_for(self, papers):
        """Everything else in this class compares the two documents to each
        other, and would pass on two A4 documents. This is what says the
        paper size reached the page at all."""
        for paper, pdf in papers.items():
            wanted = PAPERS[paper]
            for page in PdfReader(io.BytesIO(pdf)).pages:
                got = (float(page.mediabox.width), float(page.mediabox.height))
                assert got == pytest.approx(wanted, abs=0.5), f"{paper} came out {got}"

    def test_both_sizes_carry_the_same_content(self, papers):
        """Compared on characters, not on lines: a narrower page wraps
        differently, and wrapping changes where a line breaks rather than what
        the document says."""
        a4, b5 = (_squashed(pdf).replace(CONTINUED, "") for pdf in papers.values())
        assert a4 == b5

    def test_and_the_spaces_inside_a_value_survive_both(self, papers):
        """Squashing the whitespace is what makes the comparison above
        wrap-tolerant, and it would also hide an employer's name losing the
        space the user typed. So the spaces are asserted separately.

        On the lines themselves, not on the document: 職務要約 names the most
        recent employer too, so a search over the whole text would find the
        summary's spelling and pass while the section heading had lost its
        space.
        """
        for paper, pdf in papers.items():
            lines = [line.strip() for line in _text(pdf).splitlines() if line.strip()]

            assert "Example Corp" in lines, (
                f"{paper}: the employer's own heading is not spelled as recorded"
            )
            assert any(line == "職種　Software Engineer" for line in lines), (
                f"{paper}: the job title is not spelled as recorded"
            )

    def test_a_smaller_page_produces_pages_rather_than_losing_entries(
        self, client, auth_headers, shokumu_profile
    ):
        sizes = {}
        for paper in ("a4", "b5"):
            response = client.post(PATH, headers=auth_headers, json={"paper_size": paper})
            sizes[paper] = int(response.headers["X-Document-Pages"])

        assert sizes["b5"] >= sizes["a4"], "a smaller page cannot need fewer pages"

    def test_an_unknown_paper_size_is_refused(self, client, auth_headers, shokumu_profile):
        response = client.post(PATH, headers=auth_headers, json={"paper_size": "letter"})
        assert response.status_code == 422


class TestTheTwoChoicesAreIndependent:
    @pytest.mark.parametrize("paper", ["a4", "b5"])
    @pytest.mark.parametrize("convention", ["seireki", "wareki"])
    def test_every_combination_produces_a_document(
        self, client, auth_headers, shokumu_profile, paper, convention
    ):
        document = _squashed(
            _generate(client, auth_headers, paper_size=paper, date_convention=convention)
        )
        assert "株式会社サンプル" in document
        if convention == "wareki":
            assert re.findall(r"(?<!\d)\d{4}(?!\d)", document) == []
