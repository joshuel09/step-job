"""Duplicate detection.

Clarification Q4: the same employer with overlapping dates, regardless of how
the title is worded. Both halves of that matter — too strict and a user who
imports after typing sees everything twice; too loose and a promotion is
silently merged into the role it followed, destroying real career history.
"""

from datetime import date

import pytest
from app.career.duplicates import ranges_overlap


class TestRangeOverlap:
    def test_identical_ranges_overlap(self):
        assert ranges_overlap(
            date(2021, 1, 1), date(2022, 1, 1), date(2021, 1, 1), date(2022, 1, 1)
        )

    def test_partial_overlap(self):
        assert ranges_overlap(
            date(2021, 1, 1), date(2022, 6, 1), date(2022, 1, 1), date(2023, 1, 1)
        )

    def test_touching_at_a_single_day_overlaps(self):
        assert ranges_overlap(
            date(2021, 1, 1), date(2022, 1, 1), date(2022, 1, 1), date(2023, 1, 1)
        )

    def test_a_gap_does_not_overlap(self):
        # A promotion or a return years later. Merging these would be wrong.
        assert not ranges_overlap(
            date(2019, 1, 1), date(2020, 1, 1), date(2022, 1, 1), date(2023, 1, 1)
        )

    def test_an_ongoing_role_extends_to_the_present(self):
        # Without this, a current role could never match anything.
        assert ranges_overlap(date(2021, 1, 1), None, date(2024, 1, 1), date(2025, 1, 1))

    def test_two_ongoing_roles_overlap(self):
        assert ranges_overlap(date(2021, 1, 1), None, date(2023, 1, 1), None)

    def test_an_ongoing_role_does_not_reach_backwards(self):
        assert not ranges_overlap(
            date(2024, 1, 1), None, date(2019, 1, 1), date(2020, 1, 1)
        )


@pytest.mark.parametrize(
    ("proposed", "existing", "should_match"),
    [
        ("Example Corp", "Example Corp.", True),
        ("Example Inc", "EXAMPLE, Inc.", True),
        ("株式会社Example", "Example", True),
        ("Example Corp", "Other Corp", False),
    ],
)
def test_employer_normalisation_drives_matching(proposed, existing, should_match):
    from app.career.validation import normalise_employer

    assert (normalise_employer(proposed) == normalise_employer(existing)) is should_match
