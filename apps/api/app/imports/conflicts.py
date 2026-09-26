"""Detecting where a source disagrees with itself.

Real resumes contain mistakes, especially ones edited over years. A role that
ends before it starts, or the same job given two different date ranges, is
common enough that the feature has to have an answer.

The answer is to say so and stop. Choosing the likelier reading would mean the
system deciding what someone's career was rather than reporting what their
document says — which is the fabrication Principle IV forbids, wearing a helpful
face (FR-012b). The user knows which date is wrong. This module does not.
"""

import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def detect(values: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the disagreements in one entry's values.

    Each conflict names the fields that disagree and says why, so the interface
    can point at the offending inputs rather than reporting that something,
    somewhere, is wrong.
    """
    conflicts: list[dict[str, Any]] = []

    started = _as_date(values.get("started_on"))
    ended = _as_date(values.get("ended_on"))
    if started and ended and ended < started:
        conflicts.append(
            {
                "fields": ["started_on", "ended_on"],
                "reason": "the end date is earlier than the start date",
            }
        )

    issued = _as_date(values.get("issued_on"))
    expires = _as_date(values.get("expires_on"))
    if issued and expires and expires < issued:
        conflicts.append(
            {
                "fields": ["issued_on", "expires_on"],
                "reason": "the expiry date is earlier than the issue date",
            }
        )

    if conflicts:
        logger.info("conflicts flagged", extra={"count": len(conflicts)})

    return conflicts


def detect_across(entries: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    """Find entries that describe the same role with different dates.

    Flagged on both entries, not merged: two spells at one employer may be a
    genuine promotion, and this module cannot tell that from a typo.
    """
    found: dict[int, list[dict[str, Any]]] = {}
    by_employer: dict[str, list[int]] = {}

    for index, values in enumerate(entries):
        employer = str(values.get("employer_name") or "").strip().casefold()
        if employer:
            by_employer.setdefault(employer, []).append(index)

    for indices in by_employer.values():
        if len(indices) < 2:
            continue

        ranges = {
            index: (_as_date(entries[index].get("started_on")), entries[index].get("job_title"))
            for index in indices
        }
        starts = {start for start, _ in ranges.values() if start}

        # Same employer, same job title, different start dates: one role
        # described twice with dates that disagree.
        titles = {title for _, title in ranges.values() if title}
        if len(titles) == 1 and len(starts) > 1:
            for index in indices:
                found.setdefault(index, []).append(
                    {
                        "fields": ["started_on"],
                        "reason": (
                            "this role appears more than once in the document "
                            "with different start dates"
                        ),
                    }
                )

    return found
