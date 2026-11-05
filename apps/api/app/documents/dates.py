"""Dates as an English resume writes them.

`Mar 2021 – Present`, to month precision, with an en dash. Never a day: a
day-precision start date is both unconventional on a resume and more than
most profiles honestly hold (R-006).

**This module imports nothing from `app/imports/dates.py`,** and that is the
point of it rather than an accident of layout. That module holds the era
table — 令和, 平成, 昭和 — which the 履歴書 and the 職務経歴書 read and this
document must never show. The guarantee that no era can reach an English
resume is not that the renderer remembers to pass `era=False`; it is that
the only date function this document can reach has no era table behind it.

R-006 asked for the two formatters to sit together so that a reader of
either would see the other, and that is not what happened: the era table
stayed in `app/imports/dates.py` where features 003 and 004 read it from.
Between an arrangement that reads well and a rule a test can enforce, the
rule wins — and "beside the era table it must never consult" was the
operative half of that decision anyway. `tests/unit/test_resume_dates.py`
walks this module's imports and fails if `app.imports` appears among them.
"""

from datetime import date

#: Abbreviated month names, written out rather than taken from the C library.
#: `strftime("%b")` is locale-dependent: under a Japanese locale it can return
#: 3月, which is precisely the failure this module exists to prevent, and it
#: would depend on the environment a server happens to boot in.
MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)

#: What an ongoing role reads as. The profile records `ended_on = None`,
#: which means the role continues — never that the date is unknown.
PRESENT = "Present"

#: An en dash, as a date range takes in English typography. Not a hyphen.
RANGE_SEPARATOR = " – "


def format_month(value: date) -> str:
    """`Mar 2021`. The day is dropped, deliberately and always."""
    return f"{MONTHS[value.month - 1]} {value.year}"


def format_period(started_on: date | None, ended_on: date | None) -> str:
    """`Mar 2021 – Present`, or as much of it as the profile holds.

    A missing start is a gap in the profile rather than something to invent,
    so it produces the end alone — and an entry with neither produces an
    empty string, which the renderer omits rather than printing a bare dash.
    """
    if started_on is None and ended_on is None:
        return ""
    if started_on is None:
        return format_month(ended_on)  # type: ignore[arg-type]

    end = format_month(ended_on) if ended_on else PRESENT
    return f"{format_month(started_on)}{RANGE_SEPARATOR}{end}"
