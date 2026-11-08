"""Quickstart Scenarios 16 and 20 — what persists, and what does not.

Two halves of the same requirement. The document is not kept (FR-005); the
record of what it said is (FR-015), and that record has to survive the
profile changing underneath it or "what did I send them" has no answer.

Scenario 16 is the combination `test_resume_snapshot.py` does not reach.
That file edits an approval and, separately, edits an entry that has no
approval. The case a user actually arrives at is both at once: English was
approved from a Japanese sentence, the document went out, and then the
Japanese was edited — which makes the approval stale, keeps it in use, and
must leave the record of what was printed exactly as it was (FR-023, R-010).
"""

import uuid
from datetime import UTC, date, datetime

import pytest
from app.career import snapshots
from app.career.models import Locale
from app.translations.models import EntryTranslation, TranslatableEntry
from sqlalchemy import select

PATH = "/api/v1/profile/documents/resume"

ORIGINAL_TITLE = "システムエンジニア"
ORIGINAL_DESCRIPTION = "社内システムの開発を担当。"
APPROVED_TITLE = "Systems Engineer"


@pytest.fixture
def sent(session, user_id):
    """A Japanese role with an approved English title. One profile, one role."""
    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)
    session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
    entry = models.WorkExperience(
        profile_id=profile.id,
        employer_name="株式会社サンプル",
        employer_name_normalised="サンプル",
        job_title=ORIGINAL_TITLE,
        started_on=date(2015, 4, 1),
        ended_on=date(2021, 3, 31),
        description=ORIGINAL_DESCRIPTION,
        source_language=models.Locale.ja,
    )
    session.add(entry)
    session.flush()

    session.add(
        EntryTranslation(
            profile_id=profile.id,
            entry_type=TranslatableEntry.work_experience,
            entry_id=entry.id,
            field="job_title",
            language=Locale.en,
            approved_text=APPROVED_TITLE,
            approved_at=datetime.now(UTC),
            source_fingerprint="0" * 64,
        )
    )
    session.flush()
    return profile, entry


def _generate(client, auth_headers) -> uuid.UUID:
    response = client.post(PATH, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return uuid.UUID(response.headers["X-Snapshot-Id"])


class TestTheRecordHoldsWhatWasPrinted:
    """Scenario 16, FR-015."""

    @pytest.fixture
    def after_the_edit(self, client, auth_headers, session, sent):
        """Generate, then rewrite the Japanese the English was approved from."""
        profile, entry = sent
        snapshot_id = _generate(client, auth_headers)

        entry.job_title = "上級システムエンジニア"
        entry.description = "部門全体の基盤を設計。"
        session.flush()

        return snapshots.read(session, profile, snapshot_id)

    def test_the_english_that_was_printed_is_still_there(self, after_the_edit):
        titles = {item["job_title"] for item in after_the_edit.payload["rendered"]["experiences"]}
        assert titles == {APPROVED_TITLE}

    def test_the_japanese_is_recorded_as_it_read_at_the_time(self, after_the_edit):
        """The entry copy too, not only the rendered half. A record that
        moved with the row would make the approval look as though it had
        been taken against a sentence the user never approved."""
        written = str(after_the_edit.payload)

        assert ORIGINAL_DESCRIPTION in written
        assert "部門全体の基盤を設計。" not in written

    def test_the_edit_did_happen(self, session, sent, after_the_edit):
        """The two assertions above are satisfied by an edit that never
        took, which is the one way they could both pass for no reason."""
        _, entry = sent
        session.refresh(entry)
        assert entry.job_title == "上級システムエンジニア"

    def test_a_later_document_reflects_the_edit(self, client, auth_headers, after_the_edit):
        """The snapshot is frozen; the profile is not. A product where the
        edit never reached the next document would pass every test above."""
        import io

        from pypdf import PdfReader

        response = client.post(PATH, headers=auth_headers, json={})
        assert response.status_code == 200, response.text
        text = "\n".join(
            page.extract_text() or "" for page in PdfReader(io.BytesIO(response.content)).pages
        )

        # The title still prints the approved English — stale is kept and
        # used (FR-023) — but the description had no approval, so the new
        # Japanese is what appears.
        assert APPROVED_TITLE in text
        assert "部門全体の基盤を設計。" in text


class TestTheDocumentItselfIsNotRetained:
    """Scenario 20, FR-005.

    Asserted against the schema rather than against a count of rows. A count
    shows only that today's code stores nothing; no column that could hold a
    file means no later change stores one without a migration to argue about
    in review.

    `test_nothing_in_the_schema_can_hold_a_generated_document` in feature 003
    walks `Base.metadata` and so already covers this feature's tables. Stated
    again here for feature 005's own additions, because the guarantee should
    be deliberate rather than inherited.
    """

    def test_no_column_in_the_schema_could_hold_a_file(self, client, auth_headers, sent):
        from app.db.base import Base
        from sqlalchemy import LargeBinary

        _generate(client, auth_headers)

        binary = [
            f"{table.name}.{column.name}"
            for table in Base.metadata.tables.values()
            for column in table.columns
            if isinstance(column.type, LargeBinary)
        ]
        assert binary == []

    def test_the_walk_covers_this_feature_s_tables(self):
        """The assertion above is over whatever `Base.metadata` happens to
        hold. If feature 005's tables were not registered, it would pass
        while guarding nothing of this feature's."""
        from app.db.base import Base

        assert "entry_translation" in Base.metadata.tables
        assert "entry_snapshot" in Base.metadata.tables

    def test_no_column_is_named_for_a_document(self, client, auth_headers, sent):
        """A PDF fits in a text column too. This is the weaker, broader
        half: nothing in the schema is even called the thing."""
        from app.db.base import Base

        _generate(client, auth_headers)

        named = [
            f"{table.name}.{column.name}"
            for table in Base.metadata.tables.values()
            for column in table.columns
            if column.name in {"pdf", "document", "file", "content", "rendered_document"}
        ]
        assert named == []

    def test_generating_twice_adds_records_and_not_documents(
        self, client, auth_headers, session, sent
    ):
        """The runtime half, kept because the schema half cannot see a file
        written to disk or stashed in a JSON column."""
        from app.career.models import EntrySnapshot

        first = _generate(client, auth_headers)
        second = _generate(client, auth_headers)
        assert first != second

        rows = session.scalars(select(EntrySnapshot)).all()
        for row in rows:
            assert "%PDF" not in str(row.payload)
