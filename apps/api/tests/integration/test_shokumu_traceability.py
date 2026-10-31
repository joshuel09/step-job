"""Quickstart Scenario 7 — the document stays traceable after an edit.

A 職務経歴書 goes to an employer and then the profile moves on: a title is
corrected, an employer renamed, an achievement reworded. What was sent does
not change, and the record of it must not either. Otherwise the one question
the snapshot exists to answer — what did they actually receive? — gets this
year's answer to last year's question.

`test_snapshot_traceability.py` proves the machinery. This proves it is wired
to this document, which is a separate thing: feature 003 needed the same test
for the same reason.
"""

import io
import uuid

from pypdf import PdfReader
from sqlalchemy import select

PATH = "/api/v1/profile/documents/shokumu-keirekisho"


def _generate(client, auth_headers, **body):
    response = client.post(PATH, headers=auth_headers, json=body)
    assert response.status_code == 200, response.text
    return response


def _text(pdf: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


def _snapshot(session, snapshot_id: str):
    from app.career.models import EntrySnapshot

    return session.get(EntrySnapshot, uuid.UUID(snapshot_id))


def _employer(session, profile_id, name: str):
    from app.career import models

    return session.scalars(
        select(models.WorkExperience).where(
            models.WorkExperience.profile_id == profile_id,
            models.WorkExperience.employer_name == name,
        )
    ).one()


class TestWhatWasSentIsRecorded:
    def test_generating_records_what_it_was_based_on(
        self, client, auth_headers, session, shokumu_profile
    ):
        response = _generate(client, auth_headers)

        snapshot = _snapshot(session, response.headers["X-Snapshot-Id"])
        assert snapshot is not None
        assert snapshot.profile_id == shokumu_profile.id

    def test_the_snapshot_names_the_achievements_too(
        self, client, auth_headers, session, shokumu_profile
    ):
        """The 履歴書 carries no career stories, so this is the first document
        whose snapshot has to hold them."""
        from app.career import models

        response = _generate(client, auth_headers)
        captured = set(_snapshot(session, response.headers["X-Snapshot-Id"]).captured_entry_ids)

        stories = session.scalars(
            select(models.CareerStory).where(models.CareerStory.profile_id == shokumu_profile.id)
        )
        for story in stories:
            assert story.id in captured, f"{story.title} is in the document and not the record"

    def test_the_unattached_achievement_is_in_the_record_as_well(
        self, client, auth_headers, session, shokumu_profile
    ):
        """It is in the document, so it was sent, so it is recorded. An entry
        that belongs to no section is the one a capture loop forgets."""
        from app.career import models

        response = _generate(client, auth_headers)
        captured = set(_snapshot(session, response.headers["X-Snapshot-Id"]).captured_entry_ids)

        loose = session.scalars(
            select(models.CareerStory).where(
                models.CareerStory.profile_id == shokumu_profile.id,
                models.CareerStory.work_experience_id.is_(None),
            )
        ).one()
        assert loose.id in captured


class TestTheRecordDoesNotMoveWithTheProfile:
    def test_renaming_an_employer_does_not_rewrite_the_record(
        self, client, auth_headers, session, shokumu_profile
    ):
        response = _generate(client, auth_headers)
        assert "株式会社サンプル" in _text(response.content)
        snapshot_id = response.headers["X-Snapshot-Id"]

        entry = _employer(session, shokumu_profile.id, "株式会社サンプル")
        entry.employer_name = "株式会社リネーム"
        session.flush()

        snapshot = _snapshot(session, snapshot_id)
        session.refresh(snapshot)
        captured = str(snapshot.payload)
        assert "株式会社サンプル" in captured
        assert "株式会社リネーム" not in captured

    def test_rewording_an_achievement_does_not_rewrite_the_record(
        self, client, auth_headers, session, shokumu_profile
    ):
        """The part that is this document's own: a 履歴書 carries no stories,
        so nothing before this feature put one in a snapshot."""
        from app.career import models

        snapshot_id = _generate(client, auth_headers).headers["X-Snapshot-Id"]

        story = session.scalars(
            select(models.CareerStory).where(models.CareerStory.title == "ビルド時間を半分にした")
        ).one()
        story.result = "まったく別の結果になった。"
        session.flush()

        snapshot = _snapshot(session, snapshot_id)
        session.refresh(snapshot)
        captured = str(snapshot.payload)
        assert "二十分になった。" in captured
        assert "まったく別の結果" not in captured

    def test_deleting_an_entry_does_not_empty_the_record(
        self, client, auth_headers, session, shokumu_profile
    ):
        """FR-017: the record stays accurate after the entries are deleted.
        What an employer holds cannot be unsent."""
        from app.career import models

        snapshot_id = _generate(client, auth_headers).headers["X-Snapshot-Id"]

        story = session.scalars(
            select(models.CareerStory).where(models.CareerStory.title == "社外勉強会の運営")
        ).one()
        session.delete(story)
        session.flush()

        snapshot = _snapshot(session, snapshot_id)
        session.refresh(snapshot)
        assert "社外勉強会の運営" in str(snapshot.payload)


class TestTheProfileIsStillLive:
    def test_a_later_document_reflects_the_edit(
        self, client, auth_headers, session, shokumu_profile
    ):
        first = _generate(client, auth_headers)

        entry = _employer(session, shokumu_profile.id, "株式会社サンプル")
        entry.employer_name = "株式会社リネーム"
        session.flush()

        second = _generate(client, auth_headers)
        assert "株式会社リネーム" in _text(second.content)
        assert "株式会社サンプル" not in _text(second.content)
        assert second.headers["X-Snapshot-Id"] != first.headers["X-Snapshot-Id"]

    def test_two_documents_are_two_records(self, client, auth_headers, session, shokumu_profile):
        """Two documents sent to two employers are two distinct things to be
        asked about later."""
        first = _generate(client, auth_headers).headers["X-Snapshot-Id"]
        second = _generate(client, auth_headers).headers["X-Snapshot-Id"]

        assert first != second
        assert _snapshot(session, first) is not None
        assert _snapshot(session, second) is not None

    def test_the_arrangement_does_not_change_what_is_recorded(
        self, client, auth_headers, session, shokumu_profile
    ):
        """Both orders carry the same entries, so both records name the same
        entries (FR-008)."""
        newest = _generate(client, auth_headers, arrangement="reverse_chronological")
        oldest = _generate(client, auth_headers, arrangement="chronological")

        assert sorted(
            str(i) for i in _snapshot(session, newest.headers["X-Snapshot-Id"]).captured_entry_ids
        ) == sorted(
            str(i) for i in _snapshot(session, oldest.headers["X-Snapshot-Id"]).captured_entry_ids
        )
