"""Document logs record what happened, never what the document said.

A 履歴書 holds a name, an address, a date of birth and an employment history,
and the product deliberately keeps none of it after the file is handed over.
A log line quoting any of it would be exactly the copy that was not kept —
searchable, unmanaged, and outliving the deletion the rest of the system
honours (FR-025).

So the rule here is the one the import logs follow: outcomes and counts, by
identifier. The readiness report is the sharpest case, because it names
entries by the user's own text in order to be useful on screen.
"""

import json
import logging

from app.core.logging import JsonFormatter


def _formatted(**extra) -> dict:
    record = logging.LogRecord(
        "app.rirekisho.service", logging.INFO, __file__, 1, "rirekisho generated", None, None
    )
    record.__dict__.update(extra)
    return json.loads(JsonFormatter().format(record))


def test_outcomes_are_recorded():
    line = _formatted(profile_id="abc", snapshot_id="def", count=2, outcome="ready")

    assert line["profile_id"] == "abc"
    assert line["snapshot_id"] == "def"
    assert line["count"] == "2"
    assert line["outcome"] == "ready"


def test_the_identity_on_the_document_is_dropped():
    line = _formatted(
        profile_id="abc",
        full_name_latin="Taro Yamada",
        address="東京都新宿区サンプル1-2-3",
        date_of_birth="1990-05-15",
        phone="090-1234-5678",
    )

    serialised = json.dumps(line, ensure_ascii=False)
    assert "Taro Yamada" not in serialised
    assert "サンプル" not in serialised
    assert "1990" not in serialised
    assert "090" not in serialised


def test_the_readiness_report_itself_is_dropped():
    """It names entries by their own text, which is why it is never logged whole."""
    line = _formatted(
        profile_id="abc",
        missing_required=["identity.full_name_latin"],
        missing_optional=["identity.address"],
        entries_without_japanese=[{"label": "Example Corp", "entry_type": "work_experience"}],
        label="Example University",
    )

    serialised = json.dumps(line, ensure_ascii=False)
    assert "Example Corp" not in serialised
    assert "Example University" not in serialised
    assert "identity." not in serialised


def test_a_disclosed_japan_field_is_never_named():
    """Which flag someone opened is their immigration status by another name."""
    line = _formatted(
        profile_id="abc",
        nationality="Philippines",
        residence_status="永住者",
        disclosed=["disclose_visa"],
        count=1,
    )

    serialised = json.dumps(line, ensure_ascii=False)
    assert "Philippines" not in serialised
    assert "永住者" not in serialised
    assert "visa" not in serialised
    assert line["count"] == "1"
