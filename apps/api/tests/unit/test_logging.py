"""Logs must record what happened, never the career data it happened to."""

import json
import logging

from app.core.logging import JsonFormatter


def _record(**extra) -> logging.LogRecord:
    record = logging.LogRecord("career", logging.INFO, __file__, 1, "entry deleted", None, None)
    record.__dict__.update(extra)
    return record


def test_safe_fields_are_recorded():
    line = json.loads(JsonFormatter().format(_record(profile_id="abc", section="experiences")))
    assert line["profile_id"] == "abc"
    assert line["section"] == "experiences"
    assert line["message"] == "entry deleted"


def test_career_content_is_dropped():
    """A log holding a user's career would be a second copy outliving deletion."""
    line = json.loads(
        JsonFormatter().format(
            _record(
                profile_id="abc",
                employer_name="Example Corp",
                description="Built internal services.",
                nationality="Example nationality",
                visa_type="Example visa",
            )
        )
    )

    assert "employer_name" not in line
    assert "description" not in line
    assert "nationality" not in line
    assert "visa_type" not in line
    assert "Example" not in json.dumps(line)
