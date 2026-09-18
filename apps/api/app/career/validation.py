"""Field-level validation.

FR-014 requires a rejection to name the offending field and explain why, so the
interface can show the reason rather than a generic failure. Every function here
returns failures rather than raising, so a request reports everything wrong with
it at once instead of one problem per round trip.
"""

from datetime import date

Failure = tuple[str, str]


def check_date_range(
    started_on: date | None,
    ended_on: date | None,
    *,
    start_field: str = "started_on",
    end_field: str = "ended_on",
) -> list[Failure]:
    """An end date must not precede its start date.

    A missing end date is valid and means ongoing; it is not an error.
    """
    if started_on is None or ended_on is None:
        return []
    if ended_on < started_on:
        return [(end_field, f"must be on or after {start_field}")]
    return []


def check_salary_range(salary_min: int | None, salary_max: int | None) -> list[Failure]:
    failures: list[Failure] = []
    for field, value in (("salary_min", salary_min), ("salary_max", salary_max)):
        if value is not None and value < 0:
            failures.append((field, "must not be negative"))
    if salary_min is not None and salary_max is not None and salary_max < salary_min:
        failures.append(("salary_max", "must be greater than or equal to salary_min"))
    return failures


def normalise_employer(name: str) -> str:
    """Reduce an employer name to a comparable form.

    Two sources routinely write the same employer differently — one uses the
    legal entity, the other the trading name. Duplicate detection compares this
    form so a trailing "Inc." does not hide a genuine duplicate (research.md
    R-004). Never shown to the user.

    Japanese company markers are handled separately from the Latin ones because
    they are normally written against the name with no space, so word splitting
    alone would never find them.
    """
    JAPANESE_MARKERS = ("株式会社", "有限会社", "合同会社", "合資会社")
    LATIN_SUFFIXES = {
        "inc",
        "llc",
        "ltd",
        "limited",
        "corp",
        "corporation",
        "co",
        "company",
        "gmbh",
        "kk",
        "sa",
        "ag",
        "pte",
        "plc",
    }

    cleaned = name
    for marker in JAPANESE_MARKERS:
        cleaned = cleaned.replace(marker, " ")

    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in cleaned.lower())
    words = cleaned.split()
    kept = [w for w in words if w not in LATIN_SUFFIXES]

    # A name made entirely of suffix words keeps its original words rather than
    # normalising to nothing, which would make every such employer match.
    return "".join(kept or words)
