"""Validation rules, tested at the boundaries that matter."""

from datetime import date

import pytest
from app.career.validation import check_date_range, check_salary_range, normalise_employer


class TestDateRange:
    def test_end_after_start_is_accepted(self):
        assert check_date_range(date(2021, 1, 1), date(2022, 1, 1)) == []

    def test_same_day_is_accepted(self):
        assert check_date_range(date(2021, 1, 1), date(2021, 1, 1)) == []

    def test_end_before_start_names_the_field(self):
        failures = check_date_range(date(2024, 1, 1), date(2023, 1, 1))
        assert failures == [("ended_on", "must be on or after started_on")]

    def test_missing_end_date_is_ongoing_not_invalid(self):
        assert check_date_range(date(2021, 1, 1), None) == []

    def test_field_names_are_configurable_for_other_sections(self):
        failures = check_date_range(
            date(2024, 1, 1),
            date(2023, 1, 1),
            start_field="issued_on",
            end_field="expires_on",
        )
        assert failures == [("expires_on", "must be on or after issued_on")]


class TestSalaryRange:
    def test_valid_range(self):
        assert check_salary_range(400, 600) == []

    def test_inverted_range_is_rejected(self):
        assert ("salary_max", "must be greater than or equal to salary_min") in check_salary_range(
            900, 500
        )

    def test_negative_values_are_rejected(self):
        assert ("salary_min", "must not be negative") in check_salary_range(-1, None)

    def test_open_ended_ranges_are_allowed(self):
        assert check_salary_range(500, None) == []
        assert check_salary_range(None, None) == []


class TestEmployerNormalisation:
    @pytest.mark.parametrize(
        ("left", "right"),
        [
            ("Example Corp", "Example Corp."),
            ("Example Inc", "EXAMPLE, Inc."),
            ("Example Ltd", "example limited"),
            ("株式会社Example", "Example"),
        ],
    )
    def test_the_same_employer_written_differently_still_matches(self, left, right):
        # Two sources routinely write one employer differently; duplicate
        # detection would miss the real case if this did not hold (R-004).
        assert normalise_employer(left) == normalise_employer(right)

    def test_different_employers_stay_distinct(self):
        assert normalise_employer("Example Corp") != normalise_employer("Other Corp")

    def test_a_name_made_only_of_suffixes_does_not_collapse_to_nothing(self):
        # Otherwise every such employer would match every other one.
        assert normalise_employer("Corp") != ""
