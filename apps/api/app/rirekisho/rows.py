"""The 学歴・職歴 table.

A pure function from a profile's education and work entries to an ordered list
of rows. It knows nothing about PDFs, so every convention below can be tested
exhaustively without producing a document — which is the difference between
testing the rules and testing a picture of them.

The conventions are not decoration. A 履歴書 read by a Japanese employer is
expected to put education before employment, oldest first within each, one row
for entering and one for leaving, and 以上 at the end. Getting the order wrong
does not look like a formatting slip; it looks like someone who has not written
one before.
"""

import enum
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol


class RowEvent(enum.StrEnum):
    """What a row records."""

    enrolled = "入学"
    graduated = "卒業"
    joined = "入社"
    left = "退社"
    ongoing = "現在に至る"
    end = "以上"


@dataclass(frozen=True)
class Row:
    """One line of the combined table."""

    date: date | None
    institution: str
    event: RowEvent
    source_entry_id: uuid.UUID | None = None
    """Which profile entry produced this row.

    What makes FR-012 checkable: for any line in the document, the entry behind
    it can be named. The closing row has none, because 以上 is a convention
    rather than a claim about someone's career.
    """


class _Education(Protocol):
    id: uuid.UUID
    institution: str
    started_on: date | None
    ended_on: date | None


class _Experience(Protocol):
    id: uuid.UUID
    employer_name: str
    started_on: date
    ended_on: date | None


def _by_start(entry: Any) -> tuple[int, date]:
    """Sort oldest first, with undated entries last rather than dropped.

    An entry whose start date the profile does not hold is still part of
    someone's history. Discarding it to make sorting easy would lose career
    the user entered.
    """
    started = getattr(entry, "started_on", None)
    return (1, date.max) if started is None else (0, started)


def build_rows(
    education: list[_Education],
    experiences: list[_Experience],
) -> list[Row]:
    """The whole table, in the order a 履歴書 expects it."""
    rows: list[Row] = []

    # Education first, whatever the dates say. This is the convention, not a
    # chronological claim (FR-006).
    for entry in sorted(education, key=_by_start):
        rows.append(
            Row(
                date=entry.started_on,
                institution=entry.institution,
                event=RowEvent.enrolled,
                source_entry_id=entry.id,
            )
        )
        # No completing row without an end date. Nothing is inferred about
        # whether the course finished (FR-014).
        if entry.ended_on is not None:
            rows.append(
                Row(
                    date=entry.ended_on,
                    institution=entry.institution,
                    event=RowEvent.graduated,
                    source_entry_id=entry.id,
                )
            )

    # Then employment. Overlapping roles both appear, in start order: the system
    # does not reconcile, reorder or omit either to make a history look tidier
    # (FR-011).
    for entry in sorted(experiences, key=_by_start):
        rows.append(
            Row(
                date=entry.started_on,
                institution=entry.employer_name,
                event=RowEvent.joined,
                source_entry_id=entry.id,
            )
        )
        if entry.ended_on is not None:
            rows.append(
                Row(
                    date=entry.ended_on,
                    institution=entry.employer_name,
                    event=RowEvent.left,
                    source_entry_id=entry.id,
                )
            )
        else:
            # A role still held reads 現在に至る rather than a date (FR-009).
            # This is what the profile says; correcting it is a profile edit.
            rows.append(
                Row(
                    date=None,
                    institution="",
                    event=RowEvent.ongoing,
                    source_entry_id=entry.id,
                )
            )

    # Always, including when the table is otherwise empty — a first-time
    # applicant's 履歴書 is a legitimate document (FR-010).
    rows.append(Row(date=None, institution="", event=RowEvent.end))
    return rows
