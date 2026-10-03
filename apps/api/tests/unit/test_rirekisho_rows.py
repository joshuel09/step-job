"""The 学歴・職歴 projection.

Tested exhaustively and without producing a document, which is the reason it is
a separate module. A mistake here is a wrong career history, not a layout slip.
"""

import uuid
from dataclasses import dataclass
from datetime import date

from app.rirekisho.rows import Row, RowEvent, build_rows


@dataclass
class FakeEducation:
    institution: str
    started_on: date | None
    ended_on: date | None = None
    id: uuid.UUID = None  # type: ignore[assignment]

    def __post_init__(self):
        self.id = self.id or uuid.uuid4()


@dataclass
class FakeExperience:
    employer_name: str
    started_on: date | None
    ended_on: date | None = None
    id: uuid.UUID = None  # type: ignore[assignment]

    def __post_init__(self):
        self.id = self.id or uuid.uuid4()


def _events(rows: list[Row]) -> list[RowEvent]:
    return [r.event for r in rows]


class TestOrdering:
    def test_education_comes_before_employment(self):
        """The convention, not a chronological claim: the job is older here."""
        rows = build_rows(
            [FakeEducation("サンプル大学", date(2015, 4, 1), date(2019, 3, 31))],
            [FakeExperience("株式会社サンプル", date(2010, 4, 1), date(2014, 3, 31))],
        )
        assert _events(rows) == [
            RowEvent.enrolled,
            RowEvent.graduated,
            RowEvent.joined,
            RowEvent.left,
            RowEvent.end,
        ]

    def test_oldest_first_within_employment(self):
        rows = build_rows(
            [],
            [
                FakeExperience("Second Corp", date(2021, 4, 1), date(2024, 3, 31)),
                FakeExperience("First Corp", date(2015, 4, 1), date(2021, 3, 31)),
            ],
        )
        joined = [r.institution for r in rows if r.event is RowEvent.joined]
        assert joined == ["First Corp", "Second Corp"]

    def test_oldest_first_within_education(self):
        rows = build_rows(
            [
                FakeEducation("Graduate School", date(2019, 4, 1), date(2021, 3, 31)),
                FakeEducation("Undergraduate", date(2015, 4, 1), date(2019, 3, 31)),
            ],
            [],
        )
        enrolled = [r.institution for r in rows if r.event is RowEvent.enrolled]
        assert enrolled == ["Undergraduate", "Graduate School"]

    def test_an_entry_with_no_start_date_is_placed_last_not_dropped(self):
        """It is still part of someone's history."""
        rows = build_rows(
            [],
            [
                FakeExperience("Undated Corp", None),
                FakeExperience("Dated Corp", date(2020, 1, 1)),
            ],
        )
        joined = [r.institution for r in rows if r.event is RowEvent.joined]
        assert joined == ["Dated Corp", "Undated Corp"]


class TestRowsPerEntry:
    def test_a_finished_role_produces_joining_and_leaving(self):
        rows = build_rows(
            [], [FakeExperience("株式会社サンプル", date(2013, 4, 1), date(2021, 3, 31))]
        )
        assert _events(rows) == [RowEvent.joined, RowEvent.left, RowEvent.end]

    def test_an_ongoing_role_reads_genzai_ni_itaru(self):
        """What the profile says. Correcting it is a profile edit (FR-009)."""
        rows = build_rows([], [FakeExperience("Example Corp", date(2021, 4, 1), None)])
        assert _events(rows) == [RowEvent.joined, RowEvent.ongoing, RowEvent.end]
        assert rows[1].date is None

    def test_completed_education_produces_entering_and_completing(self):
        rows = build_rows([FakeEducation("サンプル大学", date(2009, 4, 1), date(2013, 3, 31))], [])
        assert _events(rows) == [RowEvent.enrolled, RowEvent.graduated, RowEvent.end]

    def test_education_with_no_end_date_produces_only_entering(self):
        """Nothing is inferred about whether the course finished (FR-014)."""
        rows = build_rows([FakeEducation("サンプル大学", date(2023, 4, 1), None)], [])
        assert _events(rows) == [RowEvent.enrolled, RowEvent.end]


class TestOverlaps:
    def test_overlapping_roles_both_appear(self):
        """FR-011: not reconciled, reordered or omitted to look tidier."""
        rows = build_rows(
            [],
            [
                FakeExperience("Day Job", date(2020, 1, 1), date(2024, 1, 1)),
                FakeExperience("Contract Work", date(2021, 6, 1), date(2022, 6, 1)),
            ],
        )
        joined = [r.institution for r in rows if r.event is RowEvent.joined]
        assert joined == ["Day Job", "Contract Work"]
        assert len([r for r in rows if r.event is RowEvent.left]) == 2

    def test_two_ongoing_roles_both_appear(self):
        rows = build_rows(
            [],
            [
                FakeExperience("First Corp", date(2020, 1, 1), None),
                FakeExperience("Second Corp", date(2022, 1, 1), None),
            ],
        )
        assert len([r for r in rows if r.event is RowEvent.ongoing]) == 2

    def test_education_and_employment_overlapping_both_appear(self):
        rows = build_rows(
            [FakeEducation("Evening School", date(2020, 4, 1), date(2022, 3, 31))],
            [FakeExperience("Example Corp", date(2019, 4, 1), date(2024, 3, 31))],
        )
        assert RowEvent.enrolled in _events(rows)
        assert RowEvent.joined in _events(rows)


class TestClosing:
    def test_the_table_ends_with_ijou(self):
        rows = build_rows([], [FakeExperience("Example Corp", date(2020, 1, 1))])
        assert rows[-1].event is RowEvent.end

    def test_an_empty_history_still_ends_with_ijou(self):
        """A first-time applicant's 履歴書 is a legitimate document."""
        rows = build_rows([], [])
        assert _events(rows) == [RowEvent.end]

    def test_the_closing_row_names_no_entry(self):
        """以上 is a convention, not a claim about someone's career."""
        rows = build_rows([], [])
        assert rows[-1].source_entry_id is None


class TestTraceability:
    def test_every_substantive_row_names_the_entry_that_produced_it(self):
        """FR-012 and SC-008: any line can be traced to what it came from."""
        education = FakeEducation("サンプル大学", date(2009, 4, 1), date(2013, 3, 31))
        experience = FakeExperience("Example Corp", date(2013, 4, 1), None)

        rows = build_rows([education], [experience])

        for row in rows:
            if row.event is RowEvent.end:
                continue
            assert row.source_entry_id is not None, row.event

        education_rows = (RowEvent.enrolled, RowEvent.graduated)
        assert {r.source_entry_id for r in rows if r.event in education_rows} == {education.id}
        work_rows = (RowEvent.joined, RowEvent.ongoing)
        assert {r.source_entry_id for r in rows if r.event in work_rows} == {experience.id}

    def test_rows_carry_no_content_the_entries_did_not_have(self):
        """Nothing invented to fill a row (FR-013)."""
        rows = build_rows([], [FakeExperience("Example Corp", date(2020, 1, 1), None)])
        institutions = {r.institution for r in rows if r.institution}
        assert institutions == {"Example Corp"}
