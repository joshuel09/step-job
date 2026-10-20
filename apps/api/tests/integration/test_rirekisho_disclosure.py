"""Quickstart Scenario 4 — disclosure is respected in the document itself (gate G5).

The unit tests prove the filter. These prove the document: a real 履歴書 is
generated and its text read back, one case per flag in both directions. This
is the test that would catch a leak — the failure it guards against is
publishing someone's immigration status — so it asserts on what an employer
would read, not on what the code meant to do.

Undisclosed means absent entirely: the value, and its label too. A blank 国籍
line still tells the reader there is a nationality being withheld.
"""

import io
import re
from datetime import date

import pytest
from pypdf import PdfReader
from sqlalchemy import select

PATH = "/api/v1/profile/documents/rirekisho"

# Flag, and for each field it governs: its label and its value as written in a
# 西暦 document. Every value is distinct, so a leak names its source.
FLAGS = {
    "disclose_residence_status": [("在留資格", "永住者")],
    "disclose_nationality": [("国籍", "Philippines")],
    "disclose_visa": [("ビザの種類", "技術・人文知識・国際業務"), ("在留期限", "2028年3月31日")],
    "disclose_work_authorisation": [("就労資格", "あり")],
    "disclose_japanese_qualification": [("日本語能力", "JLPT N2")],
}

VALUES = {
    "residence_status": "永住者",
    "nationality": "Philippines",
    "visa_type": "技術・人文知識・国際業務",
    "visa_expires_on": date(2028, 3, 31),
    "work_authorisation": True,
    "japanese_qualification": "JLPT N2",
}


def _text(content: bytes) -> str:
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(content)).pages)
    return re.sub(r"[ 　]+", " ", text)


def _lines(content: bytes) -> list[str]:
    return [line.strip() for line in _text(content).splitlines() if line.strip()]


def _generate(client, auth_headers, body: dict | None = None) -> bytes:
    response = client.post(PATH, headers=auth_headers, json=body or {})
    assert response.status_code == 200, response.text
    return response.content


@pytest.fixture
def japan(session, rirekisho_profile):
    """Every Japan-specific field filled; every flag closed."""
    from app.career import models

    record = models.JapanProfile(profile_id=rirekisho_profile.id, **VALUES)
    session.add(record)
    session.flush()
    return record


def _set(session, japan, **flags: bool) -> None:
    for flag, value in flags.items():
        setattr(japan, flag, value)
    session.flush()


def _wanted_section(content: bytes) -> list[str]:
    lines = _lines(content)
    return lines[lines.index("本人希望記入欄") + 1 : lines.index("志望の動機")]


class TestUndisclosedLeavesNoTrace:
    def test_nothing_appears_by_default(self, client, auth_headers, japan):
        """Scenario 4: no value and no label — `grep -cE '国籍|在留|ビザ'` is 0."""
        text = _text(_generate(client, auth_headers))
        for fields in FLAGS.values():
            for label, value in fields:
                assert label not in text
                assert value not in text
        assert re.findall(r"国籍|在留|ビザ", text) == []

    def test_the_section_stays_empty_by_default(self, client, auth_headers, japan):
        assert _wanted_section(_generate(client, auth_headers)) == []

    @pytest.mark.parametrize("flag", FLAGS)
    def test_with_every_other_flag_open_this_one_stays_out(
        self, client, auth_headers, session, japan, flag
    ):
        _set(session, japan, **{f: True for f in FLAGS if f != flag})
        text = _text(_generate(client, auth_headers))

        for label, value in FLAGS[flag]:
            assert label not in text, f"{flag} closed, but its label {label!r} appears"
            assert value not in text, f"{flag} closed, but its value {value!r} appears"


class TestDisclosedAppears:
    @pytest.mark.parametrize("flag", FLAGS)
    def test_a_disclosed_field_appears_labelled_in_the_section(
        self, client, auth_headers, session, japan, flag
    ):
        _set(session, japan, **{flag: True})

        assert _wanted_section(_generate(client, auth_headers)) == [
            f"{label} {value}" for label, value in FLAGS[flag]
        ]

    def test_everything_disclosed_appears_in_order(self, client, auth_headers, session, japan):
        _set(session, japan, **{f: True for f in FLAGS})

        assert _wanted_section(_generate(client, auth_headers)) == [
            f"{label} {value}" for fields in FLAGS.values() for label, value in fields
        ]

    def test_a_disclosed_date_follows_the_documents_convention(
        self, client, auth_headers, session, japan
    ):
        """FR-019 applies here too: no Western year in a 和暦 document."""
        _set(session, japan, disclose_visa=True)
        section = _wanted_section(_generate(client, auth_headers, {"date_convention": "wareki"}))
        assert "在留期限 令和10年3月31日" in section

    def test_no_work_authorisation_is_written_as_such(self, client, auth_headers, session, japan):
        """False is a value the user chose to state, not an absence."""
        japan.work_authorisation = False
        _set(session, japan, disclose_work_authorisation=True)
        assert _wanted_section(_generate(client, auth_headers)) == ["就労資格 なし"]


class TestWithdrawal:
    def test_withdrawing_and_regenerating_removes_the_field(
        self, client, auth_headers, session, japan
    ):
        """FR-021: opt in, generate, opt out, generate again."""
        _set(session, japan, disclose_nationality=True)
        assert "Philippines" in _text(_generate(client, auth_headers))

        _set(session, japan, disclose_nationality=False)
        text = _text(_generate(client, auth_headers))
        assert "Philippines" not in text
        assert "国籍" not in text


# Each flag's fields as the snapshot stores them.
SNAPSHOTTED = {
    "disclose_residence_status": {"residence_status": "永住者"},
    "disclose_nationality": {"nationality": "Philippines"},
    "disclose_visa": {"visa_type": "技術・人文知識・国際業務", "visa_expires_on": "2028-03-31"},
    "disclose_work_authorisation": {"work_authorisation": True},
    "disclose_japanese_qualification": {"japanese_qualification": "JLPT N2"},
}

# Strings no flag-free snapshot may contain. `True` is left out: a payload is
# full of booleans that are not this one.
WITHHELD_TEXT = {
    flag: [v for v in vals.values() if isinstance(v, str)] for flag, vals in SNAPSHOTTED.items()
}


def _snapshot(session):
    from app.career import models

    return session.scalars(select(models.EntrySnapshot)).one()


class TestTheSnapshotRecordsWhatWasDisclosed:
    """FR-016: every line of the document traces to the entry behind it.

    A disclosed field is captured, so a line naming a nationality stays
    traceable after the user edits it. Only the disclosed fields are: the
    snapshot is the durable record of what was sent, and a withheld field in
    it would be the leak gate G5 exists to prevent (#110).
    """

    def test_nothing_disclosed_captures_no_japan_profile(
        self, client, auth_headers, session, japan
    ):
        _generate(client, auth_headers)

        snapshot = _snapshot(session)
        assert japan.id not in snapshot.captured_entry_ids
        for values in WITHHELD_TEXT.values():
            for value in values:
                assert value not in str(snapshot.payload)

    @pytest.mark.parametrize("flag", FLAGS)
    def test_a_disclosed_field_is_captured_alone(self, client, auth_headers, session, japan, flag):
        _set(session, japan, **{flag: True})
        _generate(client, auth_headers)

        snapshot = _snapshot(session)
        assert japan.id in snapshot.captured_entry_ids
        assert snapshot.payload[str(japan.id)] == {
            "__entity__": "JapanProfile",
            "id": str(japan.id),
            "profile_id": str(japan.profile_id),
            **SNAPSHOTTED[flag],
        }

    @pytest.mark.parametrize("flag", FLAGS)
    def test_with_every_other_flag_open_this_one_stays_out(
        self, client, auth_headers, session, japan, flag
    ):
        _set(session, japan, **{f: True for f in FLAGS if f != flag})
        _generate(client, auth_headers)

        snapshot = _snapshot(session)
        captured = snapshot.payload[str(japan.id)]
        for field in SNAPSHOTTED[flag]:
            assert field not in captured
        for value in WITHHELD_TEXT[flag]:
            assert value not in str(snapshot.payload)
        for flag_name in FLAGS:
            assert flag_name not in captured, "the flags themselves are not document content"

    def test_the_record_outlives_an_edit(self, client, auth_headers, session, japan):
        """The #110 scenario: disclose, generate, edit — the record keeps what went out."""
        _set(session, japan, disclose_nationality=True)
        _generate(client, auth_headers)

        japan.nationality = "Viet Nam"
        session.flush()

        assert _snapshot(session).payload[str(japan.id)]["nationality"] == "Philippines"

    def test_a_japan_profile_cannot_be_captured_whole(self, client, auth_headers, japan):
        """The general capture endpoint takes no field list, so it must refuse."""
        response = client.post(
            "/api/v1/profile/snapshots",
            headers=auth_headers,
            json={"document_ref": "anything", "entry_ids": [str(japan.id)]},
        )
        assert response.status_code == 422
        assert "Philippines" not in response.text


class TestDeletionErasesWhatTheSnapshotHolds:
    """FR-024: the immediately-erased fields go on the request path, copies included."""

    def test_deleting_the_profile_erases_them_from_the_snapshot(
        self, client, auth_headers, session, japan
    ):
        from app.career.models import JapanProfile

        _set(session, japan, **{f: True for f in FLAGS})
        _generate(client, auth_headers)

        assert client.delete("/api/v1/profile", headers=auth_headers).status_code == 200
        session.expire_all()

        captured = _snapshot(session).payload[str(japan.id)]
        for field in JapanProfile.IMMEDIATELY_ERASED:
            assert field not in captured
        for value in ("永住者", "Philippines", "技術・人文知識・国際業務", "2028-03-31"):
            assert value not in str(_snapshot(session).payload)

    def test_what_is_not_erased_immediately_stays_until_the_purge(
        self, client, auth_headers, session, japan
    ):
        _set(session, japan, **{f: True for f in FLAGS})
        _generate(client, auth_headers)

        assert client.delete("/api/v1/profile", headers=auth_headers).status_code == 200
        session.expire_all()

        captured = _snapshot(session).payload[str(japan.id)]
        assert captured["work_authorisation"] is True
        assert captured["japanese_qualification"] == "JLPT N2"

    def test_the_other_entries_in_the_snapshot_are_untouched(
        self, client, auth_headers, session, japan
    ):
        _set(session, japan, disclose_nationality=True)
        _generate(client, auth_headers)
        before = {k: v for k, v in _snapshot(session).payload.items() if k != str(japan.id)}

        assert client.delete("/api/v1/profile", headers=auth_headers).status_code == 200
        session.expire_all()

        after = {k: v for k, v in _snapshot(session).payload.items() if k != str(japan.id)}
        assert after == before
