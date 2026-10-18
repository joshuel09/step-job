"""Japanese era year conversion.

The boundary cases are the ones worth testing. An era's first year is written
元年 rather than 1年, and the year an era changes is the one where an off-by-one
becomes a resume that says someone worked somewhere a year longer than they did.
"""

from datetime import date

import pytest
from app.imports.dates import (
    ALIASES,
    ERA_STARTS,
    ERAS,
    UnknownEraError,
    date_to_era,
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


class TestDateToEra:
    """Eras change mid-year, so the era of a date depends on the day (#76).

    Each changeover is tested on both sides. The last day of an era and the
    first day of the next are a day apart and a whole era apart.
    """

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            # 平成 → 令和 on 1 May 2019.
            (date(2019, 4, 30), ("平成", 31)),
            (date(2019, 5, 1), ("令和", 1)),
            # 昭和 → 平成 on 8 January 1989.
            (date(1989, 1, 7), ("昭和", 64)),
            (date(1989, 1, 8), ("平成", 1)),
            # 大正 → 昭和 on 25 December 1926.
            (date(1926, 12, 24), ("大正", 15)),
            (date(1926, 12, 25), ("昭和", 1)),
            # 明治 → 大正 on 30 July 1912.
            (date(1912, 7, 29), ("明治", 45)),
            (date(1912, 7, 30), ("大正", 1)),
        ],
    )
    def test_each_changeover_on_both_sides(self, value, expected):
        assert date_to_era(value) == expected

    def test_the_rest_of_the_first_year_stays_gannen(self):
        assert date_to_era(date(2019, 12, 31)) == ("令和", 1)
        assert date_to_era(date(2020, 1, 1)) == ("令和", 2)

    def test_a_date_before_the_table_is_refused(self):
        with pytest.raises(UnknownEraError):
            date_to_era(date(1868, 1, 24))


class TestTheSpring2019Cohort:
    """The case users will actually hit.

    The Japanese academic and fiscal year ends on 31 March and begins on
    1 April. Everyone who graduated in March 2019 or started work on 1 April
    2019 did so in 平成, a month before 令和 began.
    """

    def test_a_1_april_2019_start_is_heisei_31(self):
        assert format_year_month(date(2019, 4, 1)) == "平成31年4月"
        assert format_japanese_date(date(2019, 4, 1)) == "平成31年4月1日"

    def test_a_march_2019_graduation_is_heisei_31(self):
        assert format_year_month(date(2019, 3, 31)) == "平成31年3月"
        assert format_japanese_date(date(2019, 3, 31)) == "平成31年3月31日"

    def test_may_2019_is_reiwa_gannen(self):
        assert format_year_month(date(2019, 5, 1)) == "令和元年5月"

    def test_early_january_1989_is_showa_64(self):
        assert format_japanese_date(date(1989, 1, 5)) == "昭和64年1月5日"
        assert format_japanese_date(date(1989, 1, 8)) == "平成元年1月8日"


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


class TestTheErasAreOneTable:
    """Both directions read one list of eras (#98).

    `ERAS`, which parsing adds the era year to, is derived from `ERA_STARTS`
    rather than written out beside it. These tests read `ERA_STARTS` and check
    what the rest of the module does with each entry, so they cover whatever
    that list holds rather than the five eras it holds today. The next
    changeover is the one moment this table is certain to be edited, probably
    in a hurry.

    The two halves of a half-added era were not equally visible. Parsing an era
    the table lacks returns nothing and the entry is left for the user to
    correct — the module's refuse-rather-than-guess rule. Rendering a date in
    that era wrote it as a year of the previous era with no error anywhere,
    which is the shape of #76.
    """

    @pytest.mark.parametrize(("name", "start"), ERA_STARTS)
    def test_each_era_parses_from_its_first_day(self, name, start):
        assert parse_japanese_date(f"{name}元年{start.month}月{start.day}日") == start

    @pytest.mark.parametrize(("name", "start"), ERA_STARTS)
    def test_each_era_renders_on_its_first_day(self, name, start):
        assert format_japanese_date(start) == f"{name}元年{start.month}月{start.day}日"

    # The letters, written out here rather than read from the module. They are
    # the one thing on this page that cannot be derived from anything, so a
    # change to them has to be made twice to pass: once in the code and once
    # where a reviewer reads it.
    LETTERS = {"R": "令和", "H": "平成", "S": "昭和", "T": "大正", "M": "明治"}

    def test_each_letter_stands_for_the_era_a_form_means_by_it(self):
        assert ALIASES == self.LETTERS

    @pytest.mark.parametrize(
        ("written", "expected"),
        [
            ("R3年4月", date(2021, 4, 1)),
            ("H3年4月", date(1991, 4, 1)),
            ("S3年4月", date(1928, 4, 1)),
            ("T3年4月", date(1914, 4, 1)),
            ("M3年4月", date(1870, 4, 1)),
        ],
    )
    def test_a_letter_parses_to_the_year_it_names(self, written, expected):
        """Against a year written out, not against the kanji form.

        Comparing the two forms would pass whatever the letters pointed at,
        since both sides read the same derived table.
        """
        assert parse_japanese_date(written) == expected

    def test_every_era_has_a_letter(self):
        """A new era should parse in the letter form too, as the others do."""
        assert set(ALIASES.values()) == {name for name, _ in ERA_STARTS}

    def test_the_parse_table_holds_the_eras_and_their_letters_and_nothing_else(self):
        assert set(ERAS) == {name for name, _ in ERA_STARTS} | set(ALIASES)


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
            # Either side of a changeover. The wrong era round-trips too, since
            # both directions share the table, so these guard the parsing side
            # of #76's fix rather than detect the original bug.
            date(2019, 4, 1),
            date(2019, 4, 30),
            date(1989, 1, 7),
            date(1989, 1, 8),
        ],
    )
    def test_rendering_then_parsing_returns_the_original(self, value):
        assert parse_japanese_date(format_japanese_date(value)) == value

    @pytest.mark.parametrize("value", [date(2024, 3, 1), date(2019, 5, 1), date(1988, 12, 1)])
    def test_year_and_month_round_trips_to_the_first_of_that_month(self, value):
        assert parse_japanese_date(format_year_month(value)) == value
