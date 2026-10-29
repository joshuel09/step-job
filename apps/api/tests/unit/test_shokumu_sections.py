"""The 職務経歴書's projection, tested without producing a document.

`sections.build_history` is a pure function from entries to an ordered
structure, which is what makes these exhaustive: every ordering rule, every
grouping rule and every "nothing is dropped" guarantee can be checked here,
leaving the integration tests to prove the result reaches the page.

The conventions are not decoration. An employer section missing its
achievements, or an achievement filed under the wrong employer, is a document
that misrepresents someone's career to the person deciding whether to hire
them.
"""

import uuid
from datetime import date
from types import SimpleNamespace

import pytest
from app.shokumu.sections import build_history


def experience(employer: str, started: date | None, ended: date | None = None, **extra):
    return SimpleNamespace(
        id=uuid.uuid4(),
        employer_name=employer,
        job_title=extra.get("job_title", "エンジニア"),
        employment_type=extra.get("employment_type"),
        started_on=started,
        ended_on=ended,
        description=extra.get("description", ""),
    )


def story(title: str, employer_id: uuid.UUID | None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        work_experience_id=employer_id,
        title=title,
        challenge="課題",
        action="対応",
        result="結果",
    )


@pytest.fixture
def two_employers():
    return [
        experience("古い会社", date(2013, 4, 1), date(2018, 3, 31)),
        experience("新しい会社", date(2018, 4, 1)),
    ]


class TestOneSectionPerEmployer:
    def test_every_employer_gets_a_section(self, two_employers):
        history = build_history(two_employers)
        assert {s.employer for s in history.sections} == {"古い会社", "新しい会社"}

    def test_a_section_carries_what_the_profile_holds(self):
        entry = experience(
            "株式会社サンプル",
            date(2020, 1, 1),
            employment_type="permanent",
            description="社内システムの開発。",
        )
        [section] = build_history([entry]).sections

        assert section.job_title == "エンジニア"
        assert section.employment_type == "permanent"
        assert section.description == "社内システムの開発。"
        assert section.source_entry_id == entry.id

    def test_an_ongoing_role_keeps_its_open_end(self):
        [section] = build_history([experience("現職", date(2021, 4, 1))]).sections
        assert section.ended_on is None, "ongoing, not unknown"

    def test_overlapping_employment_is_left_unreconciled(self):
        """Concurrent roles are legitimate; the document does not tidy them away."""
        history = build_history(
            [
                experience("本業", date(2020, 1, 1), date(2023, 1, 1)),
                experience("副業", date(2021, 1, 1), date(2022, 1, 1)),
            ]
        )
        assert len(history.sections) == 2


class TestTheArrangement:
    def test_newest_first_by_default(self, two_employers):
        history = build_history(two_employers)
        assert [s.employer for s in history.sections] == ["新しい会社", "古い会社"]

    def test_oldest_first_when_asked(self, two_employers):
        history = build_history(two_employers, newest_first=False)
        assert [s.employer for s in history.sections] == ["古い会社", "新しい会社"]

    @pytest.mark.parametrize("newest_first", [True, False])
    def test_both_arrangements_carry_the_same_entries(self, two_employers, newest_first):
        """FR-008: only the order differs — nothing gained, lost or merged."""
        one = build_history(two_employers, newest_first=True)
        other = build_history(two_employers, newest_first=False)

        assert sorted(one.entry_ids(), key=str) == sorted(other.entry_ids(), key=str)
        assert len(one.sections) == len(other.sections) == 2

    def test_an_undated_employer_sorts_last_in_both_arrangements(self, two_employers):
        """It is still part of someone's history, so it is placed, not dropped.

        Unreachable through the ORM — `WorkExperience.started_on` is not
        nullable — which is exactly why it is pinned here: the rule holds at
        the only level where the case can exist, as `rows.py` established.
        """
        entries = [*two_employers, experience("日付のない会社", None)]

        for newest_first in (True, False):
            history = build_history(entries, newest_first=newest_first)
            assert history.sections[-1].employer == "日付のない会社"


class TestAchievements:
    def test_a_story_lands_under_the_employer_it_was_recorded_against(self, two_employers):
        old, new = two_employers
        history = build_history(two_employers, [story("古い実績", old.id)])

        by_employer = {s.employer: s for s in history.sections}
        assert [a.title for a in by_employer["古い会社"].achievements] == ["古い実績"]
        assert by_employer["新しい会社"].achievements == ()

    def test_recorded_order_is_kept(self, two_employers):
        """The profile does not rank achievements and neither does this."""
        employer = two_employers[0]
        stories = [story("ひとつめ", employer.id), story("ふたつめ", employer.id)]

        history = build_history(two_employers, stories)
        [section] = [s for s in history.sections if s.employer == "古い会社"]
        assert [a.title for a in section.achievements] == ["ひとつめ", "ふたつめ"]

    def test_the_user_s_own_words_arrive_unchanged(self, two_employers):
        told = SimpleNamespace(
            id=uuid.uuid4(),
            work_experience_id=two_employers[0].id,
            title="Cut the build in half",
            challenge="The build took forty minutes.",
            action="Split it and cached the slow step.",
            result="Twenty minutes.",
        )
        [achievement] = [
            a for s in build_history(two_employers, [told]).sections for a in s.achievements
        ]

        assert achievement.title == told.title
        assert achievement.challenge == told.challenge
        assert achievement.action == told.action
        assert achievement.result == told.result
        assert achievement.source_entry_id == told.id


class TestNothingRecordedIsDropped:
    def test_a_story_with_no_employer_closes_the_document(self, two_employers):
        history = build_history(two_employers, [story("どこにも属さない実績", None)])
        assert [a.title for a in history.unattached] == ["どこにも属さない実績"]

    def test_it_is_not_attached_to_the_nearest_employer(self, two_employers):
        """Inventing a relationship the user did not record is the failure
        Principle IV names (R-005)."""
        history = build_history(two_employers, [story("未所属", None)])
        assert all(s.achievements == () for s in history.sections)

    def test_a_story_pointing_at_an_employer_this_history_lacks_still_appears(self, two_employers):
        """Otherwise it falls between the two loops and vanishes silently."""
        history = build_history(two_employers, [story("孤児", uuid.uuid4())])
        assert [a.title for a in history.unattached] == ["孤児"]

    def test_every_story_comes_out_somewhere(self, two_employers):
        stories = [
            story("A", two_employers[0].id),
            story("B", two_employers[1].id),
            story("C", None),
            story("D", uuid.uuid4()),
        ]
        history = build_history(two_employers, stories)

        placed = [a.title for s in history.sections for a in s.achievements]
        assert sorted(placed + [a.title for a in history.unattached]) == ["A", "B", "C", "D"]


class TestTheOtherSections:
    def test_skills_languages_and_certifications_carry_their_entry(self):
        skill = SimpleNamespace(id=uuid.uuid4(), name="SQL", level="advanced")
        language = SimpleNamespace(
            id=uuid.uuid4(), language="日本語", proficiency="business", qualification="JLPT N2"
        )
        certification = SimpleNamespace(
            id=uuid.uuid4(), name="基本情報技術者", issuer="IPA", issued_on=date(2019, 4, 1)
        )

        history = build_history(
            [experience("会社", date(2020, 1, 1))],
            skills=[skill],
            languages=[language],
            certifications=[certification],
        )

        assert history.skills[0].source_entry_id == skill.id
        assert history.languages[0].qualification == "JLPT N2"
        assert history.certifications[0].issued_on == date(2019, 4, 1)


class TestTraceability:
    def test_every_drawn_entry_is_named(self, two_employers):
        """FR-016: for any statement in the document, name the entry behind it."""
        skill = SimpleNamespace(id=uuid.uuid4(), name="SQL", level=None)
        attached = story("実績", two_employers[0].id)
        loose = story("未所属", None)

        history = build_history(two_employers, [attached, loose], skills=[skill])
        ids = history.entry_ids()

        for entry in (*two_employers, attached, loose, skill):
            assert entry.id in ids

    def test_no_entry_is_named_twice(self, two_employers):
        history = build_history(two_employers, [story("実績", two_employers[0].id)])
        ids = history.entry_ids()
        assert len(ids) == len(set(ids))
