"""職務要約 — the opening summary, assembled from facts that can be counted.

The summary is built from the span of the career, the number of employers, and
the most recent role and employer. Nothing else (research.md R-003). Every
clause points at entries, which is what makes Principle IV hold here without
the evidence machinery feature 002 needed: there is no claim to evidence,
only arithmetic over what the user recorded.

What is deliberately absent is any characterising phrase — "experienced in",
"strong background in", 経験豊富. They read better and they are exactly what
the constitution forbids: the profile records that someone held a role, not
that they were good at it.

A profile too thin to summarise produces a shorter summary, or none. Saying
less is correct; reaching is not.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.imports.dates import format_year_month

# The whole fixed vocabulary of 職務要約, as templates. A test subtracts these,
# the user's own values and the dates, and asserts nothing is left — which is
# how a characterising word added later is caught, rather than by a word list
# that only knows the adjectives someone thought of.
SPAN = "職務経験年数　{years}年（{start}〜{end}）"
EMPLOYERS = "在籍企業数　{count}社"
LATEST = "直近の職務　{employer}　{role}"
TEMPLATES = (SPAN, EMPLOYERS, LATEST)

# How an ongoing role's end is written, matching 現在に至る in the 履歴書.
ONGOING = "現在"


@dataclass(frozen=True)
class Summary:
    """Countable facts about a career. No adjective, by construction.

    `span_years` is None where it cannot be counted — no employer has a start
    date — rather than zero, which would state something.
    """

    employer_count: int
    span_years: int | None = None
    earliest_start: date | None = None
    latest_end: date | None = None
    """The end of the span, or None where a role is ongoing and the span runs
    to the day the document was made."""
    latest_role: str | None = None
    latest_employer: str | None = None


def build_summary(experiences: Sequence[Any], *, today: date | None = None) -> Summary:
    """What can be counted from the employers a profile holds.

    `today` is a parameter rather than a call to the clock, so the span of an
    ongoing role can be tested without freezing time.
    """
    today = today or date.today()
    dated = sorted(
        (entry for entry in experiences if entry.started_on is not None),
        key=lambda entry: entry.started_on,
    )

    summary = Summary(employer_count=len(experiences))
    if not dated:
        return summary

    earliest = dated[0].started_on
    # An ongoing role runs to the day the document is made. Anything else ends
    # at the latest end the profile holds.
    ongoing = any(entry.ended_on is None for entry in dated)
    ends = [entry.ended_on for entry in dated if entry.ended_on is not None]
    latest_end = None if ongoing else max(ends, default=None)
    until = today if ongoing else latest_end

    recent = dated[-1]
    return Summary(
        employer_count=len(experiences),
        span_years=None if until is None else _years(earliest, until),
        earliest_start=earliest,
        latest_end=latest_end,
        latest_role=recent.job_title or None,
        latest_employer=recent.employer_name or None,
    )


def lines(summary: Summary, *, era: bool, today: date | None = None) -> list[str]:
    """The summary as the document writes it, one line per countable fact.

    A fact the profile does not hold produces no line at all. The alternative —
    a line with a blank where a number belongs — would read as a defect rather
    than as an absence.
    """
    today = today or date.today()
    written: list[str] = []

    if summary.span_years is not None and summary.earliest_start is not None:
        end = (
            ONGOING
            if summary.latest_end is None
            else format_year_month(summary.latest_end, era=era)
        )
        written.append(
            SPAN.format(
                years=summary.span_years,
                start=format_year_month(summary.earliest_start, era=era),
                end=end,
            )
        )

    if summary.employer_count:
        written.append(EMPLOYERS.format(count=summary.employer_count))

    if summary.latest_employer and summary.latest_role:
        written.append(LATEST.format(employer=summary.latest_employer, role=summary.latest_role))

    return written


def _years(start: date, end: date) -> int:
    """Whole years between two dates, never rounded up.

    A career of eleven months is nought years, not one. Rounding up would be
    the smallest possible overstatement, and it would still be one.
    """
    years = end.year - start.year - ((end.month, end.day) < (start.month, start.day))
    return max(years, 0)
