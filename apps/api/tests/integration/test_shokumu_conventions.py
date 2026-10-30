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
from app.documents.typography import CONTINUED
from pypdf import PdfReader

PATH = "/api/v1/profile/documents/shokumu-keirekisho"

ERAS = ("令和", "平成", "昭和", "大正", "明治")

# CONTINUED marks a section carried over to another page, which B5 may need
# where A4 does not. It is the page's own word, not content.


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

    def test_both_sizes_carry_the_same_content(self, papers):
        """Compared on characters, not on lines: a narrower page wraps
        differently, and wrapping changes where a line breaks rather than what
        the document says."""
        a4, b5 = (_squashed(pdf).replace(CONTINUED, "") for pdf in papers.values())
        assert a4 == b5

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
