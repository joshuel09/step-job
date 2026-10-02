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

# First Gregorian year of each era. 令和 began in 1989 + 30; the arithmetic is
# (start_year + era_year - 1), so 令和3年 is 2018 + 3 = 2021.
ERAS: dict[str, int] = {
    "令和": 2018,
    "R": 2018,
    "平成": 1988,
    "H": 1988,
    "昭和": 1925,
    "S": 1925,
    "大正": 1911,
    "T": 1911,
    "明治": 1867,
    "M": 1867,
}

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
# one era table. Two copies would eventually disagree, and the disagreement
# would surface as a date that imports one way and prints another.

# Each era's first Gregorian year, newest first. An era applies from its start
# year onwards until the next one begins.
ERA_STARTS: list[tuple[str, int]] = [
    ("令和", 2019),
    ("平成", 1989),
    ("昭和", 1926),
    ("大正", 1912),
    ("明治", 1868),
]


def year_to_era(year: int) -> tuple[str, int]:
    """The era name and year for a calendar year.

    Boundary years are ambiguous — 2019 was both 平成31年 and 令和元年, depending
    on the month — and this returns the later era, which is what a document
    written now would use. A caller needing the month-accurate answer has the
    date and can decide; this function does not guess on their behalf.
    """
    for name, start in ERA_STARTS:
        if year >= start:
            return name, year - start + 1
    raise UnknownEraError(f"{year} predates the eras this table covers")


def format_japanese_date(value: date, *, era: bool = True) -> str:
    """Write a date the way a Japanese document does.

    With `era=False` this is 西暦 — a calendar year in Japanese form. With
    `era=True` it is 和暦. One convention is used throughout a document; mixing
    them within one is what FR-019 of feature 003 forbids.
    """
    if not era:
        return f"{value.year}年{value.month}月{value.day}日"

    name, era_year = year_to_era(value.year)
    # An era's first year is written 元年, never 1年.
    written = FIRST_YEAR if era_year == 1 else str(era_year)
    return f"{name}{written}年{value.month}月{value.day}日"


def format_year_month(value: date, *, era: bool = True) -> str:
    """The same, to month precision, as a 学歴・職歴 table uses."""
    if not era:
        return f"{value.year}年{value.month}月"

    name, era_year = year_to_era(value.year)
    written = FIRST_YEAR if era_year == 1 else str(era_year)
    return f"{name}{written}年{value.month}月"
