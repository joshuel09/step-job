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
    format_japanese_date,
    format_year_month,
    normalise_dates,
    parse_japanese_date,
    year_to_era,
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


class TestYearToEra:
    """Rendering a calendar year as an era year — the reverse of parsing."""

    @pytest.mark.parametrize(
        ("year", "expected"),
        [
            (2024, ("令和", 6)),
            (2021, ("令和", 3)),
            (2019, ("令和", 1)),
            (2018, ("平成", 30)),
            (1989, ("平成", 1)),
            (1988, ("昭和", 63)),
            (1970, ("昭和", 45)),
            (1926, ("昭和", 1)),
            (1912, ("大正", 1)),
            (1868, ("明治", 1)),
        ],
    )
    def test_known_years_render(self, year, expected):
        assert year_to_era(year) == expected

    def test_a_boundary_year_renders_as_the_later_era(self):
        """2019 was both 平成31年 and 令和元年; a document written now says 令和."""
        assert year_to_era(2019) == ("令和", 1)

    def test_a_year_before_the_table_is_refused(self):
        with pytest.raises(UnknownEraError):
            year_to_era(1800)


class TestFormatting:
    def test_an_era_date(self):
        assert format_japanese_date(date(2021, 4, 1)) == "令和3年4月1日"

    def test_the_first_year_of_an_era_is_written_gannen(self):
        assert format_japanese_date(date(2019, 5, 1)) == "令和元年5月1日"

    def test_a_western_date_in_japanese_form(self):
        assert format_japanese_date(date(2021, 4, 1), era=False) == "2021年4月1日"

    def test_year_and_month_only(self):
        assert format_year_month(date(2021, 4, 1)) == "令和3年4月"
        assert format_year_month(date(2021, 4, 1), era=False) == "2021年4月"


class TestRoundTrip:
    """The reason both directions live in one module.

    Two copies of the era table would eventually disagree, and the disagreement
    would surface as a date that imports one way and prints another.
    """

    @pytest.mark.parametrize(
        "value",
        [
            date(2024, 3, 31),
            date(2021, 4, 1),
            date(2019, 5, 1),
            date(2018, 10, 15),
            date(1995, 7, 20),
            date(1970, 1, 1),
        ],
    )
    def test_rendering_then_parsing_returns_the_original(self, value):
        assert parse_japanese_date(format_japanese_date(value)) == value

    @pytest.mark.parametrize("value", [date(2024, 3, 1), date(2019, 5, 1), date(1988, 12, 1)])
    def test_year_and_month_round_trips_to_the_first_of_that_month(self, value):
        assert parse_japanese_date(format_year_month(value)) == value
