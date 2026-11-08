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

import re
import uuid
from datetime import UTC, date, datetime

import pytest
from app.career import snapshots
from app.career.models import Locale
from app.resume.render import JOIN
from app.translations.models import EntryTranslation, TranslatableEntry
from sqlalchemy import select

PATH = "/api/v1/profile/documents/resume"

ORIGINAL_TITLE = "システムエンジニア"
ORIGINAL_DESCRIPTION = "社内システムの開発を担当。"
APPROVED_TITLE = "Systems Engineer"

#: When the fixture's one role ran, and the period the resume prints for it.
#: The period is written out rather than formatted from the dates:
#: `format_month` is what puts it on the page, and asking it what the page
#: should say would make the document its own oracle.
STARTED_ON = date(2015, 4, 1)
ENDED_ON = date(2021, 3, 31)
PERIOD = "Apr 2015 – Mar 2021"

#: What the user rewrites after the document has gone out.
EDITED_TITLE = "上級システムエンジニア"
EDITED_DESCRIPTION = "部門全体の基盤を設計。"


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
        started_on=STARTED_ON,
        ended_on=ENDED_ON,
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

        entry.job_title = EDITED_TITLE
        entry.description = EDITED_DESCRIPTION
        session.flush()

        return snapshots.read(session, profile, snapshot_id)

    def test_the_record_describes_the_document_that_was_sent(
        self, client, auth_headers, session, sent
    ):
        """Before anything is edited, and against the file itself.

        Every other test here reads the record after the profile moved, and
        what they show is that it did not move with it. None of them shows
        it ever matched the page: a snapshot describing a document nobody
        received would satisfy all four. This one holds the rendered half
        to the bytes that were streamed back.

        The whole page, not each field in it. `in printed` would be
        satisfied by a record that said `Engineer` where the document said
        `Systems Engineer`, and by one that described three of the four
        things on the page — so what the record holds is assembled into the
        document it claims to describe and the two are compared entire.

        Whitespace is squashed on both sides. A long sentence wraps where
        the column ends, and a line break the layout chose is not a
        difference between what was recorded and what was sent.
        """
        import io

        from pypdf import PdfReader

        profile, _ = sent
        response = client.post(PATH, headers=auth_headers, json={})
        assert response.status_code == 200, response.text

        pages = PdfReader(io.BytesIO(response.content)).pages
        printed = re.sub(r"\s+", "", "\n".join(page.extract_text() or "" for page in pages))
        rendered = snapshots.read(
            session, profile, uuid.UUID(response.headers["X-Snapshot-Id"])
        ).payload["rendered"]

        def squashed(value: str) -> str:
            return re.sub(r"\s+", "", value)

        # This profile holds exactly one role, which is what makes the page
        # below writable in full.
        assert len(rendered["experiences"]) == 1, rendered["experiences"]
        item = rendered["experiences"][0]

        # The dates are in the record and not on the page in that form, so
        # the comparison below cannot reach them: a record that misstated
        # when someone worked somewhere would describe the right-looking
        # document and still be wrong about their career.
        assert item["started_on"] == STARTED_ON.isoformat()
        assert item["ended_on"] == ENDED_ON.isoformat()

        described = "\n".join(
            [
                rendered["contact"]["full_name"],
                "Experience",
                f"{item['job_title']}{JOIN}{item['employer']}",
                PERIOD,
                item["description"],
            ]
        )

        assert printed == squashed(described)

    def test_the_english_that_was_printed_is_still_there(self, after_the_edit):
        """What this one does *not* prove: that the record is frozen. An
        approval survives the Japanese being edited, so a snapshot that
        re-rendered from live rows would answer the same way. The test
        below is where the freezing is checked.
        """
        titles = {item["job_title"] for item in after_the_edit.payload["rendered"]["experiences"]}
        assert titles == {APPROVED_TITLE}

    def test_the_japanese_is_recorded_as_it_read_at_the_time(self, after_the_edit):
        """The entry copy too, not only the rendered half. A record that
        moved with the row would make the approval look as though it had
        been taken against a sentence the user never approved."""
        written = str(after_the_edit.payload)

        assert ORIGINAL_DESCRIPTION in written
        assert EDITED_DESCRIPTION not in written
        # The title too. The approval masks it in the rendered half, so the
        # entry copy is the only place a record that moved with the row
        # would show.
        assert ORIGINAL_TITLE in written
        assert EDITED_TITLE not in written

    def test_the_edit_did_happen(self, session, sent, after_the_edit):
        """The two assertions above are satisfied by an edit that never
        took, which is the one way they could both pass for no reason."""
        _, entry = sent
        session.refresh(entry)
        assert entry.job_title == EDITED_TITLE

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
        assert EDITED_DESCRIPTION in text


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

    def test_no_column_in_the_schema_could_hold_a_file(self):
        from app.db.base import Base
        from sqlalchemy import LargeBinary

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
        while guarding nothing of this feature's.

        Registration is a side effect of importing the modules that define
        the models, so this imports the application rather than relying on
        what this file happens to have imported at the top. The question is
        whether the running application registers them, not whether a test
        can make it look as though it does.
        """
        import app.main  # noqa: F401
        from app.db.base import Base

        assert "entry_translation" in Base.metadata.tables
        assert "entry_snapshot" in Base.metadata.tables

    def test_no_column_is_named_for_a_document(self):
        """A PDF fits in a text column too. This is the weaker, broader
        half: nothing in the schema is even called the thing.

        `document` is not among the forbidden parts — `entry_snapshot`
        has a `document_ref`, which names which document a record is of
        and holds no document. Forbidding the word would mean forbidding
        the thing this feature correctly does.
        """
        from app.db.base import Base

        named = [
            f"{table.name}.{column.name}"
            for table in Base.metadata.tables.values()
            for column in table.columns
            if column.name in {"document", "file", "content", "rendered_document"}
            or "pdf" in column.name
            or "blob" in column.name
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
        # Counted, because an empty list satisfies the loop below and would
        # mean the session could not see what the route wrote.
        assert len(rows) == 2
        for row in rows:
            written = str(row.payload)
            assert "%PDF" not in written
            # A file put into a JSON column would arrive base64-encoded,
            # where the header this checks for does not appear at all.
            assert "JVBERi" not in written
