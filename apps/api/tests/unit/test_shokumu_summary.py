"""職務要約 says only what can be counted.

The summary is the one part of this document the product writes rather than
copies, which makes it the one place a characterising phrase could get in.
"Experienced in", "strong background in", 経験豊富 — they read better and they
are exactly what Principle IV forbids: the profile records that someone held a
role, not that they were good at it.

So the test below is subtractive rather than a list of banned adjectives. It
strips the module's own templates, the user's values and the dates, and
asserts nothing is left. A word list only catches the adjectives someone
thought of; this catches the next one.
"""

import re
import uuid
from datetime import date
from types import SimpleNamespace

import pytest
from app.imports.dates import format_year_month
from app.shokumu.summary import ONGOING, TEMPLATES, build_summary, lines

TODAY = date(2026, 10, 29)


def experience(employer: str, started: date | None, ended: date | None = None, title="エンジニア"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        employer_name=employer,
        job_title=title,
        started_on=started,
        ended_on=ended,
    )


# The whole of 職務要約, written out here rather than imported. The module's
# own TEMPLATES cannot be the oracle for a test about what the module is
# allowed to say: adding "として豊富な経験" to a template would then be
# subtracted as vocabulary and the test would pass on the adjective it exists
# to forbid. Changing the wording of the document is a deliberate act, and it
# fails here until it is made deliberately.
EXPECTED_TEMPLATES = (
    "職務経験年数　{years}年（{start}〜{end}）",
    "在籍企業数　{count}社",
    "直近の職務　{employer}　{role}",
)


def _fixed_vocabulary() -> list[str]:
    """Every literal fragment of the expected templates, longest first.

    Longest first so that stripping "年" does not leave the "職務経験年数"
    around it unmatched.
    """
    pieces = [
        piece
        for template in EXPECTED_TEMPLATES
        for piece in re.split(r"\{\w+\}", template)
        if piece
    ]
    return sorted(pieces, key=len, reverse=True)


def test_the_summary_says_only_what_this_file_expects_it_to():
    """The check that makes every test below mean something."""
    assert TEMPLATES == EXPECTED_TEMPLATES


class TestWhatIsCounted:
    def test_the_span_runs_from_the_earliest_start_to_the_latest_end(self):
        facts = build_summary(
            [
                experience("A", date(2013, 4, 1), date(2018, 3, 31)),
                experience("B", date(2018, 4, 1), date(2021, 3, 31)),
            ],
            today=TODAY,
        )
        assert facts.earliest_start == date(2013, 4, 1)
        assert facts.latest_end == date(2021, 3, 31)
        assert facts.span_years == 7

    def test_an_ongoing_role_runs_to_the_day_the_document_is_made(self):
        facts = build_summary([experience("A", date(2016, 10, 29))], today=TODAY)
        assert facts.latest_end is None
        assert facts.span_years == 10

    def test_a_part_year_is_never_rounded_up(self):
        """Eleven months is nought years. Rounding up is the smallest possible
        overstatement, and it is still one."""
        facts = build_summary([experience("A", date(2026, 1, 1), date(2026, 11, 30))], today=TODAY)
        assert facts.span_years == 0

    def test_the_employers_are_counted(self):
        facts = build_summary(
            [experience("A", date(2013, 4, 1)), experience("B", date(2018, 4, 1))], today=TODAY
        )
        assert facts.employer_count == 2

    def test_the_most_recent_role_is_the_one_that_started_last(self):
        facts = build_summary(
            [
                experience("古い会社", date(2013, 4, 1), date(2018, 3, 31), title="開発者"),
                experience("新しい会社", date(2018, 4, 1), title="主任"),
            ],
            today=TODAY,
        )
        assert facts.latest_employer == "新しい会社"
        assert facts.latest_role == "主任"


class TestAThinProfileSaysLess:
    def test_an_undated_employer_yields_no_span(self):
        facts = build_summary([experience("A", None)], today=TODAY)
        assert facts.span_years is None
        assert facts.employer_count == 1

    def test_and_the_summary_is_shorter_rather_than_reaching(self):
        written = lines(build_summary([experience("A", None)], today=TODAY), era=False)
        assert len(written) == 1
        assert "在籍企業数" in written[0]

    def test_a_profile_with_no_employer_says_nothing_at_all(self):
        assert lines(build_summary([], today=TODAY), era=False) == []


class TestItCharacterisesNobody:
    @pytest.fixture
    def facts(self):
        return build_summary(
            [
                experience("古い会社", date(2013, 4, 1), date(2018, 3, 31)),
                experience("株式会社サンプル", date(2018, 4, 1), title="主任エンジニア"),
            ],
            today=TODAY,
        )

    def test_nothing_remains_once_the_facts_are_subtracted(self, facts):
        """The test the word lists below cannot be: whatever is on the page is
        either a value from an entry, a date, or this module's own vocabulary.

        Subtracted in that order on purpose. The templates contribute single
        characters — 年, 社 — that also occur inside an employer's name, so
        taking the vocabulary out first would eat 株式会社サンプル from the
        inside and the test would pass on a document that said anything.
        """
        text = "".join(lines(facts, era=False, today=TODAY))

        # The user's values, longest first.
        for value in sorted(["株式会社サンプル", "主任エンジニア"], key=len, reverse=True):
            text = text.replace(value, "")

        # The dates, exactly as the document writes them.
        for when in (facts.earliest_start, facts.latest_end):
            if when is not None:
                text = text.replace(format_year_month(when, era=False), "")

        # The counts.
        text = re.sub(r"[0-9]+", "", text)

        # And only then this module's own fixed vocabulary.
        for piece in [*_fixed_vocabulary(), ONGOING]:
            text = text.replace(piece, "")

        assert text == "", f"unaccounted text in 職務要約: {text!r}"

    @pytest.mark.parametrize(
        "adjective",
        ["経験豊富", "優秀", "強み", "実績豊富", "幅広い", "experienced", "strong", "proven"],
    )
    def test_no_characterising_word_appears(self, facts, adjective):
        """A cheap second guard. The subtraction above is the real one."""
        written = " ".join(lines(facts, era=False, today=TODAY))
        assert adjective.lower() not in written.lower()

    def test_every_line_is_one_of_the_module_s_own_templates(self, facts):
        shapes = [re.escape(t) for t in EXPECTED_TEMPLATES]
        patterns = [re.compile(re.sub(r"\\\{\w+\\\}", ".+", s)) for s in shapes]

        for line in lines(facts, era=False, today=TODAY):
            assert any(p.fullmatch(line) for p in patterns), line


class TestTheConvention:
    def test_the_span_is_written_in_the_chosen_calendar(self):
        facts = build_summary([experience("A", date(2013, 4, 1), date(2018, 3, 31))], today=TODAY)

        seireki = lines(facts, era=False, today=TODAY)[0]
        wareki = lines(facts, era=True, today=TODAY)[0]

        assert "2013年4月" in seireki
        assert "平成25年4月" in wareki
        assert "2013" not in wareki, "one convention throughout (FR-009)"

    def test_an_ongoing_role_ends_at_現在_rather_than_a_date(self):
        facts = build_summary([experience("A", date(2020, 4, 1))], today=TODAY)
        assert "現在" in lines(facts, era=False, today=TODAY)[0]
