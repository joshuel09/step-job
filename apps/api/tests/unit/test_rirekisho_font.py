"""The Japanese font.

This is the quiet failure in feature 003. Without an embedded typeface every
character renders as a hollow box: the document is produced, correctly sized,
and unreadable — and a developer whose machine has Japanese system fonts may
never reproduce it.

So these assert on text extracted back out of a document, not on bytes or on a
file existing. Both of those pass for a page of boxes.
"""

import io

import pytest
from app.rirekisho.render import FONT_NAME, FONT_PATH, FontUnavailable, page_size, register_font
from pypdf import PdfReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

JAPANESE = ["履歴書", "学歴・職歴", "現在に至る", "以上", "株式会社サンプル", "令和3年4月"]


def _draw(lines: list[str]) -> bytes:
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer)
    page.setFont(FONT_NAME, 14)
    for index, line in enumerate(lines):
        page.drawString(60, 760 - index * 24, line)
    page.save()
    return buffer.getvalue()


def test_the_font_file_ships_with_the_application():
    """Not fetched at build time, and not taken from the host."""
    assert FONT_PATH.is_file(), f"the Japanese font is missing from {FONT_PATH}"


def test_the_font_is_registered_at_import():
    assert FONT_NAME in pdfmetrics.getRegisteredFontNames()


def test_registering_twice_is_harmless():
    register_font()
    register_font()
    assert FONT_NAME in pdfmetrics.getRegisteredFontNames()


@pytest.mark.parametrize("text", JAPANESE)
def test_japanese_survives_a_round_trip_through_a_document(text):
    """The check a page of hollow boxes would fail."""
    reader = PdfReader(io.BytesIO(_draw([text])))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert text in extracted


def test_the_glyphs_are_embedded_rather_than_referenced():
    """A document is printed by an employer, not only read by its author.

    A font referenced rather than embedded renders only where the reader
    supplies it, which is a worse failure than a larger file.
    """
    assert b"/FontFile2" in _draw(JAPANESE)


def test_both_page_sizes_are_available():
    a4, b5 = page_size("a4"), page_size("b5")
    assert a4 != b5
    assert a4[0] > b5[0] and a4[1] > b5[1]


def test_an_unknown_paper_size_is_refused():
    with pytest.raises(ValueError):
        page_size("letter")


def test_a_missing_font_would_be_refused_loudly(monkeypatch):
    """The failure that must not be silent."""
    from pathlib import Path

    import app.rirekisho.render as render

    monkeypatch.setattr(render, "FONT_PATH", Path("/nonexistent/font.ttf"))
    monkeypatch.setattr(pdfmetrics, "getRegisteredFontNames", lambda: [])

    with pytest.raises(FontUnavailable) as raised:
        render.register_font()
    assert "empty box" in str(raised.value)
