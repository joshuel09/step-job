"""Quickstart Scenario 0 — the Japanese in a 職務経歴書 is readable (FR-002).

The failure this guards against is quiet. A document with no embedded font is
produced at the right size, passes every check on bytes, and renders every
Japanese character as a hollow box — and a developer whose machine has
Japanese system fonts may never see it. The employer who prints it does.

So this extracts the text back out and asserts the font is embedded. Feature
003 has the same test; this one exists because the two documents could stop
sharing the typographic base and only one of them would notice.
"""

import io

from pypdf import PdfReader

PATH = "/api/v1/profile/documents/shokumu-keirekisho"


def _pdf(client, auth_headers) -> bytes:
    response = client.post(PATH, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return response.content


def _text(pdf: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)


def test_the_japanese_extracts_as_text(client, auth_headers, shokumu_profile):
    text = _text(_pdf(client, auth_headers))
    assert "職務経歴書" in text
    assert "株式会社サンプル" in text


def test_the_font_is_embedded(client, auth_headers, shokumu_profile):
    """`/FontFile2` is the embedded TrueType programme itself.

    Without it the glyphs are the reader's to find, and a machine without a
    Japanese font has none.
    """
    assert b"/FontFile2" in _pdf(client, auth_headers)


def test_both_documents_embed_the_same_font(client, auth_headers, shokumu_profile):
    """They draw on one typographic base (#159); this is what would notice
    if they stopped."""
    from app.documents.typography import FONT_NAME

    rirekisho = client.post("/api/v1/profile/documents/rirekisho", headers=auth_headers, json={})
    assert rirekisho.status_code == 200, rirekisho.text

    for pdf in (_pdf(client, auth_headers), rirekisho.content):
        fonts = {
            str(font.get("/BaseFont", ""))
            for page in PdfReader(io.BytesIO(pdf)).pages
            for font in (page["/Resources"]["/Font"] or {}).values()
        }
        assert any(FONT_NAME in name for name in fonts), fonts
