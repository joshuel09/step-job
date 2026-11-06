"""Quickstart Scenario 0 — the Japanese in an English resume is readable.

The surprising requirement of this document. It is written in English, and
it still embeds the CJK font, because R-002 means an employer with no
supplied English name appears exactly as the user recorded it. 株式会社サンプル
rendered as four hollow boxes would have failed in the one place the
applicant most needs the page to be legible: the name of the company they
worked for.

The failure is quiet. A document with no embedded font comes out the right
size, passes every check on bytes, and renders every Japanese character as
an empty box — and a developer whose machine has Japanese system fonts may
never see it. The employer who prints it does.
"""

import io

from pypdf import PdfReader

PATH = "/api/v1/profile/documents/resume"


def _pdf(client, auth_headers) -> bytes:
    response = client.post(PATH, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return response.content


def _text(pdf: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)


def test_an_untranslated_employer_extracts_as_the_japanese_it_was_recorded_as(
    client, auth_headers, resume_profile
):
    """Not transliterated, not romanised, not left out (FR-021)."""
    assert "株式会社サンプル" in _text(_pdf(client, auth_headers))


def test_the_font_is_embedded(client, auth_headers, resume_profile):
    """`/FontFile2` is the embedded TrueType programme itself.

    Without it the glyphs are the reader's to find, and a machine without a
    Japanese font has none.
    """
    assert b"/FontFile2" in _pdf(client, auth_headers)


def test_the_resume_uses_the_shared_typographic_base(client, auth_headers, resume_profile):
    """The same embedded font as the two Japanese documents (#159).

    Named for the resume rather than for all three. The 履歴書 and the
    職務経歴書 need a profile this fixture does not build, and
    `test_shokumu_font.py` already holds those two to each other — a test
    here that iterated a one-item tuple would say "all three" and check
    one, which is worse than checking one and saying so.

    This is what would notice if the English document stopped sharing the
    base, which is exactly the change someone would make on the reasoning
    that an English resume does not need a Japanese font.
    """
    from app.documents.typography import FONT_NAME

    fonts = {
        str(font.get("/BaseFont", ""))
        for page in PdfReader(io.BytesIO(_pdf(client, auth_headers))).pages
        for font in (page["/Resources"]["/Font"] or {}).values()
    }
    assert any(FONT_NAME in name for name in fonts), fonts
