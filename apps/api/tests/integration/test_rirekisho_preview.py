"""Quickstart Scenario 2 — a preview is the document, and paper size is only paper.

A user must never preview one document and download another. The contract test
compares extracted text, which would miss a layout difference: a box drawn in
the wrong place or a line on the wrong page reads the same. These tests compare
what is drawn.

Two renders a moment apart differ only in their creation timestamps and the
trailer's document id, so those are removed and everything else must be equal.
"""

import io
import re

import pytest
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4, B5

PATH = "/api/v1/profile/documents/rirekisho"

# What varies between two renders of the same content, and nothing else.
_TIMESTAMP = re.compile(rb"/(?:CreationDate|ModDate) \(D:[^)]*\)")
_DOCUMENT_ID = re.compile(rb"/ID\s*\[<[0-9a-fA-F]+>\s*<[0-9a-fA-F]+>\]")

# Every entry in the fixture profile, which each paper size must carry.
ENTRIES = ("山田太郎", "サンプル大学", "株式会社サンプル", "Example Corp", "現在に至る", "以上")


def _without_render_metadata(pdf: bytes) -> bytes:
    return _DOCUMENT_ID.sub(b"", _TIMESTAMP.sub(b"", pdf))


def _pages(pdf: bytes) -> list[tuple[tuple[float, float], bytes]]:
    """Each page's size and decoded drawing instructions, in order.

    Compared alongside the bytes so a failure says which page differs rather
    than only that the files do.
    """
    return [
        ((float(p.mediabox.width), float(p.mediabox.height)), p.get_contents().get_data())
        for p in PdfReader(io.BytesIO(pdf)).pages
    ]


def _text(pdf: bytes) -> str:
    pages = PdfReader(io.BytesIO(pdf)).pages
    return re.sub(r"\s+", " ", "\n".join(p.extract_text() or "" for p in pages)).strip()


def _post(client, auth_headers, body: dict, *, preview: bool = False):
    response = client.post(
        f"{PATH}?preview=true" if preview else PATH, headers=auth_headers, json=body
    )
    assert response.status_code == 200, response.text
    return response


# A preview that ignored the request body would still match a default download,
# so parity is checked with the non-default choices as well.
CHOICES = [
    {},
    {"date_convention": "wareki"},
    {"paper_size": "b5"},
    {"date_convention": "wareki", "paper_size": "b5"},
]


@pytest.mark.parametrize("body", CHOICES, ids=lambda b: "-".join(b.values()) or "default")
class TestPreviewIsTheDownload:
    def test_every_page_draws_the_same(self, client, auth_headers, rirekisho_profile, body):
        preview = _post(client, auth_headers, body, preview=True)
        download = _post(client, auth_headers, body)

        assert _pages(preview.content) == _pages(download.content)

    def test_the_files_are_identical_apart_from_render_metadata(
        self, client, auth_headers, rirekisho_profile, body
    ):
        """Fonts, page boxes and drawing, not only the content streams."""
        preview = _post(client, auth_headers, body, preview=True)
        download = _post(client, auth_headers, body)

        assert _without_render_metadata(preview.content) == _without_render_metadata(
            download.content
        )

    def test_only_the_disposition_differs(self, client, auth_headers, rirekisho_profile, body):
        """The snapshot id is set aside: each generation records its own (FR-016)."""
        preview = _post(client, auth_headers, body, preview=True)
        download = _post(client, auth_headers, body)

        assert preview.headers["Content-Disposition"] == 'inline; filename="rirekisho.pdf"'
        assert download.headers["Content-Disposition"] == 'attachment; filename="rirekisho.pdf"'

        ignored = {"content-disposition", "x-snapshot-id"}
        assert {k: v for k, v in preview.headers.items() if k.lower() not in ignored} == {
            k: v for k, v in download.headers.items() if k.lower() not in ignored
        }


def test_the_metadata_stripping_removes_only_what_varies(client, auth_headers, rirekisho_profile):
    """Guards the guard: if stripping removed nothing, the file comparison above
    would fail on timestamps; if it removed everything, it would prove nothing."""
    pdf = _post(client, auth_headers, {}).content
    stripped = _without_render_metadata(pdf)

    assert _TIMESTAMP.search(pdf) and _DOCUMENT_ID.search(pdf)
    assert not _TIMESTAMP.search(stripped) and not _DOCUMENT_ID.search(stripped)
    assert len(pdf) - len(stripped) < 200


class TestPaperSize:
    @pytest.fixture
    def a4(self, client, auth_headers, rirekisho_profile):
        return _post(client, auth_headers, {"paper_size": "a4"}).content

    @pytest.fixture
    def b5(self, client, auth_headers, rirekisho_profile):
        return _post(client, auth_headers, {"paper_size": "b5"}).content

    def test_a4_pages_are_a4(self, a4):
        sizes = [size for size, _ in _pages(a4)]
        assert sizes and all(size == pytest.approx(A4) for size in sizes)

    def test_b5_pages_are_b5(self, b5):
        sizes = [size for size, _ in _pages(b5)]
        assert sizes and all(size == pytest.approx(B5) for size in sizes)

    @pytest.mark.parametrize("entry", ENTRIES)
    def test_every_entry_appears_at_both_sizes(self, a4, b5, entry):
        assert entry in _text(a4)
        assert entry in _text(b5)

    def test_the_content_is_the_same_at_both_sizes(self, a4, b5):
        """Presentation differs; content does not."""
        assert _text(a4) == _text(b5)
