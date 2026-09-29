"""Import logs record what happened, never the document it happened to.

A log holding someone's resume would be a second copy of the thing this feature
takes care never to retain — outliving the import, the evidence and the
deletion guarantees alike.
"""

import json
import logging

from app.core.logging import JsonFormatter


def _formatted(**extra) -> dict:
    record = logging.LogRecord(
        "app.imports", logging.INFO, __file__, 1, "import completed", None, None
    )
    record.__dict__.update(extra)
    return json.loads(JsonFormatter().format(record))


def test_outcomes_are_recorded():
    line = _formatted(profile_id="abc", count=3, outcome="completed")

    assert line["profile_id"] == "abc"
    assert line["count"] == "3"
    assert line["outcome"] == "completed"


def test_document_text_is_dropped():
    line = _formatted(
        profile_id="abc",
        source_text="Software Engineer, Example Corp. Visa: Example category.",
        quote="Software Engineer",
        filename="application-to-Example-Corp.pdf",
        payload={"employer_name": "Example Corp"},
    )

    serialised = json.dumps(line)
    assert "Example Corp" not in serialised
    assert "Visa" not in serialised
    assert "application-to" not in serialised


def test_a_filename_never_reaches_a_log():
    """It can reveal where someone was applying (FR-019b)."""
    line = _formatted(profile_id="abc", filename="resume_for_SomeCompany.pdf")
    assert "SomeCompany" not in json.dumps(line)
