"""Quickstart Scenario 6 — nothing recorded is lost.

A career story the user recorded against no employer is the entry most likely
to disappear. It belongs to no section, so the obvious implementation drops
it between the loops, and nobody notices: the document still reads well, and
the only person who could tell is the one who wrote the story and will not
read their own document closely enough to miss it.

The rule is counted rather than asserted case by case. Stories in, achievements
out, and the two numbers match whatever shape the profile has.
"""

import io
import re
from datetime import date

import pytest
from pypdf import PdfReader
from sqlalchemy import select

PATH = "/api/v1/profile/documents/shokumu-keirekisho"

CLOSING = "その他の実績"
AFTER_CLOSING = "活かせる経験・知識・技術"


def _lines(client, auth_headers, **body) -> list[str]:
    response = client.post(PATH, headers=auth_headers, json=body)
    assert response.status_code == 200, response.text
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(response.content)).pages)
    return [line.strip() for line in text.splitlines() if line.strip()]


def _titles(session, profile_id) -> list[str]:
    from app.career import models

    return list(
        session.scalars(
            select(models.CareerStory.title).where(models.CareerStory.profile_id == profile_id)
        )
    )


def _story(profile_id, title: str, employer_id=None):
    from app.career import models

    # The three fields deliberately do not repeat the title: counting how
    # many times a title appears is how these tests check nothing is
    # duplicated or dropped, and a title echoed inside its own story would
    # make every count four.
    return models.CareerStory(
        profile_id=profile_id,
        work_experience_id=employer_id,
        title=title,
        challenge="課題があった。",
        action="対応した。",
        result="解決した。",
    )


class TestCountInCountOut:
    def test_every_recorded_story_appears_exactly_once(
        self, client, auth_headers, session, shokumu_profile
    ):
        document = "".join(_lines(client, auth_headers))

        recorded = _titles(session, shokumu_profile.id)
        assert len(recorded) == 2, "the fixture records one attached and one unattached"
        for title in recorded:
            assert document.count(title) == 1, f"{title} appears {document.count(title)} times"

    def test_adding_an_unattached_story_adds_one_to_the_document(
        self, client, auth_headers, session, shokumu_profile
    ):
        before = "".join(_lines(client, auth_headers))

        session.add(_story(shokumu_profile.id, "あとから足した実績"))
        session.flush()

        after = "".join(_lines(client, auth_headers))
        assert "あとから足した実績" not in before
        assert after.count("あとから足した実績") == 1

    def test_every_story_comes_out_whatever_it_is_attached_to(
        self, client, auth_headers, session, shokumu_profile
    ):
        from app.career import models

        employers = list(
            session.scalars(
                select(models.WorkExperience).where(
                    models.WorkExperience.profile_id == shokumu_profile.id
                )
            )
        )
        session.add_all(
            [
                _story(shokumu_profile.id, "一社目の実績", employers[0].id),
                _story(shokumu_profile.id, "二社目の実績", employers[1].id),
                _story(shokumu_profile.id, "どこにも属さない実績"),
            ]
        )
        session.flush()

        document = "".join(_lines(client, auth_headers))
        for title in _titles(session, shokumu_profile.id):
            assert title in document, f"{title} was dropped"


class TestWhereAnUnattachedStoryGoes:
    def test_it_closes_the_document_rather_than_joining_an_employer(
        self, client, auth_headers, shokumu_profile
    ):
        lines = _lines(client, auth_headers)
        closing = lines.index(CLOSING)

        assert lines.index("・社外勉強会の運営") > closing
        assert lines.index("・社外勉強会の運営") < lines.index(AFTER_CLOSING)

    def test_an_attached_story_does_not_go_there(self, client, auth_headers, shokumu_profile):
        lines = _lines(client, auth_headers)
        assert lines.index("・ビルド時間を半分にした") < lines.index(CLOSING)

    def test_the_closing_section_is_absent_when_there_is_nothing_for_it(
        self, client, auth_headers, session, user_id
    ):
        """An empty section is labelled where the document has a box for it.
        This one is not a box — it exists only because something was recorded
        against no employer, so with nothing there it is not drawn at all."""
        from app.career import models, service

        profile = service.get_or_create_profile(session, user_id)
        session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
        session.add(
            models.WorkExperience(
                profile_id=profile.id,
                employer_name="株式会社サンプル",
                employer_name_normalised="サンプル",
                job_title="エンジニア",
                started_on=date(2020, 4, 1),
            )
        )
        session.flush()

        assert CLOSING not in _lines(client, auth_headers)


class TestAProfileOfNothingButUnattachedStories:
    @pytest.fixture
    def all_loose(self, session, user_id):
        from app.career import models, service

        profile = service.get_or_create_profile(session, user_id)
        session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
        session.add(
            models.WorkExperience(
                profile_id=profile.id,
                employer_name="株式会社サンプル",
                employer_name_normalised="サンプル",
                job_title="エンジニア",
                started_on=date(2020, 4, 1),
            )
        )
        session.flush()
        session.add_all([_story(profile.id, f"実績{number}") for number in ("一", "二", "三")])
        session.flush()
        return profile

    def test_the_employer_section_has_no_achievements(self, client, auth_headers, all_loose):
        lines = _lines(client, auth_headers)
        employer = lines.index("株式会社サンプル")
        assert lines[employer : lines.index(CLOSING)].count("実績") == 0

    def test_and_the_closing_section_has_all_of_them(self, client, auth_headers, all_loose):
        lines = _lines(client, auth_headers)
        closing = lines.index(CLOSING)

        for number in ("一", "二", "三"):
            assert lines.index(f"・実績{number}") > closing

    def test_a_true_picture_of_what_was_recorded(self, client, auth_headers, session, all_loose):
        """Three stories recorded against nothing produce three achievements
        under no employer. Attaching them to the only employer there would
        read better and would be a claim the user did not make."""
        document = "".join(_lines(client, auth_headers))
        assert len(_titles(session, all_loose.id)) == 3
        assert sum(document.count(f"実績{n}") for n in ("一", "二", "三")) == 3


class TestTheUserSOwnWords:
    def test_an_achievement_is_not_summarised_on_the_way_through(
        self, client, auth_headers, shokumu_profile
    ):
        document = re.sub(r"[\s　]+", "", "".join(_lines(client, auth_headers)))
        for sentence in (
            "参加者が集まらなかった。",
            "告知の方法を変えた。",
            "毎回三十名が参加した。",
        ):
            assert sentence in document
