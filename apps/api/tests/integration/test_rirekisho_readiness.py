"""The readiness report — what a 履歴書 would lack, before it is printed.

The report and generation must never disagree. If the report says a document
can be made and generation refuses, or the reverse, the user has been told
something false at exactly the moment they act on it. So every profile shape
here is checked against an actual generation, not only against the report.
"""

from datetime import date

import pytest
from sqlalchemy import func, select

PATH = "/api/v1/profile/documents/rirekisho"
READINESS = f"{PATH}/readiness"

ALL_IDENTITY = [
    "identity.furigana",
    "identity.date_of_birth",
    "identity.address",
    "identity.phone",
    "identity.email",
]
ALL_SECTIONS = ["education", "experiences", "certifications"]


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
def name_only(session, profile):
    from app.career import models

    session.add(models.Identity(profile_id=profile.id, full_name_latin="Hanako Suzuki"))
    session.flush()
    return profile


class TestWhatCannotBeLeftOut:
    def test_no_identity_cannot_generate(self, client, auth_headers, profile):
        report = _report(client, auth_headers)
        assert report["can_generate"] is False
        assert report["missing_required"] == ["identity"]

    def test_a_blank_name_cannot_generate(self, client, auth_headers, session, profile):
        from app.career import models

        session.add(models.Identity(profile_id=profile.id, full_name_latin="   "))
        session.flush()

        report = _report(client, auth_headers)
        assert report["can_generate"] is False
        assert report["missing_required"] == ["identity.full_name_latin"]

    def test_a_name_is_all_that_is_required(self, client, auth_headers, name_only):
        report = _report(client, auth_headers)
        assert report["can_generate"] is True
        assert report["missing_required"] == []


class TestWhatWillBeBlank:
    def test_a_name_only_profile_lists_every_blank_box(self, client, auth_headers, name_only):
        assert _report(client, auth_headers)["missing_optional"] == ALL_IDENTITY + ALL_SECTIONS

    def test_the_full_fixture_lists_only_what_it_lacks(
        self, client, auth_headers, rirekisho_profile
    ):
        """The shared fixture has no phone, no email and no certifications."""
        assert _report(client, auth_headers)["missing_optional"] == [
            "identity.phone",
            "identity.email",
            "certifications",
        ]

    def test_with_no_identity_the_identity_boxes_are_still_listed(
        self, client, auth_headers, profile
    ):
        """Told everything at once, rather than one thing per attempt."""
        assert _report(client, auth_headers)["missing_optional"] == ALL_IDENTITY + ALL_SECTIONS

    def test_a_blank_box_does_not_stop_generation(self, client, auth_headers, name_only):
        assert _report(client, auth_headers)["missing_optional"]
        assert _can_actually_generate(client, auth_headers)


class TestEntriesWithoutJapanese:
    def test_an_english_entry_is_named_with_its_id_and_label(
        self, client, auth_headers, session, rirekisho_profile
    ):
        from app.career import models

        role_id = session.scalar(
            select(models.WorkExperience.id).where(
                models.WorkExperience.employer_name == "Example Corp"
            )
        )

        assert _report(client, auth_headers)["entries_without_japanese"] == [
            {"entry_id": str(role_id), "entry_type": "work_experience", "label": "Example Corp"}
        ]

    def test_japanese_text_is_not_reported_whatever_its_recorded_language(
        self, client, auth_headers, rirekisho_profile
    ):
        """The fixture's university was entered without a source language, so it
        defaults to English. It is written in Japanese and must not be listed."""
        labels = [e["label"] for e in _report(client, auth_headers)["entries_without_japanese"]]
        assert "サンプル大学" not in labels
        assert "株式会社サンプル" not in labels

    def test_every_kind_of_entry_is_checked(self, client, auth_headers, session, name_only):
        from app.career import models

        session.add_all(
            [
                models.Education(profile_id=name_only.id, institution="Example University"),
                models.WorkExperience(
                    profile_id=name_only.id,
                    employer_name="Example Corp",
                    employer_name_normalised="example",
                    job_title="Engineer",
                    started_on=date(2020, 4, 1),
                ),
                models.Certification(profile_id=name_only.id, name="AWS Solutions Architect"),
                models.Certification(profile_id=name_only.id, name="日本語能力試験 N2"),
            ]
        )
        session.flush()

        english = _report(client, auth_headers)["entries_without_japanese"]
        assert sorted((e["entry_type"], e["label"]) for e in english) == [
            ("certification", "AWS Solutions Architect"),
            ("education", "Example University"),
            ("work_experience", "Example Corp"),
        ]

    def test_reporting_writes_no_japanese_version(
        self, client, auth_headers, session, rirekisho_profile
    ):
        """R-001: the user is told; nothing is written for them."""
        from app.career import models

        _report(client, auth_headers)
        names = session.scalars(select(models.WorkExperience.employer_name)).all()
        assert sorted(names) == ["Example Corp", "株式会社サンプル"]


class TestTheReportAgreesWithGeneration:
    """For every shape of profile, can_generate is what generation does."""

    # "spaces_name" is the one where two separate checks would part company: a
    # truthiness test accepts "   " and a strip() test does not.
    @pytest.mark.parametrize(
        "shape", ["no_identity", "blank_name", "spaces_name", "name_only", "full"]
    )
    def test_can_generate_matches_an_actual_generation(
        self, client, auth_headers, session, request, shape
    ):
        from app.career import models

        if shape == "full":
            request.getfixturevalue("rirekisho_profile")
        else:
            profile = request.getfixturevalue("profile")
            if shape == "blank_name":
                session.add(models.Identity(profile_id=profile.id, full_name_latin=""))
            elif shape == "spaces_name":
                session.add(models.Identity(profile_id=profile.id, full_name_latin="   "))
            elif shape == "name_only":
                session.add(models.Identity(profile_id=profile.id, full_name_latin="Hanako"))
            session.flush()

        assert _report(client, auth_headers)["can_generate"] is _can_actually_generate(
            client, auth_headers
        )

    def test_a_refusal_names_what_the_report_named(self, client, auth_headers, profile):
        required = _report(client, auth_headers)["missing_required"]
        refusal = client.post(PATH, headers=auth_headers, json={}).json()
        assert [f["field"] for f in refusal["failures"]] == required


class TestTheRoute:
    def test_the_response_has_every_documented_field(self, client, auth_headers, rirekisho_profile):
        assert set(_report(client, auth_headers)) == {
            "can_generate",
            "missing_required",
            "missing_optional",
            "entries_without_japanese",
        }

    def test_reading_the_report_records_no_snapshot(
        self, client, auth_headers, session, rirekisho_profile
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
