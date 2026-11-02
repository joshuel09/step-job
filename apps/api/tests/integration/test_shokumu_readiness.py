"""The readiness report — what a 職務経歴書 would lack, before it is printed.

The report and generation must never disagree. If the report says a document
can be made and generation refuses, or the reverse, the user has been told
something false at exactly the moment they act on it. So every shape of
profile here is checked against an actual generation, not only against the
report.

This document's report has something the 履歴書's does not: achievements
recorded against no employer. They are not missing — they are in the closing
section — but a user who meant to attach one and did not should find that out
before they send it.
"""

from datetime import date

import pytest
from sqlalchemy import func, select

PATH = "/api/v1/profile/documents/shokumu-keirekisho"
READINESS = f"{PATH}/readiness"

ALL_SECTIONS = ["skills", "languages", "certifications", "stories"]


def _report(client, auth_headers) -> dict:
    response = client.get(READINESS, headers=auth_headers)
    assert response.status_code == 200, response.text
    return response.json()


def _can_actually_generate(client, auth_headers) -> bool:
    status = client.post(PATH, headers=auth_headers, json={}).status_code
    assert status in (200, 422), status
    return status == 200


@pytest.fixture
def profile(session, user_id):
    from app.career import service

    return service.get_or_create_profile(session, user_id)


@pytest.fixture
def one_employer(session, profile):
    """A name and one employer: the least that produces a document."""
    from app.career import models

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
    return profile


class TestWhatCannotBeLeftOut:
    def test_an_empty_profile_cannot_generate(self, client, auth_headers, profile):
        report = _report(client, auth_headers)
        assert report["can_generate"] is False
        assert report["missing_required"] == ["identity", "experiences"]

    def test_a_name_alone_is_not_enough(self, client, auth_headers, session, profile):
        """A 職務経歴書 with no work history is a different document."""
        from app.career import models

        session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
        session.flush()

        assert _report(client, auth_headers)["missing_required"] == ["experiences"]

    def test_work_history_alone_is_not_enough_either(self, client, auth_headers, session, profile):
        from app.career import models

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

        assert _report(client, auth_headers)["missing_required"] == ["identity"]

    def test_a_blank_name_counts_as_no_name(self, client, auth_headers, session, profile):
        """The case where a truthiness test and a strip() part company."""
        from app.career import models

        session.add(models.Identity(profile_id=profile.id, full_name_latin="   "))
        session.flush()

        assert "identity" in _report(client, auth_headers)["missing_required"]

    def test_a_name_and_an_employer_are_all_that_is_required(
        self, client, auth_headers, one_employer
    ):
        report = _report(client, auth_headers)
        assert report["can_generate"] is True
        assert report["missing_required"] == []


class TestWhatWillBeBlank:
    def test_the_least_profile_lists_every_empty_section(self, client, auth_headers, one_employer):
        assert _report(client, auth_headers)["missing_optional"] == ALL_SECTIONS

    def test_the_full_fixture_lists_nothing(self, client, auth_headers, shokumu_profile):
        """It records a skill, a language, a certification and two stories."""
        assert _report(client, auth_headers)["missing_optional"] == []

    def test_a_blank_section_does_not_stop_generation(self, client, auth_headers, one_employer):
        assert _report(client, auth_headers)["missing_optional"]
        assert _can_actually_generate(client, auth_headers)

    def test_a_section_stops_being_listed_once_it_holds_something(
        self, client, auth_headers, session, one_employer
    ):
        from app.career import models

        assert "skills" in _report(client, auth_headers)["missing_optional"]

        session.add(models.Skill(profile_id=one_employer.id, name="SQL"))
        session.flush()

        assert "skills" not in _report(client, auth_headers)["missing_optional"]


class TestAchievementsAttachedToNothing:
    def test_one_is_named_with_its_id_and_title(
        self, client, auth_headers, session, shokumu_profile
    ):
        """The id as well as the title, so a client can link straight to the
        entry rather than making the user find it by name."""
        from app.career import models

        story = session.scalars(
            select(models.CareerStory).where(models.CareerStory.work_experience_id.is_(None))
        ).one()

        assert _report(client, auth_headers)["unattached_achievements"] == [
            {"entry_id": str(story.id), "title": "社外勉強会の運営"}
        ]

    def test_an_attached_one_is_not_named(self, client, auth_headers, shokumu_profile):
        titles = [e["title"] for e in _report(client, auth_headers)["unattached_achievements"]]
        assert "ビルド時間を半分にした" not in titles

    def test_it_does_not_stop_a_document_being_made(self, client, auth_headers, shokumu_profile):
        """Reported, not refused: it is in the document, in the closing
        section. The user may attach it, and nothing here guesses (R-005)."""
        assert _report(client, auth_headers)["can_generate"] is True
        assert _can_actually_generate(client, auth_headers)

    def test_reporting_one_attaches_nothing(self, client, auth_headers, session, shokumu_profile):
        """The user is told; nothing is written for them."""
        from app.career import models

        _report(client, auth_headers)

        story = session.scalars(
            select(models.CareerStory).where(models.CareerStory.title == "社外勉強会の運営")
        ).one()
        assert story.work_experience_id is None

    def test_a_profile_with_none_reports_none(self, client, auth_headers, one_employer):
        assert _report(client, auth_headers)["unattached_achievements"] == []


class TestTheReportAgreesWithGeneration:
    """For every shape of profile, can_generate is what generation does."""

    @pytest.mark.parametrize(
        "shape", ["empty", "name_only", "spaces_name", "employer_only", "least", "full"]
    )
    def test_can_generate_matches_an_actual_generation(
        self, client, auth_headers, session, request, shape
    ):
        from app.career import models

        if shape == "full":
            request.getfixturevalue("shokumu_profile")
        elif shape == "least":
            request.getfixturevalue("one_employer")
        else:
            owner = request.getfixturevalue("profile")
            if shape in ("name_only", "spaces_name"):
                name = "   " if shape == "spaces_name" else "Taro Yamada"
                session.add(models.Identity(profile_id=owner.id, full_name_latin=name))
            elif shape == "employer_only":
                session.add(
                    models.WorkExperience(
                        profile_id=owner.id,
                        employer_name="株式会社サンプル",
                        employer_name_normalised="サンプル",
                        job_title="エンジニア",
                        started_on=date(2020, 4, 1),
                    )
                )
            session.flush()

        assert _report(client, auth_headers)["can_generate"] is _can_actually_generate(
            client, auth_headers
        )

    def test_a_refusal_names_what_the_report_named(self, client, auth_headers, profile):
        required = _report(client, auth_headers)["missing_required"]
        refusal = client.post(PATH, headers=auth_headers, json={}).json()
        assert [f["field"] for f in refusal["failures"]] == required


class TestTheRoute:
    def test_the_response_has_every_documented_field(self, client, auth_headers, shokumu_profile):
        assert set(_report(client, auth_headers)) == {
            "can_generate",
            "missing_required",
            "missing_optional",
            "unattached_achievements",
        }

    def test_reading_the_report_records_no_snapshot(
        self, client, auth_headers, session, shokumu_profile
    ):
        """Nothing is generated, so nothing is recorded as having been sent."""
        from app.career import models

        def count() -> int:
            return session.scalar(select(func.count()).select_from(models.EntrySnapshot))

        before = count()
        _report(client, auth_headers)
        assert count() == before

    def test_a_caller_without_an_identity_is_refused(self, client):
        assert client.get(READINESS).status_code == 401

    def test_a_caller_with_no_profile_gets_404(self, client, auth_headers):
        assert client.get(READINESS, headers=auth_headers).status_code == 404
