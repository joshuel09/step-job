"""Quickstart Scenario 12 — what an English resume leaves out (FR-009, FR-010).

A 履歴書 asks for a date of birth, an address and a photograph, and feature
004 prints a user's Japan-specific circumstances when they have said to. A US
resume carries none of it, and an applicant should not have to know that: the
protection is the product's, not theirs to remember per document.

**Every disclosure flag is set to `true` here, deliberately.** That is the
state in which a leak is most likely and least excusable — the user has said
"yes, publish this", and meant it about a different document to a different
reader. Undisclosed values staying off the page would prove nothing; feature
004's own filter would be doing the work.

Two kinds of absence, which fail differently and so are tested differently:

- Nothing appears **on the page**, read back out of the PDF.
- Nothing is **fetched** in the first place. A value filtered out after
  loading is one a later layout change, a log line or a debug repr can still
  reach; a value never selected is not.

Every assertion of absence here runs in a test that first proves the document
was produced and its text could be read. `extract_text` returning an empty
string satisfies every `not in` ever written.
"""

import io
import json
import re
from datetime import date

import pytest
from pypdf import PdfReader
from sqlalchemy import event

PATH = "/api/v1/profile/documents/resume"

#: What the `resume_profile` fixture records and this document must not print.
BIRTH_DATE = date(1990, 5, 15)
ADDRESS = "東京都千代田区1-1-1"

#: Filled in full, and written out here rather than imported from feature
#: 004's disclosure test: that file is about what a 履歴書 *shows*, and the
#: day someone narrows it this guard must not narrow with it.
JAPAN = {
    "residence_status": "永住者",
    "nationality": "Philippines",
    "visa_type": "技術・人文知識・国際業務",
    "visa_expires_on": date(2028, 3, 31),
    "work_authorisation": True,
    "japanese_qualification": "JLPT N2",
}

FLAGS = (
    "disclose_residence_status",
    "disclose_nationality",
    "disclose_visa",
    "disclose_work_authorisation",
    "disclose_japanese_qualification",
)

#: Each value as it would be written. Derived from the fixture rather than
#: written out beside it: two lists that must agree are two lists that will
#: eventually not, and the one that silently stops guarding is this one.
#: `work_authorisation` is excluded — "True" is not a string a reader would
#: see, and the label is what gives that field away.
FORBIDDEN_VALUES = (
    *(str(value) for value in JAPAN.values() if not isinstance(value, bool)),
    str(JAPAN["visa_expires_on"].year),
    str(BIRTH_DATE.year),
    ADDRESS,
    "千代田区",
)

FORBIDDEN_LABELS = (
    "在留資格",
    "国籍",
    "ビザ",
    "在留期限",
    "就労",
    "日本語能力",
    "生年月日",
    "現住所",
    "写真",
    "Nationality",
    "Residence",
    "Visa",
    "Date of Birth",
    "Photo",
)


def _text(pdf: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)


def _age_on(day: date) -> int:
    """The age a reader would work out from the fixture's date of birth.

    Computed rather than written down, because a literal would stop being
    the applicant's age at the next birthday and the test would go on
    passing — against a number nobody has.
    """
    had_birthday = (day.month, day.day) >= (BIRTH_DATE.month, BIRTH_DATE.day)
    return day.year - BIRTH_DATE.year - (0 if had_birthday else 1)


@pytest.fixture
def disclosed(session, resume_profile):
    """Every Japan-specific field filled, and every flag open.

    Returned so a test can read it back: a fixture that silently failed to
    attach would make every absence below true for the wrong reason.
    """
    from app.career import models

    record = models.JapanProfile(
        profile_id=resume_profile.id,
        **JAPAN,
        **dict.fromkeys(FLAGS, True),
    )
    session.add(record)
    session.flush()
    return record


@pytest.fixture
def document(client, auth_headers, disclosed):
    response = client.post(PATH, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return _text(response.content)


class TestTheFixtureHoldsWhatItClaims:
    """Without these, every absence below is satisfied by an empty page."""

    def test_every_field_is_recorded_and_every_flag_is_open(self, disclosed):
        for field, value in JAPAN.items():
            assert getattr(disclosed, field) == value
        for flag in FLAGS:
            assert getattr(disclosed, flag) is True

    def test_the_identity_carries_the_two_fields_this_document_must_not_print(
        self, session, resume_profile
    ):
        from app.career import models
        from sqlalchemy import select

        identity = session.scalars(
            select(models.Identity).where(models.Identity.profile_id == resume_profile.id)
        ).one()
        assert identity.date_of_birth == BIRTH_DATE
        assert identity.address == ADDRESS

    def test_the_document_was_produced_and_can_be_read(self, document):
        """The positive control. Every `not in` in this file depends on it."""
        assert "Taro Yamada" in document
        assert "Example Corp" in document


class TestNoneOfItIsOnThePage:
    @pytest.mark.parametrize("value", FORBIDDEN_VALUES)
    def test_no_recorded_value_appears(self, document, value):
        assert value not in document

    @pytest.mark.parametrize("label", FORBIDDEN_LABELS)
    def test_no_label_appears(self, document, label):
        """Including the English ones. A resume that grew a "Nationality:"
        heading would be a leak whether or not anything followed it."""
        assert label.lower() not in document.lower()

    def test_no_age_can_be_read_off_the_page(self, document):
        """FR-009 is about what an employer can infer, not only about what
        is printed. A date of birth withheld and an age stated is the same
        disclosure made shorter.

        A bare word-boundary search, not `"age 36"` or `"36 years"`. The
        number alone beside a name is the disclosure; a phrasing this test
        did not predict would be the leak going unreported. It can in
        principle collide with an unrelated number the fixture starts
        printing — and that failure is loud, names this test, and takes a
        minute to read, which is the trade this file is making everywhere
        else too."""
        age = _age_on(date.today())
        assert re.search(rf"\b{age}\b", document) is None
        assert "歳" not in document
        assert re.search(r"\bages?\b", document, re.IGNORECASE) is None

    def test_no_photograph_frame_is_drawn(self, document):
        """A 履歴書 reserves a box for a photograph and labels it. On a US
        resume the box is the problem, not the label — a frame with nothing
        in it still invites a reader to notice there is no face."""
        assert "写真貼付欄" not in document
        assert "写真" not in document


class TestNoneOfItIsEvenFetched:
    """The other half of the guarantee, and the one that holds under change.

    A filter applied after loading leaves the row in the session, where the
    next person to add a log line or a debug repr can reach it. These assert
    against the SQL the generation path actually issued.
    """

    @staticmethod
    def _statements(session, run):
        """Every statement issued while `run()` ran.

        Listening on the bind rather than the engine, and removed in a
        `finally`: the engine is shared by the whole session-scoped suite,
        and a listener left attached by a failing test would follow every
        test after it.
        """
        seen: list[str] = []
        bind = session.get_bind()

        def capture(conn, cursor, statement, parameters, context, executemany):
            seen.append(statement)

        event.listen(bind, "before_cursor_execute", capture)
        try:
            run()
        finally:
            event.remove(bind, "before_cursor_execute", capture)
        return seen

    @staticmethod
    def _touching_japan(statements):
        return [sql for sql in statements if "japan_profile" in sql.lower()]

    def test_the_projection_issues_no_query_against_japan_profile(
        self, session, resume_profile, disclosed
    ):
        """What the renderer is given is assembled without the table being
        read at all — so there is no loaded row for a later change to find
        its way to."""
        from app.resume import service

        statements = self._statements(session, lambda: service.build(session, resume_profile))

        assert statements, "nothing was captured, so nothing was proved"
        assert not self._touching_japan(statements), self._touching_japan(statements)

    def test_the_readiness_report_does_not_either(self, session, resume_profile, disclosed):
        """Readiness reads more of the profile than the projection does, and
        it is the newer route — the likelier place for a convenient `select`
        over everything the profile holds to appear."""
        from app.resume import service

        statements = self._statements(
            session, lambda: service.readiness_report(session, resume_profile)
        )

        assert statements, "nothing was captured, so nothing was proved"
        assert not self._touching_japan(statements)

    def test_the_capture_would_notice(self, session, resume_profile, disclosed):
        """The two guards above assert that a string is absent, which is the
        kind of assertion that passes when the capture is broken. This issues
        the query they forbid and checks it is seen."""
        from app.career import models
        from sqlalchemy import select

        statements = self._statements(
            session,
            lambda: session.scalars(
                select(models.JapanProfile).where(
                    models.JapanProfile.profile_id == resume_profile.id
                )
            ).all(),
        )

        assert self._touching_japan(statements)


class TestTheOneTimeTheTableIsNamed:
    """Generating does issue a statement naming `japan_profile`, and it is
    not a fetch of this user's Japan profile.

    Snapshot capture resolves the ids a document drew on by looking for each
    one in every table a snapshot may hold, and that list includes the Japan
    profile because feature 004's 履歴書 legitimately captures disclosed
    fields from it. The ids this document passes are its own entries, so the
    probe matches nothing.

    Worth a test rather than a comment, because "it cannot match" is a claim
    about the ids being passed, and the ids being passed are a thing the next
    change to `generate` could alter.
    """

    @pytest.fixture
    def snapshot(self, session, resume_profile, disclosed):
        from app.resume import service

        _, _, snapshot = service.generate(session, resume_profile)
        return snapshot

    def test_the_japan_profile_is_not_among_the_entries_captured(self, snapshot, disclosed):
        assert disclosed.id not in snapshot.captured_entry_ids

    def test_generating_names_the_table_once_and_only_to_resolve_ids(
        self, session, resume_profile, disclosed
    ):
        """The whole call, snapshot capture included.

        The two guards above narrow to the projection, which leaves a gap
        the size of everything `generate` does afterwards: a fetch added
        inside capture would load this applicant's residence status without
        changing an id or a payload, and every other test in this file would
        pass. So the statement is identified rather than counted away — a
        lookup by id, which cannot be a fetch of someone's Japan profile,
        because a fetch of someone's Japan profile does not know an id to
        ask for.
        """
        from app.resume import service

        statements = TestNoneOfItIsEvenFetched._statements(
            session, lambda: service.generate(session, resume_profile)
        )
        touching = [sql for sql in statements if "japan_profile" in sql.lower()]

        assert len(touching) == 1, touching
        assert "japan_profile.id IN" in touching[0], touching[0]

    def test_the_snapshot_holds_no_japan_profile_entity(self, snapshot):
        entities = {
            value.get("__entity__")
            for value in snapshot.payload.values()
            if isinstance(value, dict)
        }
        assert "JapanProfile" not in entities
        assert "Identity" in entities, "the payload was not read as expected"

    def test_the_durable_record_carries_none_of_it_either(self, snapshot):
        """FR-009 is about the page, and a snapshot is not the page — but a
        record that copied a date of birth in because the document needed
        the name beside it would be a second place that data lives, outliving
        the user clearing it from their profile."""
        written = json.dumps(snapshot.payload, ensure_ascii=False, default=str)

        for value in FORBIDDEN_VALUES:
            assert value not in written, value

    def test_the_identity_is_recorded_narrowed_to_what_was_printed(self, snapshot):
        """By key rather than by substring. "address" appearing anywhere in a
        serialised payload could be an employer's description; the question
        is whether the identity row went in with a field the page never
        showed."""
        identity = next(
            value
            for value in snapshot.payload.values()
            if isinstance(value, dict) and value.get("__entity__") == "Identity"
        )

        assert set(identity) == {
            "__entity__",
            "id",
            "profile_id",
            "full_name_latin",
            "email",
            "phone",
        }
