"""Quickstart Scenarios 0 and 1 — a profile becomes a readable 履歴書.

Every assertion reads text back out of the document. A page of hollow boxes is
the right size and passes any check on bytes, so asserting on the file would
prove nothing about whether a Japanese employer could read it.
"""

import io

import pytest
from pypdf import PdfReader


def _text(content: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)


@pytest.fixture
def generated(client, auth_headers, rirekisho_profile):
    response = client.post("/api/v1/profile/documents/rirekisho", headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return response


def test_the_document_is_a_pdf(generated):
    assert generated.headers["content-type"] == "application/pdf"
    assert generated.content.startswith(b"%PDF-")


def test_the_japanese_is_readable(generated):
    """Scenario 0: the check a page of boxes would fail."""
    assert "履歴書" in _text(generated.content)


def test_the_glyphs_are_embedded(generated):
    """A document printed by an employer, not only read by its author."""
    assert b"/FontFile2" in generated.content


def test_the_identity_appears(generated):
    text = _text(generated.content)
    assert "山田太郎" in text
    assert "ヤマダタロウ" in text
    assert "東京都新宿区サンプル1-2-3" in text


def test_education_appears_before_employment(generated):
    text = _text(generated.content)
    assert text.index("サンプル大学") < text.index("株式会社サンプル")


def test_each_role_produces_joining_and_leaving(generated):
    text = _text(generated.content)
    assert "入社" in text
    assert "退社" in text


def test_an_ongoing_role_reads_genzai_ni_itaru(generated):
    """The fixture's second role has no end date."""
    assert "現在に至る" in _text(generated.content)


def test_the_table_ends_with_ijou(generated):
    assert "以上" in _text(generated.content)


def test_the_photograph_frame_is_labelled_and_empty(generated):
    """FR-022a: the product stores no photograph."""
    assert "写真貼付欄" in _text(generated.content)


def test_the_per_employer_sections_are_labelled(generated):
    """FR-022b and FR-022c: left for the user, and visibly so."""
    text = _text(generated.content)
    assert "志望の動機" in text
    assert "本人希望記入欄" in text


def test_no_gender_field_appears(generated):
    """FR-022: omitted, not an empty box inviting completion."""
    assert "性別" not in _text(generated.content)


def test_the_response_reports_its_page_count(generated):
    """So the interface can say when a document runs longer than usual."""
    assert int(generated.headers["X-Document-Pages"]) >= 1


def test_the_response_reports_what_the_document_was_based_on(generated):
    assert generated.headers["X-Snapshot-Id"]


def test_a_profile_without_a_name_is_refused(client, auth_headers):
    """FR-015: a document with a blank name is not a 履歴書."""
    assert client.post("/api/v1/profile", headers=auth_headers).status_code == 201

    response = client.post("/api/v1/profile/documents/rirekisho", headers=auth_headers, json={})
    assert response.status_code == 422
    assert "identity" in str(response.json()["failures"])


def test_nothing_in_the_schema_can_hold_a_generated_document(generated):
    """FR-005: the document is streamed, never stored.

    Asserted against the schema rather than against a count of rows. A count
    shows only that today's code stores nothing; no column that could hold a
    file means no later change stores one by accident.
    """
    from app.db.base import Base
    from sqlalchemy import LargeBinary

    binary = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, LargeBinary)
    ]
    assert binary == []


def test_a_first_time_applicant_gets_a_document(client, auth_headers, session, user_id):
    """FR-010: no education and no roles is a legitimate 履歴書, not an error.

    The table is just 以上. The identity is the only entry the document draws
    on, and the snapshot has to name it — a document based on nothing is not
    traceable to anything.
    """
    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)
    session.add(
        models.Identity(
            profile_id=profile.id,
            full_name_latin="Hanako Suzuki",
            full_name_japanese="鈴木花子",
            furigana="スズキハナコ",
        )
    )
    session.flush()

    response = client.post("/api/v1/profile/documents/rirekisho", headers=auth_headers, json={})
    assert response.status_code == 200, response.text

    text = _text(response.content)
    assert "鈴木花子" in text
    assert "以上" in text
    assert response.headers["X-Snapshot-Id"]
