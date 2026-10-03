"""Quickstart Scenario 4, through a generated document.

`test_snapshot_traceability.py` proves the snapshot machinery holds its wording
when an entry changes. This proves the machinery is actually wired to document
generation: that producing a 履歴書 records what the document was based on, and
that the record still describes the document after the profile moves on.

Without this, every claim about a document being traceable rests on a feature
nobody calls.
"""

import io

from pypdf import PdfReader


def _text(content: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)


def _generate(client, headers):
    response = client.post("/api/v1/profile/documents/rirekisho", headers=headers, json={})
    assert response.status_code == 200, response.text
    return response


def _snapshot(session, snapshot_id):
    import uuid

    from app.career.models import EntrySnapshot

    return session.get(EntrySnapshot, uuid.UUID(snapshot_id))


def test_generating_a_document_records_what_it_was_based_on(
    client, auth_headers, rirekisho_profile, session
):
    response = _generate(client, auth_headers)

    snapshot = _snapshot(session, response.headers["X-Snapshot-Id"])
    assert snapshot is not None
    assert snapshot.profile_id == rirekisho_profile.id


def test_the_snapshot_names_every_entry_the_document_used(
    client, auth_headers, rirekisho_profile, session
):
    """The link between a line in the document and an entry in the profile."""
    from app.career.models import Education, WorkExperience

    response = _generate(client, auth_headers)
    snapshot = _snapshot(session, response.headers["X-Snapshot-Id"])

    captured = set(snapshot.captured_entry_ids)
    expected = {
        row.id
        for model in (Education, WorkExperience)
        for row in session.query(model).filter_by(profile_id=rirekisho_profile.id)
    }
    assert expected <= captured


def test_the_snapshot_still_describes_the_document_after_the_entry_changes(
    client, auth_headers, rirekisho_profile, session
):
    """FR-016: what was sent to an employer does not change retroactively.

    The document went out naming 株式会社サンプル. Renaming the entry afterwards
    must not rewrite the record of what the employer received.
    """
    from app.career.models import WorkExperience

    response = _generate(client, auth_headers)
    assert "株式会社サンプル" in _text(response.content)
    snapshot_id = response.headers["X-Snapshot-Id"]

    experience = (
        session.query(WorkExperience)
        .filter_by(profile_id=rirekisho_profile.id, employer_name="株式会社サンプル")
        .one()
    )
    experience.employer_name = "株式会社リネーム"
    session.flush()

    snapshot = _snapshot(session, snapshot_id)
    session.refresh(snapshot)
    captured = str(snapshot.payload)
    assert "株式会社サンプル" in captured
    assert "株式会社リネーム" not in captured


def test_a_later_document_reflects_the_edit(client, auth_headers, rirekisho_profile, session):
    """The profile is live; only the snapshot is frozen."""
    from app.career.models import WorkExperience

    first = _generate(client, auth_headers)

    experience = (
        session.query(WorkExperience)
        .filter_by(profile_id=rirekisho_profile.id, employer_name="株式会社サンプル")
        .one()
    )
    experience.employer_name = "株式会社リネーム"
    session.flush()

    second = _generate(client, auth_headers)

    assert "株式会社リネーム" in _text(second.content)
    assert second.headers["X-Snapshot-Id"] != first.headers["X-Snapshot-Id"]


def test_each_generation_records_itself_separately(
    client, auth_headers, rirekisho_profile, session
):
    """Two documents sent to two employers are two distinct records."""
    first = _generate(client, auth_headers).headers["X-Snapshot-Id"]
    second = _generate(client, auth_headers).headers["X-Snapshot-Id"]

    assert first != second
    assert _snapshot(session, first) is not None
    assert _snapshot(session, second) is not None
