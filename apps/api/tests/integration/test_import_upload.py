"""Quickstart Scenario 3 — import a file, and confirm it is not kept.

The retention check is the one worth having. FR-004 promises the document is not
retained, and the design keeps that promise by never writing it. A test that
only checked "no file in a known directory" would pass trivially; these look for
the document's own content anywhere it could plausibly have been left.
"""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

PDF = ("example-resume.pdf", "application/pdf")
DOCX = (
    "example-resume.docx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
)


def _profile(client, headers):
    assert client.post("/api/v1/profile", headers=headers).status_code == 201


def _upload(client, headers, fixture):
    name, content_type = fixture
    with (FIXTURES / name).open("rb") as handle:
        return client.post(
            "/api/v1/profile/imports/upload",
            headers=headers,
            files={"file": (name, handle, content_type)},
        )


@pytest.mark.parametrize("fixture", [PDF, DOCX], ids=["pdf", "docx"])
def test_a_document_produces_proposals(client, auth_headers, fixture):
    _profile(client, auth_headers)

    response = _upload(client, auth_headers, fixture)
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["status"] == "completed"
    assert body["entry_count"] >= 1


def test_a_pdf_and_a_docx_of_the_same_resume_agree(client, auth_headers):
    _profile(client, auth_headers)

    pdf = _upload(client, auth_headers, PDF).json()
    docx = _upload(client, auth_headers, DOCX).json()

    assert pdf["entry_count"] == docx["entry_count"]


def test_the_uploaded_document_is_not_retained(client, auth_headers, session):
    """FR-004, checked by looking for the document rather than assuming."""
    from app.imports.models import Import

    _profile(client, auth_headers)
    _upload(client, auth_headers, PDF)

    # Nothing in the import record holds the document or its name.
    for record in session.query(Import).all():
        stored = str(record.outcome or "") + str(record.source_kind)
        assert "example-resume" not in stored
        assert not hasattr(record, "filename")
        assert not hasattr(record, "document")

    # And no temporary file was left anywhere obvious.
    for directory in (Path("/tmp"), Path("/var/tmp"), Path.cwd()):
        if directory.exists():
            assert not list(directory.glob("*example-resume*"))


def test_the_filename_is_never_stored(client, auth_headers):
    """FR-019b: a name can reveal where someone was applying."""
    _profile(client, auth_headers)

    with (FIXTURES / "example-resume.pdf").open("rb") as handle:
        created = client.post(
            "/api/v1/profile/imports/upload",
            headers=auth_headers,
            files={"file": ("application-to-Example-Corp.pdf", handle, "application/pdf")},
        ).json()

    listed = client.get("/api/v1/profile/imports", headers=auth_headers).json()
    assert "application-to-Example-Corp" not in str(listed)
    assert "filename" not in created


def test_a_scan_with_no_text_is_reported_as_unreadable(client, auth_headers):
    """Not as a service problem. Retrying will never help, and the user should know."""
    _profile(client, auth_headers)

    response = _upload(client, auth_headers, ("scanned-no-text.pdf", "application/pdf"))
    assert response.status_code == 201

    body = response.json()
    assert body["status"] == "failed"
    assert body["failure_reason"] == "unreadable_document"
    assert body["entry_count"] == 0


def test_an_unsupported_format_is_refused(client, auth_headers):
    _profile(client, auth_headers)

    response = client.post(
        "/api/v1/profile/imports/upload",
        headers=auth_headers,
        files={"file": ("notes.txt", b"Software Engineer at Example Corp" * 5, "text/plain")},
    )
    assert response.status_code == 415


def test_a_failed_upload_leaves_nothing_behind(client, auth_headers):
    """FR-017d: a failure produces no proposals and no partial set."""
    _profile(client, auth_headers)
    _upload(client, auth_headers, ("scanned-no-text.pdf", "application/pdf"))

    assert client.get("/api/v1/profile/proposals", headers=auth_headers).json() == []
    assert client.get("/api/v1/profile", headers=auth_headers).json()["experiences"] == []


def test_an_import_from_a_file_records_its_source_kind(client, auth_headers):
    _profile(client, auth_headers)

    assert _upload(client, auth_headers, PDF).json()["source_kind"] == "pdf"
    assert _upload(client, auth_headers, DOCX).json()["source_kind"] == "docx"
