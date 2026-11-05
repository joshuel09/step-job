"""Dates as an English resume writes them, and the era table out of reach.

Two kinds of test here, and the second is the one that matters.

The first kind checks output: `Mar 2021 – Present`, month precision, no era
name anywhere. Useful, and it can only ever check the cases someone thought
to write down.

The second checks the shape: `app/documents/dates.py` imports nothing from
`app/imports/dates.py`, where the era table lives. That is what makes "no
era can reach this document" a property rather than a hope — the renderer
cannot forget to pass `era=False` to a function it has no way to call.
"""

import re
from datetime import date
from pathlib import Path

import pytest
from app.documents import dates
from app.documents.dates import PRESENT, format_month, format_period

from tests.unit.import_graph import reaches

APP = Path(__file__).resolve().parents[2] / "app"

#: Written out here rather than read from the module under test. Comparing
#: `MONTHS[n]` against `MONTHS[n]` passes whichever name is in the table,
#: including a wrong one for a month nobody looked at.
EXPECTED = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

ERA_NAMES = ("令和", "平成", "昭和", "大正", "明治")

#: Kana and Han. A period is English typography — it carries an en dash, so
#: `isascii()` is the wrong question; what must not appear is Japanese.
JAPANESE = re.compile(r"[ぁ-んァ-ン一-龯]")


class TestAPeriod:
    def test_an_ongoing_role_reads_as_present(self):
        assert format_period(date(2021, 3, 1), None) == "Mar 2021 – Present"

    def test_a_finished_role_reads_as_two_months(self):
        assert format_period(date(2021, 3, 1), date(2024, 12, 31)) == "Mar 2021 – Dec 2024"

    def test_the_separator_is_an_en_dash(self):
        """Not a hyphen. A date range takes an en dash in English
        typography, and a resume is read by people who notice."""
        assert "–" in format_period(date(2021, 3, 1), None)
        assert "-" not in format_period(date(2021, 3, 1), None)

    def test_an_entry_with_no_dates_at_all_is_empty(self):
        """Rather than a bare dash. The renderer omits an empty period; it
        would have to special-case " – " otherwise."""
        assert format_period(None, None) == ""

    def test_an_entry_with_only_an_end_gives_the_end(self):
        """A missing start is a gap in the profile, not something to invent."""
        assert format_period(None, date(2024, 12, 31)) == "Dec 2024"


class TestPrecision:
    @pytest.mark.parametrize("day", [1, 9, 15, 28, 31])
    def test_the_day_never_appears(self, day):
        """Month precision always. A day-precision start date is both
        unconventional on a resume and more than most profiles honestly
        hold (R-006)."""
        assert format_month(date(2021, 3, day)) == "Mar 2021"

    @pytest.mark.parametrize(("month", "name"), sorted(EXPECTED.items()))
    def test_every_month_has_the_right_name(self, month, name):
        """Against a literal, not against the table. September is the one
        that goes wrong — "Sept" is four letters and wrong, and a test
        reading the name out of the module would agree with it."""
        rendered = format_month(date(2021, month, 1))
        assert rendered == f"{name} 2021"
        assert rendered.isascii()


class TestNoEraCanAppear:
    @pytest.mark.parametrize("month", range(1, 13))
    def test_not_in_any_month_of_a_year_that_straddles_a_changeover(self, month):
        """2019 was both 平成31年 and 令和元年 depending on the day, which is
        the year an era-aware formatter is most likely to reach for."""
        rendered = format_period(date(2019, month, 1), date(2019, month, 28))
        assert not any(era in rendered for era in ERA_NAMES), rendered
        assert not JAPANESE.search(rendered), rendered

    @pytest.mark.parametrize("year", [1988, 1989, 2018, 2019, 2024])
    def test_not_for_any_year_an_era_boundary_falls_in(self, year):
        rendered = format_period(date(year, 1, 1), None)
        assert not any(era in rendered for era in ERA_NAMES), rendered

    def test_the_module_holds_no_era_name_of_its_own(self):
        """A table copied here rather than imported would pass the import
        test below and fail the user just the same."""
        source = Path(dates.__file__).read_text()
        code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
        body = code.split('"""', 2)[-1] if code.count('"""') >= 2 else code
        assert not any(era in body for era in ERA_NAMES), "an era name is in the code"


class TestTheEraTableIsUnreachable:
    """The structural half, and the reason T026 overrode R-006's arrangement.

    R-006 asked for the Western formatter to sit beside `year_to_era` so a
    reader of either would see the other. The era table stayed in
    `app/imports/dates.py`, where features 003 and 004 read it from — so
    "beside" would have meant "importable", and the operative half of that
    decision was "the era table it must never consult".
    """

    def test_it_imports_nothing_from_the_module_holding_the_eras(self):
        """The walk itself lives in `tests/unit/import_graph.py` and is
        checked by `test_import_graph.py` against every form of import,
        including `from ..imports.dates import year_to_era` — which a walk
        that reads `node.module` and stops sees as `imports.dates` and
        quietly lets through."""
        reached = reaches(Path(dates.__file__), "app.imports", root=APP)
        assert not reached, f"the era table is reachable from the English formatter: {reached}"

    def test_the_era_formatter_is_still_where_the_japanese_documents_read_it(self):
        """So this test is about separation and not about deletion — the
        履歴書 and the 職務経歴書 still need it."""
        from app.imports.dates import year_to_era

        assert year_to_era(2021)[0] == "令和"

    def test_and_a_japanese_date_is_still_available_to_those_documents(self):
        from app.imports.dates import format_year_month

        assert "令和" in format_year_month(date(2021, 3, 1))


class TestWhatTheLocaleCannotChange:
    def test_the_month_names_do_not_come_from_strftime(self, monkeypatch):
        """`%b` is locale-dependent. Under a Japanese locale it returns 3月,
        which is the exact failure this module exists to prevent — and it
        would depend on which locale a server happened to boot in.
        """
        import time

        def explode(*args, **kwargs):
            raise AssertionError("the formatter reached for the C library")

        monkeypatch.setattr(time, "strftime", explode)
        assert format_month(date(2021, 3, 1)) == "Mar 2021"

    def test_present_is_a_word_and_not_a_blank(self):
        """An ongoing role says so. A blank would read as a missing date."""
        assert PRESENT == "Present"
