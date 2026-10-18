"""Converting Japanese era years to calendar dates.

Arithmetic against a published table, not a model task.

A date the model produced would have no passage behind it — the document says
令和3年4月, not 2021-04 — so it is precisely the case the evidence verifier is
built to reject. Converting deterministically keeps the original text as the
evidence, which means a user sees the document's own words beside the converted
date and can confirm it rather than trust it (FR-011, research.md R-007).

An unrecognised era fails visibly. A model asked to do this would produce a
confident wrong year instead, which is worse than an error because nothing
downstream would question it.
"""

import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

# The day each era began, newest first. An era applies from that day until the
# next one begins. Everything else here is derived from this list, so the two
# directions cannot name different years for the same era (#98).
#
# The day, not the year: eras change mid-year. 令和 began on 1 May 2019, so a
# graduation in March 2019 or a start on 1 April 2019 is 平成31年, and that is
# the most common pair of dates a Japanese career history holds. 明治 was
# proclaimed later in 1868 but applied from the first day of that year in the
# old calendar, which is 25 January in the Gregorian one.
ERA_STARTS: list[tuple[str, date]] = [
    ("令和", date(2019, 5, 1)),
    ("平成", date(1989, 1, 8)),
    ("昭和", date(1926, 12, 25)),
    ("大正", date(1912, 7, 30)),
    ("明治", date(1868, 1, 25)),
]

# The letters Japanese forms use for each era, as in H31年4月. Written out
# because there is nothing in the kanji to derive them from. A letter naming an
# era the table above does not hold raises KeyError at import, rather than
# parsing dates into an era that does not exist.
ERA_LETTERS: dict[str, str] = {
    "R": "令和",
    "H": "平成",
    "S": "昭和",
    "T": "大正",
    "M": "明治",
}

# The year before each era's first, which is what parsing adds the era year to:
# 令和3年 is 2018 + 3 = 2021. Derived, not written out. A second copy of the
# table would be a second place to remember when the era changes, and the two
# omissions are not equally visible — leaving an era out of this one is silent,
# and renders dates in the new era as years of the previous era (#98).
ERAS: dict[str, int] = {name: start.year - 1 for name, start in ERA_STARTS}
ERAS.update({letter: ERAS[name] for letter, name in ERA_LETTERS.items()})

# The first year of an era is written 元年 rather than 1年.
FIRST_YEAR = "元"

_ERA_NAMES = "|".join(re.escape(name) for name in ERAS)
ERA_DATE = re.compile(
    rf"(?P<era>{_ERA_NAMES})\s*(?P<year>{FIRST_YEAR}|\d{{1,2}})\s*年"
    rf"(?:\s*(?P<month>\d{{1,2}})\s*月)?"
    rf"(?:\s*(?P<day>\d{{1,2}})\s*日)?"
)

# Western dates as Japanese documents commonly write them.
WESTERN_DATE = re.compile(
    r"(?P<year>(?:19|20)\d{2})\s*年(?:\s*(?P<month>\d{1,2})\s*月)?(?:\s*(?P<day>\d{1,2})\s*日)?"
)


class UnknownEraError(ValueError):
    """An era this table does not cover.

    Raised rather than guessed. A wrong year in a resume is not a small error:
    it changes how long someone appears to have worked somewhere.
    """


def era_to_year(era: str, era_year: int) -> int:
    if era not in ERAS:
        raise UnknownEraError(f"Unrecognised era: {era!r}")
    if era_year < 1:
        raise UnknownEraError(f"Era years start at 1 or 元: got {era_year}")
    return ERAS[era] + era_year


def parse_japanese_date(text: str) -> date | None:
    """Return the first date in the text, at the precision it was written.

    A month without a day yields the first of that month, and a year alone the
    first of January, because the profile stores dates rather than partial
    dates. The original text remains as the evidence, so the precision the
    document actually used is never lost — it is visible beside the value
    (FR-009).
    """
    match = ERA_DATE.search(text)
    if match:
        era = match.group("era")
        raw_year = match.group("year")
        era_year = 1 if raw_year == FIRST_YEAR else int(raw_year)
        year = era_to_year(era, era_year)
    else:
        match = WESTERN_DATE.search(text)
        if not match:
            return None
        year = int(match.group("year"))

    month = int(match.group("month") or 1)
    day = int(match.group("day") or 1)

    try:
        return date(year, month, day)
    except ValueError as error:
        # A date the document states but that does not exist, such as 2月31日.
        # Reported rather than nudged to the nearest valid day.
        raise UnknownEraError(f"{text!r} is not a real date") from error


def normalise_dates(values: dict[str, str]) -> dict[str, str]:
    """Convert any Japanese date fields to calendar dates.

    Values already in calendar form are left alone. A value that cannot be
    parsed is left as it is rather than dropped: the user sees what the document
    said and can correct it, which is the same answer as for a contradiction.
    """
    converted = dict(values)

    for field in ("started_on", "ended_on", "issued_on", "expires_on"):
        raw = converted.get(field)
        if not raw or not isinstance(raw, str):
            continue
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            continue

        try:
            parsed = parse_japanese_date(raw)
        except UnknownEraError:
            logger.info("date left unconverted", extra={"entry_type": field})
            continue

        if parsed:
            converted[field] = parsed.isoformat()

    return converted


# --- the other direction -----------------------------------------------------
#
# Feature 003 renders calendar dates as era years for a 履歴書. It lives here,
# beside the parsing, rather than in that feature, so both directions share the
# one era table — `ERA_STARTS`, at the top of this module. Two copies would
# eventually disagree, and the disagreement would surface as a date that
# imports one way and prints another.


def date_to_era(value: date) -> tuple[str, int]:
    """The era name and year for a date.

    The era year counts from the era's first calendar year, so the year an era
    begins is its first year (元年) from its first day to 31 December, and
    the days before that day belong to the previous era's final year.
    """
    for name, start in ERA_STARTS:
        if value >= start:
            return name, value.year - start.year + 1
    raise UnknownEraError(f"{value.isoformat()} predates the eras this table covers")


def year_to_era(year: int) -> tuple[str, int]:
    """The era name and year for a calendar year alone.

    Boundary years are ambiguous — 2019 was both 平成31年 and 令和元年, depending
    on the month — and with no month to go on this returns the era the year
    ended in. Anything that has the date uses `date_to_era`, which is exact.
    """
    return date_to_era(date(year, 12, 31))


def format_japanese_date(value: date, *, era: bool = True) -> str:
    """Write a date the way a Japanese document does.

    With `era=False` this is 西暦 — a calendar year in Japanese form. With
    `era=True` it is 和暦. One convention is used throughout a document; mixing
    them within one is what FR-019 of feature 003 forbids.
    """
    if not era:
        return f"{value.year}年{value.month}月{value.day}日"

    name, era_year = date_to_era(value)
    # An era's first year is written 元年, never 1年.
    written = FIRST_YEAR if era_year == 1 else str(era_year)
    return f"{name}{written}年{value.month}月{value.day}日"


def format_year_month(value: date, *, era: bool = True) -> str:
    """The same, to month precision, as a 学歴・職歴 table uses."""
    if not era:
        return f"{value.year}年{value.month}月"

    name, era_year = date_to_era(value)
    written = FIRST_YEAR if era_year == 1 else str(era_year)
    return f"{name}{written}年{value.month}月"
