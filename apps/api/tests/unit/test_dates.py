"""Japanese era year conversion.

The boundary cases are the ones worth testing. An era's first year is written
元年 rather than 1年, and the year an era changes is the one where an off-by-one
becomes a resume that says someone worked somewhere a year longer than they did.
"""

from datetime import date

import pytest
from app.imports.dates import (
    UnknownEraError,
    era_to_year,
    normalise_dates,
    parse_japanese_date,
)


class TestEraToYear:
    @pytest.mark.parametrize(
        ("era", "era_year", "expected"),
        [
            ("令和", 1, 2019),
            ("令和", 3, 2021),
            ("令和", 6, 2024),
            ("平成", 1, 1989),
            ("平成", 31, 2019),
            ("昭和", 64, 1989),
            ("昭和", 45, 1970),
            ("大正", 1, 1912),
            ("明治", 1, 1868),
        ],
    )
    def test_known_eras_convert(self, era, era_year, expected):
        assert era_to_year(era, era_year) == expected

    def test_the_heisei_reiwa_boundary(self):
        """Both name 2019, which is correct — the era changed mid-year."""
        assert era_to_year("平成", 31) == era_to_year("令和", 1) == 2019

    def test_an_unknown_era_is_refused(self):
        # A wrong year changes how long someone appears to have worked
        # somewhere, so this fails rather than guesses.
        with pytest.raises(UnknownEraError):
            era_to_year("架空", 3)

    def test_a_zero_or_negative_era_year_is_refused(self):
        with pytest.raises(UnknownEraError):
            era_to_year("令和", 0)


class TestParseJapaneseDate:
    def test_a_full_era_date(self):
        assert parse_japanese_date("令和3年4月1日") == date(2021, 4, 1)

    def test_an_era_year_and_month(self):
        assert parse_japanese_date("令和3年4月") == date(2021, 4, 1)

    def test_an_era_year_alone(self):
        assert parse_japanese_date("令和3年") == date(2021, 1, 1)

    def test_the_first_year_of_an_era_is_written_gannen(self):
        assert parse_japanese_date("令和元年5月1日") == date(2019, 5, 1)

    def test_spacing_is_tolerated(self):
        assert parse_japanese_date("令和 3 年 4 月") == date(2021, 4, 1)

    def test_a_western_year_in_japanese_style(self):
        assert parse_japanese_date("2021年4月1日") == date(2021, 4, 1)

    def test_a_date_inside_a_sentence(self):
        assert parse_japanese_date("令和3年4月から勤務") == date(2021, 4, 1)

    def test_text_with_no_date_returns_nothing(self):
        assert parse_japanese_date("エンジニアとして勤務") is None

    def test_an_impossible_date_is_refused(self):
        with pytest.raises(UnknownEraError):
            parse_japanese_date("令和3年2月31日")

    def test_an_unknown_era_is_refused(self):
        assert parse_japanese_date("架空5年4月") is None


class TestNormaliseDates:
    def test_era_dates_become_calendar_dates(self):
        result = normalise_dates({"started_on": "令和3年4月", "ended_on": "令和6年3月"})

        assert result["started_on"] == "2021-04-01"
        assert result["ended_on"] == "2024-03-01"

    def test_calendar_dates_are_left_alone(self):
        result = normalise_dates({"started_on": "2021-04-01"})
        assert result["started_on"] == "2021-04-01"

    def test_an_unparseable_date_is_left_as_written(self):
        """The user sees what the document said and can correct it."""
        result = normalise_dates({"started_on": "sometime in spring"})
        assert result["started_on"] == "sometime in spring"

    def test_an_impossible_date_is_left_as_written(self):
        result = normalise_dates({"started_on": "令和3年2月31日"})
        assert result["started_on"] == "令和3年2月31日"

    def test_other_fields_are_untouched(self):
        result = normalise_dates({"employer_name": "サンプル株式会社", "started_on": "令和3年4月"})
        assert result["employer_name"] == "サンプル株式会社"

    def test_certification_dates_convert_too(self):
        result = normalise_dates({"issued_on": "平成30年10月", "expires_on": "令和5年10月"})
        assert result["issued_on"] == "2018-10-01"
        assert result["expires_on"] == "2023-10-01"
