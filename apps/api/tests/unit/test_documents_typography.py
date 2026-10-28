"""The typographic base both Japanese documents share.

Feature 003 built a font, two paper sizes and a page that knows when it is
full; feature 004 needs the same ones. They live in app/documents now, and
what these guard is the thing a shared module makes possible and a copied
one does not: that there is exactly one of each.

The font tests in test_rirekisho_font.py check that Japanese survives a round
trip through a document. These check the module's own contract.
"""

import io

import pytest
from app.documents.typography import (
    FONT_NAME,
    MARGIN,
    FontUnavailable,
    Page,
    page_size,
    register_font,
    wrap,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas


def _page(paper: str = "a4") -> Page:
    return Page(Canvas(io.BytesIO(), pagesize=page_size(paper)), page_size(paper))


class TestTheFont:
    def test_it_is_registered_once_at_import(self):
        names = pdfmetrics.getRegisteredFontNames()
        assert names.count(FONT_NAME) == 1

    def test_registering_again_does_not_reload_the_file(self, monkeypatch):
        """Two features now arrive here, and the tests do as well.

        Asserted on the work skipped rather than on the result: registering
        the same font twice overwrites it with itself, so the list of names
        looks identical either way and a lost guard would go unnoticed.
        """
        loaded: list[object] = []
        monkeypatch.setattr(pdfmetrics, "registerFont", loaded.append)

        register_font()
        register_font()

        assert loaded == [], "the font file was read again though it was already registered"

    def test_a_missing_font_is_refused_loudly(self, monkeypatch):
        from pathlib import Path

        import app.documents.typography as typography

        monkeypatch.setattr(typography, "FONT_PATH", Path("/nonexistent/font.ttf"))
        monkeypatch.setattr(pdfmetrics, "getRegisteredFontNames", lambda: [])

        with pytest.raises(FontUnavailable) as raised:
            typography.register_font()
        assert "empty box" in str(raised.value)


class TestPaperSizes:
    def test_both_conventional_sizes_are_offered(self):
        a4, b5 = page_size("a4"), page_size("b5")
        assert a4[0] > b5[0] and a4[1] > b5[1]

    @pytest.mark.parametrize("name", ["A4", "b5", "B5"])
    def test_the_name_is_read_however_it_is_cased(self, name):
        assert page_size(name) == page_size(name.lower())

    @pytest.mark.parametrize("name", ["letter", "a3", "", "a4 "])
    def test_an_unknown_size_is_refused_by_name(self, name):
        """Named in the message: the caller passed it and has to find it."""
        with pytest.raises(ValueError) as raised:
            page_size(name)
        assert repr(name) in str(raised.value)


class TestWrapping:
    def test_short_text_stays_on_one_line(self):
        assert wrap("山田太郎", 400, 400, 10) == ["山田太郎"]

    def test_japanese_breaks_between_any_two_characters(self):
        lines = wrap("あ" * 60, 100, 100, 10)
        assert len(lines) > 1
        assert "".join(lines) == "あ" * 60

    def test_english_breaks_at_a_space_rather_than_mid_word(self):
        lines = wrap("Graduate School of Advanced Studies", 120, 120, 10)
        assert len(lines) > 1
        assert all(not line.endswith(" ") for line in lines)
        assert " ".join(lines) == "Graduate School of Advanced Studies"

    def test_nothing_is_ever_cut_to_fit(self):
        """FR-018a. A long name moves onto more lines; it never loses a character."""
        text = "国立研究開発法人新エネルギー・産業技術総合開発機構" * 3
        assert "".join(wrap(text, 90, 90, 10)) == text


class TestAPageKnowsWhenItIsFull:
    def test_it_starts_a_second_page_rather_than_running_off_the_first(self):
        page = _page()
        for _ in range(80):
            page.line("サンプル株式会社")
        assert page.pages > 1

    def test_a_heading_lands_on_the_same_page_as_its_first_row(self):
        """#105: a heading left at the foot of a page is a heading with no rows.

        Set to the one height that distinguishes the two behaviours: room for
        a single line, so a heading alone would fit and a heading with its
        first row would not.
        """
        page = _page()
        page.y = MARGIN + 30
        page.heading("学歴・職歴")
        page.line("サンプル株式会社")
        assert page.pages == 2, "the heading was left at the foot of page 1"
        assert page.section == "学歴・職歴"

    def test_a_heading_with_room_for_its_row_does_not_start_a_page(self):
        """The other half: it must not break out of caution."""
        page = _page()
        page.heading("学歴・職歴")
        page.line("サンプル株式会社")
        assert page.pages == 1


class TestKeepingClearOfSomething:
    def test_nothing_is_reserved_by_default(self):
        """The 職務経歴書 has nothing in its corner and must not pay for one."""
        page = _page()
        assert page._right() == page.width - MARGIN

    def test_a_reserved_box_narrows_the_lines_beside_it(self):
        page = _page()
        page.reserve_top_right(90, 120, 10)
        assert page._right() == page.width - MARGIN - 100

    def test_lines_below_it_have_the_full_width_again(self):
        page = _page()
        page.reserve_top_right(90, 120, 10)
        page.y = page.height - MARGIN - 121
        assert page._right() == page.width - MARGIN

    def test_the_next_page_has_nothing_in_the_way(self):
        """Whatever was in the corner was on that page, not this one (#106)."""
        page = _page()
        page.reserve_top_right(90, 120, 10)
        # Bounded: a page that never fills would otherwise hang the suite
        # rather than fail it, and "never fills" is a plausible fault.
        for _ in range(200):
            page.line("サンプル株式会社")
            if page.pages > 1:
                break
        assert page.pages > 1, "the page never filled"
        assert page._right() == page.width - MARGIN
