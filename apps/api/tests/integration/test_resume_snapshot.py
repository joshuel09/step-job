"""What the document said, after the profile stops saying it.

R-010 and SC-008. `snapshots.capture` serialises the entries a document
drew on, which for a Japanese profile is the Japanese — so a snapshot of
entry ids alone would, the moment a user edits an approval, describe a
document that no longer resembles the one they sent.

The English that was printed is recorded beside the entries. The test that
matters is the one that changes the profile afterwards and reads the
snapshot back: everything else here would pass against a snapshot that
stored nothing but ids.
"""

import uuid
from datetime import UTC, datetime

import pytest
from app.career import snapshots
from app.career.models import Locale, WorkExperience
from app.resume.service import DOCUMENT_REF
from app.translations.models import EntryTranslation, TranslatableEntry
from sqlalchemy import select

PATH = "/api/v1/profile/documents/resume"


@pytest.fixture
def approved(session, resume_profile):
    """An approved English title on the Japanese role."""
    entry = session.scalars(
        select(WorkExperience).where(
            WorkExperience.profile_id == resume_profile.id,
            WorkExperience.employer_name == "株式会社サンプル",
        )
    ).one()

    session.add(
        EntryTranslation(
            profile_id=resume_profile.id,
            entry_type=TranslatableEntry.work_experience,
            entry_id=entry.id,
            field="job_title",
            language=Locale.en,
            approved_text="Systems Engineer",
            approved_at=datetime.now(UTC),
            source_fingerprint="0" * 64,
        )
    )
    session.flush()
    return entry


def _generate(client, auth_headers):
    response = client.post(PATH, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return uuid.UUID(response.headers["X-Snapshot-Id"])


class TestTheRecordOfWhatWasSent:
    def test_the_snapshot_is_labelled_for_this_document(
        self, client, auth_headers, session, resume_profile
    ):
        snapshot = snapshots.read(session, resume_profile, _generate(client, auth_headers))

        assert snapshot.document_ref == DOCUMENT_REF

    def test_the_identity_leads_the_entries(self, client, auth_headers, session, resume_profile):
        """A profile holding only a name and one role still produces a
        document, and `capture` refuses an empty list."""
        from app.career.models import Identity

        identity = session.scalars(
            select(Identity).where(Identity.profile_id == resume_profile.id)
        ).one()

        snapshot = snapshots.read(session, resume_profile, _generate(client, auth_headers))

        assert snapshot.captured_entry_ids[0] == identity.id

    def test_every_rendered_entry_is_captured(self, client, auth_headers, session, resume_profile):
        snapshot = snapshots.read(session, resume_profile, _generate(client, auth_headers))

        captured = set(snapshot.captured_entry_ids)
        for employer in ("株式会社サンプル", "Example Corp"):
            entry = session.scalars(
                select(WorkExperience).where(
                    WorkExperience.profile_id == resume_profile.id,
                    WorkExperience.employer_name == employer,
                )
            ).one()
            assert entry.id in captured, employer

    def test_the_english_that_was_printed_is_recorded(
        self, client, auth_headers, session, resume_profile, approved
    ):
        snapshot = snapshots.read(session, resume_profile, _generate(client, auth_headers))

        titles = {entry["job_title"] for entry in snapshot.payload["rendered"]["experiences"]}
        assert "Systems Engineer" in titles

    def test_and_it_survives_the_approval_being_edited(
        self, client, auth_headers, session, resume_profile, approved
    ):
        """SC-008, and the only test here that a snapshot of entry ids
        alone would fail.

        The user sends the document, then changes their mind about the
        wording. What they sent does not change, and the record of it must
        not either — otherwise "what did I send them" has no answer.
        """
        snapshot_id = _generate(client, auth_headers)

        translation = session.scalars(
            select(EntryTranslation).where(EntryTranslation.profile_id == resume_profile.id)
        ).one()
        translation.approved_text = "Senior Systems Engineer"
        session.flush()

        snapshot = snapshots.read(session, resume_profile, snapshot_id)
        titles = {entry["job_title"] for entry in snapshot.payload["rendered"]["experiences"]}

        assert "Systems Engineer" in titles
        assert "Senior Systems Engineer" not in titles

    def test_and_it_survives_the_entry_itself_being_edited(
        self, client, auth_headers, session, resume_profile
    ):
        """The same guarantee for a profile with no translations at all —
        the entries are serialised as they read at capture."""
        snapshot_id = _generate(client, auth_headers)

        entry = session.scalars(
            select(WorkExperience).where(
                WorkExperience.profile_id == resume_profile.id,
                WorkExperience.employer_name == "Example Corp",
            )
        ).one()
        entry.employer_name = "Renamed Corp"
        session.flush()

        snapshot = snapshots.read(session, resume_profile, snapshot_id)
        employers = {item["employer"] for item in snapshot.payload["rendered"]["experiences"]}

        assert "Example Corp" in employers
        assert "Renamed Corp" not in employers

    def test_the_payload_is_json_a_column_will_take(
        self, client, auth_headers, session, resume_profile
    ):
        """Dates and ids are not things a JSON column accepts, and a
        snapshot that fails to serialise fails the generation it was
        capturing — in the same transaction, after the user asked for a
        document."""
        import json

        snapshot = snapshots.read(session, resume_profile, _generate(client, auth_headers))

        assert json.loads(json.dumps(snapshot.payload))["rendered"]["contact"]["full_name"] == (
            "Taro Yamada"
        )

    def test_nothing_withheld_reaches_the_payload(
        self, client, auth_headers, session, resume_profile
    ):
        """The rendered half of the payload is the dataclasses, which carry
        no address and no date of birth. Worth asserting here rather than
        only on the page: a snapshot is stored, and a document is not."""
        import json

        snapshot = snapshots.read(session, resume_profile, _generate(client, auth_headers))
        rendered = json.dumps(snapshot.payload["rendered"], ensure_ascii=False)

        assert "東京都千代田区" not in rendered
        assert "1990-05-15" not in rendered
