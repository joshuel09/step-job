"""A preview and a download are the same document.

The promise in the contract is that only the disposition differs. A user who
previews one thing and downloads another has been shown something they did
not send, which is worse than no preview at all.

Feature 003's contract test compares the two as extracted text. That would
pass on two documents whose words match and whose layout does not — a line
drawn in a different place, a frame missing, a section at a different size.
So this compares the drawing itself: the content stream of each page, which
is the sequence of operators the reader executes.
"""

import io

import pytest
from pypdf import PdfReader

PATH = "/api/v1/profile/documents/shokumu-keirekisho"


def _drawn(pdf: bytes) -> list[bytes]:
    """What each page actually draws.

    The creation timestamp and the document id differ between two renders a
    moment apart, so comparing whole files proves nothing. They live in the
    trailer, not in the page content, which is why this compares the latter.
    """
    return [page.get_contents().get_data() for page in PdfReader(io.BytesIO(pdf)).pages]


@pytest.fixture
def both(client, auth_headers, shokumu_profile):
    preview = client.post(f"{PATH}?preview=true", headers=auth_headers, json={})
    download = client.post(PATH, headers=auth_headers, json={})
    assert preview.status_code == download.status_code == 200
    return preview, download


class TestTheSameDocument:
    def test_every_page_draws_the_same_thing(self, both):
        preview, download = both
        assert _drawn(preview.content) == _drawn(download.content)

    def test_the_comparison_can_tell_two_documents_apart(
        self, client, auth_headers, shokumu_profile
    ):
        """Otherwise the test above passes on a comparison of nothing."""
        a4 = client.post(PATH, headers=auth_headers, json={"paper_size": "a4"})
        b5 = client.post(PATH, headers=auth_headers, json={"paper_size": "b5"})
        assert _drawn(a4.content) != _drawn(b5.content)

    def test_they_run_to_the_same_length(self, both):
        preview, download = both
        assert preview.headers["X-Document-Pages"] == download.headers["X-Document-Pages"]


class TestOnlyTheDispositionDiffers:
    def test_a_download_is_an_attachment(self, both):
        _, download = both
        assert download.headers["Content-Disposition"].startswith("attachment")

    def test_a_preview_is_shown_in_place(self, both):
        preview, _ = both
        assert preview.headers["Content-Disposition"].startswith("inline")

    def test_both_are_offered_under_the_same_name(self, both):
        preview, download = both
        assert 'filename="shokumu-keirekisho.pdf"' in preview.headers["Content-Disposition"]
        assert 'filename="shokumu-keirekisho.pdf"' in download.headers["Content-Disposition"]


class TestAPreviewIsStillARecord:
    def test_previewing_records_a_snapshot_like_any_other_generation(self, both):
        """It is the same document, so what it was based on is recorded the
        same way. A user who previews and sends a screenshot has sent it."""
        preview, _ = both
        assert preview.headers["X-Snapshot-Id"]

    def test_the_two_are_separate_generations(self, both):
        preview, download = both
        assert preview.headers["X-Snapshot-Id"] != download.headers["X-Snapshot-Id"]
