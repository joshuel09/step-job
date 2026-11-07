"""The readiness report — what an English resume would lack, before it is made.

The report and generation must never disagree. If the report says a
document can be made and generation refuses, or the reverse, the user has
been told something false at exactly the moment they act on it. So the
shapes here are checked against an actual generation and not only against
the report.

The other half is what readiness must **not** do. A missing English version
is reported and does not stop anything: the entry appears as recorded, in
Japanese, and a document a user can send today beats a refusal explaining
what they should have done months ago (FR-017, FR-020).
"""

from datetime import date

import pytest

PATH = "/api/v1/profile/documents/resume"
READINESS = f"{PATH}/readiness"
TRANSLATIONS = "/api/v1/profile/translations"


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
def japanese_profile(session, profile):
    """A career recorded in Japanese, with one English name supplied.

    Invented content. The education entry has an English institution name
    and the work experience does not, so "which organisations still need a
    name" has both answers in it.
    """
    from app.career import models

    session.add(
        models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"),
    )
    experience = models.WorkExperience(
        profile_id=profile.id,
        employer_name="株式会社サンプル",
        employer_name_normalised="サンプル",
        job_title="課長",
        description="社内システムの開発を担当。",
        started_on=date(2019, 4, 1),
    )
    education = models.Education(
        profile_id=profile.id,
        institution="サンプル大学",
        institution_english="Sample University",
        qualification="学士",
        field_of_study="情報工学",
        started_on=date(2015, 4, 1),
    )
    session.add_all([experience, education])
    session.flush()
    return {"experience": experience, "education": education}


class TestWhatIsMissingBeforeAnythingIsMade:
    def test_an_empty_profile_cannot_generate_and_says_why(self, client, auth_headers, profile):
        report = _report(client, auth_headers)

        assert report["can_generate"] is False
        assert sorted(report["missing_required"]) == ["experiences", "identity"]

    def test_and_generation_refuses_the_same_profile(self, client, auth_headers, profile):
        """The report and the refusal come from one rule, so they cannot
        disagree about whether a document can be made (FR-006)."""
        assert not _can_actually_generate(client, auth_headers)

    def test_a_profile_with_a_name_and_a_role_can_generate(
        self, client, auth_headers, japanese_profile
    ):
        report = _report(client, auth_headers)

        assert report["can_generate"] is True
        assert report["missing_required"] == []
        assert _can_actually_generate(client, auth_headers)

    def test_a_report_is_given_to_a_profile_that_cannot_generate_at_all(
        self, client, auth_headers, profile
    ):
        """The profile most in need of an answer is the one that could not
        produce a document, so this route answers rather than refusing."""
        assert client.get(READINESS, headers=auth_headers).status_code == 200

    def test_a_caller_with_no_profile_is_a_404(self, client, auth_headers):
        assert client.get(READINESS, headers=auth_headers).status_code == 404


class TestWhatStillNeedsEnglish:
    def test_each_japanese_field_is_named_with_its_text(
        self, client, auth_headers, japanese_profile
    ):
        needed = {
            (item["entry_type"], item["field"]): item
            for item in _report(client, auth_headers)["needs_english"]
        }

        assert set(needed) == {
            ("work_experience", "job_title"),
            ("work_experience", "description"),
            ("education", "qualification"),
            ("education", "field_of_study"),
        }
        assert needed[("work_experience", "job_title")]["source_text"] == "課長"

    def test_the_entry_is_named_so_the_user_knows_which_one(
        self, client, auth_headers, japanese_profile
    ):
        """An id tells the user nothing. The employer does."""
        labels = {item["label"] for item in _report(client, auth_headers)["needs_english"]}

        assert labels == {"株式会社サンプル", "サンプル大学"}

    def test_approving_one_takes_it_off_the_list(self, client, auth_headers, japanese_profile):
        """Scenario 8: approving once is enough, and the same work is not
        asked for twice (SC-012)."""
        entry = japanese_profile["experience"]
        client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json={
                "entry_type": "work_experience",
                "entry_id": str(entry.id),
                "field": "job_title",
                "text": "Section Chief",
            },
        )

        remaining = {
            (item["entry_type"], item["field"])
            for item in _report(client, auth_headers)["needs_english"]
        }

        assert ("work_experience", "job_title") not in remaining
        assert ("work_experience", "description") in remaining

    def test_a_field_already_in_english_is_not_reported(self, client, auth_headers, profile):
        """There is nothing to draft: the text is its own English version,
        and reporting it would ask the user to fix what is not broken."""
        client.post(
            "/api/v1/profile/experiences",
            headers=auth_headers,
            json={
                "employer_name": "Example Corp",
                "job_title": "Software Engineer",
                "description": "Platform work on the billing service.",
                "started_on": "2021-04-01",
            },
        )

        assert _report(client, auth_headers)["needs_english"] == []

    def test_a_career_story_is_never_reported(self, client, auth_headers, japanese_profile):
        """Stories are translatable and the 職務経歴書 prints them. A resume
        has no section for one, so reporting it would send the user off to
        do work that changes nothing on the page."""
        client.post(
            "/api/v1/profile/stories",
            headers=auth_headers,
            json={
                "title": "ビルド時間を半分にした",
                "challenge": "ビルドが遅かった",
                "action": "キャッシュを導入した",
                "result": "半分になった",
            },
        )

        types = {item["entry_type"] for item in _report(client, auth_headers)["needs_english"]}

        assert "career_story" not in types

    def test_nothing_missing_stops_the_document(self, client, auth_headers, japanese_profile):
        """The whole report can be non-empty and the resume still
        generates. Readiness tells; it does not gate (FR-017)."""
        report = _report(client, auth_headers)

        assert report["needs_english"]
        assert _can_actually_generate(client, auth_headers)


class TestWhichOrganisationsStillNeedAName:
    def test_one_with_no_english_name_is_reported(self, client, auth_headers, japanese_profile):
        reported = [
            (item["entry_type"], item["field"], item["recorded_name"])
            for item in _report(client, auth_headers)["untranslated_names"]
        ]

        assert reported == [("work_experience", "employer_name", "株式会社サンプル")]

    def test_one_the_user_has_already_supplied_is_not(self, client, auth_headers, japanese_profile):
        """The education entry has `institution_english`. The
        distinguishing half: a report that listed every Japanese name would
        pass the test above."""
        names = {
            item["recorded_name"] for item in _report(client, auth_headers)["untranslated_names"]
        }

        assert "サンプル大学" not in names

    def test_a_certification_has_two_of_them(self, client, auth_headers, japanese_profile):
        """Which is why the report names the field. A certification holds a
        name and an issuer and neither is ever drafted — both are proper
        nouns, and an invented awarding body is a claim the applicant has
        to answer for (R-002)."""
        client.post(
            "/api/v1/profile/certifications",
            headers=auth_headers,
            json={"name": "基本情報技術者", "issuer": "情報処理推進機構"},
        )

        fields = {
            item["field"]
            for item in _report(client, auth_headers)["untranslated_names"]
            if item["entry_type"] == "certification"
        }

        assert fields == {"name", "issuer"}

    def test_a_name_already_in_english_is_not_reported(self, client, auth_headers, profile):
        client.post(
            "/api/v1/profile/experiences",
            headers=auth_headers,
            json={
                "employer_name": "Example Corp",
                "job_title": "Software Engineer",
                "started_on": "2021-04-01",
            },
        )

        assert _report(client, auth_headers)["untranslated_names"] == []

    def test_a_name_is_never_in_needs_english(self, client, auth_headers, japanese_profile):
        """The two lists are separate because the answers are. Nothing
        drafts a company's name, so an employer that appeared under
        `needs_english` would be offering the user a draft of a proper noun
        (FR-021)."""
        drafted = {
            (item["entry_type"], item["field"])
            for item in _report(client, auth_headers)["needs_english"]
        }

        assert ("work_experience", "employer_name") not in drafted
