"""Every pass through the document surface leaves a line, and only a line.

The unit test holds the formatter to the allow-list. This holds the calls:
that each outcome a user can reach is actually recorded, and that nothing
emitted along the way carries a word of the document — asserted on the
formatted output, because a `LogRecord` can hold anything and the formatter is
the only thing between it and the log.
"""

import io
import json
import logging

import pytest
from app.core.logging import JsonFormatter
from pypdf import PdfReader

PATH = "/api/v1/profile/documents/rirekisho"
READINESS = f"{PATH}/readiness"
LOGGER = "app.rirekisho.service"


@pytest.fixture
def logs(caplog):
    """Every line the document service emits during one test."""
    with caplog.at_level(logging.INFO, logger=LOGGER):
        yield caplog


def _lines(logs, message: str) -> list[logging.LogRecord]:
    return [r for r in logs.records if r.name == LOGGER and r.getMessage() == message]


def _one(logs, message: str) -> logging.LogRecord:
    found = _lines(logs, message)
    assert len(found) == 1, f"expected one {message!r}, got {len(found)}"
    return found[0]


class TestWhatIsRecorded:
    def test_a_report_on_a_complete_profile_records_it_as_ready(
        self, client, auth_headers, rirekisho_profile, logs
    ):
        client.get(READINESS, headers=auth_headers)

        line = _one(logs, "readiness reported")
        assert line.outcome == "ready"
        assert str(line.profile_id) == str(rirekisho_profile.id)
        # The fixture lacks a phone, an email and any certification.
        assert line.count == 3

    def test_a_report_on_an_empty_profile_records_it_as_incomplete(
        self, client, auth_headers, session, user_id, logs
    ):
        from app.career import service

        service.get_or_create_profile(session, user_id)
        client.get(READINESS, headers=auth_headers)

        assert _one(logs, "readiness reported").outcome == "incomplete"

    def test_a_refusal_is_recorded_with_how_much_was_missing(
        self, client, auth_headers, session, user_id, logs
    ):
        from app.career import service

        service.get_or_create_profile(session, user_id)
        assert client.post(PATH, headers=auth_headers, json={}).status_code == 422

        line = _one(logs, "rirekisho refused")
        assert line.outcome == "missing_required"
        assert line.count == 1
        assert not _lines(logs, "rirekisho generated"), "nothing was produced"

    def test_a_generated_document_is_recorded_with_its_snapshot(
        self, client, auth_headers, rirekisho_profile, logs
    ):
        response = client.post(PATH, headers=auth_headers, json={})
        assert response.status_code == 200, response.text

        line = _one(logs, "rirekisho generated")
        assert str(line.snapshot_id) == response.headers["X-Snapshot-Id"]
        assert str(line.count) == response.headers["X-Document-Pages"]

    def test_including_japan_fields_is_recorded_as_a_count(
        self, client, auth_headers, session, rirekisho_profile, logs
    ):
        """A document went out carrying them, which is worth being able to find."""
        from app.career import models

        session.add(
            models.JapanProfile(
                profile_id=rirekisho_profile.id,
                nationality="Philippines",
                japanese_qualification="JLPT N2",
                disclose_nationality=True,
                disclose_japanese_qualification=True,
            )
        )
        session.flush()

        assert client.post(PATH, headers=auth_headers, json={}).status_code == 200

        line = _one(logs, "japan fields included")
        assert line.outcome == "disclosed"
        assert line.count == 2

    def test_a_document_with_nothing_disclosed_records_no_such_line(
        self, client, auth_headers, rirekisho_profile, logs
    ):
        """Closed flags are the default, and silence is the honest record."""
        assert client.post(PATH, headers=auth_headers, json={}).status_code == 200
        assert _lines(logs, "japan fields included") == []


class TestWhatIsNeverRecorded:
    def test_no_word_of_the_document_reaches_a_log(
        self, client, auth_headers, session, rirekisho_profile, logs
    ):
        from app.career import models

        session.add(
            models.JapanProfile(
                profile_id=rirekisho_profile.id,
                nationality="Philippines",
                disclose_nationality=True,
            )
        )
        session.flush()

        client.get(READINESS, headers=auth_headers)
        response = client.post(PATH, headers=auth_headers, json={})
        assert response.status_code == 200

        formatter = JsonFormatter()
        written = "\n".join(formatter.format(record) for record in logs.records)

        # Everything the fixture puts on the page, and the one disclosed value.
        for secret in (
            "Taro Yamada",
            "山田太郎",
            "東京都新宿区サンプル1-2-3",
            "1990-05-15",
            "サンプル大学",
            "株式会社サンプル",
            "Example Corp",
            "Software Engineer",
            "Philippines",
        ):
            assert secret not in written, f"{secret!r} reached a log"

        # And it really was on the page, so the assertion above has something
        # to be about.
        pages = PdfReader(io.BytesIO(response.content)).pages
        assert "Example Corp" in "\n".join(p.extract_text() or "" for p in pages)

    def test_every_line_survives_the_formatter_as_json(
        self, client, auth_headers, rirekisho_profile, logs
    ):
        """A line that cannot be written is a line that will not be there."""
        client.get(READINESS, headers=auth_headers)
        client.post(PATH, headers=auth_headers, json={})

        assert logs.records
        for record in logs.records:
            json.loads(JsonFormatter().format(record))
