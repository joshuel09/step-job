"""Reading text out of documents.

The threshold test matters most. A scanned page is not empty — it yields a few
stray characters — so a zero check would call it readable and hand the model
noise. The user would then be told their resume contained no career
information, which is both wrong and unactionable.
"""

from pathlib import Path

import pytest
from app.imports.documents import (
    DocumentError,
    DocumentProblem,
    detect_kind,
    extract_text,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class TestDetectKind:
    def test_a_pdf_is_recognised_from_its_bytes(self):
        assert detect_kind(_read("example-resume.pdf"), None, None) == "pdf"

    def test_a_docx_is_recognised_from_its_bytes(self):
        assert detect_kind(_read("example-resume.docx"), None, None) == "docx"

    def test_the_bytes_win_over_a_misleading_name(self):
        # A filename can say anything; the leading bytes cannot.
        assert detect_kind(_read("example-resume.pdf"), "resume.docx", None) == "pdf"

    def test_an_unrecognised_file_is_rejected(self):
        with pytest.raises(DocumentError) as raised:
            detect_kind(b"just some plain text, not a document", "notes.txt", "text/plain")
        assert raised.value.problem is DocumentProblem.unsupported


class TestExtractText:
    def test_a_pdf_yields_its_text(self):
        text = extract_text(_read("example-resume.pdf"))
        assert "Example Corp" in text
        assert "Software Engineer" in text

    def test_a_docx_yields_its_text(self):
        text = extract_text(_read("example-resume.docx"))
        assert "Example Corp" in text
        assert "Sample Industries" in text

    def test_a_pdf_and_a_docx_of_the_same_resume_agree(self):
        pdf = extract_text(_read("example-resume.pdf"))
        docx = extract_text(_read("example-resume.docx"))

        for expected in ("Example Corp", "Sample Industries", "PostgreSQL"):
            assert expected in pdf and expected in docx

    def test_a_japanese_document_keeps_its_text(self):
        text = extract_text(_read("example-resume-ja.docx"))
        assert "職務経歴書" in text
        assert "令和3年4月" in text

    def test_a_scan_with_no_text_layer_is_unreadable(self):
        """Not 'empty' and not a service problem: the document cannot be read."""
        with pytest.raises(DocumentError) as raised:
            extract_text(_read("scanned-no-text.pdf"))

        assert raised.value.problem is DocumentProblem.unreadable
        assert "scan" in raised.value.message.lower()

    def test_an_empty_file_is_unreadable(self):
        with pytest.raises(DocumentError) as raised:
            extract_text(b"")
        assert raised.value.problem is DocumentProblem.unreadable

    def test_a_damaged_pdf_is_unreadable_rather_than_crashing(self):
        with pytest.raises(DocumentError) as raised:
            extract_text(b"%PDF-1.4\nthis is not actually a pdf")
        assert raised.value.problem is DocumentProblem.unreadable

    def test_a_damaged_docx_is_unreadable_rather_than_crashing(self):
        with pytest.raises(DocumentError) as raised:
            extract_text(b"PK\x03\x04 not really a zip")
        assert raised.value.problem is DocumentProblem.unreadable

    def test_an_oversized_document_is_refused(self):
        from app.imports.documents import MAXIMUM_BYTES

        with pytest.raises(DocumentError) as raised:
            extract_text(b"%PDF-" + b"x" * MAXIMUM_BYTES)
        assert raised.value.problem is DocumentProblem.too_large

    def test_plain_text_pretending_to_be_a_document_is_unsupported(self):
        with pytest.raises(DocumentError) as raised:
            extract_text(b"Software Engineer at Example Corp" * 10, "resume.txt", "text/plain")
        assert raised.value.problem is DocumentProblem.unsupported
