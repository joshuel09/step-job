"""Quickstart Scenario 11 — editing the source does not withdraw an approval.

A user approves an English rendering, then fixes a typo in the Japanese it
was a rendering of. Three things must happen, and the third is the one a
system gets wrong by being helpful:

- the approval is reported as stale, with the source as it now reads;
- it is **still stored** — not deleted, not re-drafted;
- the document is still produced, carrying the approved text.

Replacing the user's approved words with the newer Japanese, or dropping
the entry, would both be the product deciding something FR-023 gives to the
user. They approved those words. A typo fix does not take that back.
"""

import io
from datetime import date

import pytest
from app.translations.models import EntryTranslation
from pypdf import PdfReader
from sqlalchemy import select

PATH = "/api/v1/profile/documents/resume"
READINESS = f"{PATH}/readiness"
TRANSLATIONS = "/api/v1/profile/translations"

APPROVED = "Section Chief, platform team"


@pytest.fixture
def profile(session, user_id):
    from app.career import service

    return service.get_or_create_profile(session, user_id)


@pytest.fixture
def approved(client, auth_headers, session, profile):
    """One Japanese role with an approved English title. Invented content."""
    from app.career import models

    session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
    experience = models.WorkExperience(
        profile_id=profile.id,
        employer_name="株式会社サンプル",
        employer_name_normalised="サンプル",
        job_title="課長",
        started_on=date(2019, 4, 1),
    )
    session.add(experience)
    session.flush()

    stored = client.put(
        TRANSLATIONS,
        headers=auth_headers,
        json={
            "entry_type": "work_experience",
            "entry_id": str(experience.id),
            "field": "job_title",
            "text": APPROVED,
        },
    )
    assert stored.status_code == 200, stored.text
    assert stored.json()["is_stale"] is False
    return experience


def _edit(client, auth_headers, experience, title: str) -> None:
    response = client.patch(
        f"/api/v1/profile/experiences/{experience.id}",
        headers=auth_headers,
        json={"job_title": title},
    )
    assert response.status_code == 200, response.text


def _page(client, auth_headers) -> str:
    response = client.post(PATH, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(response.content)).pages
    )


class TestWhenTheSourceChanges:
    def test_the_approval_is_reported_stale_with_the_new_source(
        self, client, auth_headers, approved
    ):
        _edit(client, auth_headers, approved, "部長")

        report = client.get(READINESS, headers=auth_headers).json()

        assert [row["source_text"] for row in report["stale_translations"]] == ["部長"]
        assert [row["text"] for row in report["stale_translations"]] == [APPROVED]

    def test_it_is_still_stored(self, client, auth_headers, session, profile, approved):
        _edit(client, auth_headers, approved, "部長")

        rows = list(
            session.scalars(
                select(EntryTranslation).where(EntryTranslation.profile_id == profile.id)
            )
        )

        assert [row.approved_text for row in rows] == [APPROVED]

    def test_the_document_is_still_produced_and_carries_it(self, client, auth_headers, approved):
        _edit(client, auth_headers, approved, "部長")

        page = _page(client, auth_headers)

        assert APPROVED in page
        assert "部長" not in page

    def test_the_report_still_says_the_document_can_be_made(self, client, auth_headers, approved):
        """Staleness is a thing to know, not a thing to be stopped by."""
        _edit(client, auth_headers, approved, "部長")

        assert client.get(READINESS, headers=auth_headers).json()["can_generate"] is True

    def test_it_is_not_asked_for_again(self, client, auth_headers, approved):
        """A stale approval is not a missing one. Putting it back in
        `needs_english` would ask the user to do work they have done, and
        the two lists would be saying contradictory things about one
        field."""
        _edit(client, auth_headers, approved, "部長")

        report = client.get(READINESS, headers=auth_headers).json()

        assert [row["field"] for row in report["stale_translations"]] == ["job_title"]
        assert ("work_experience", "job_title") not in {
            (item["entry_type"], item["field"]) for item in report["needs_english"]
        }


class TestAnApprovalThisDocumentDoesNotPrint:
    def test_a_stale_story_is_not_reported_here(self, client, auth_headers, approved):
        """A story's English is kept and the 職務経歴書 prints it. This
        report is the resume's, and a resume has no section for a story —
        so asking its reader to re-read an approval that appears nowhere on
        their page is the same mistake as listing one under
        `needs_english`."""
        story = client.post(
            "/api/v1/profile/stories",
            headers=auth_headers,
            json={
                "title": "ビルド時間を半分にした",
                "challenge": "ビルドが遅かった",
                "action": "キャッシュを導入した",
                "result": "半分になった",
            },
        )
        assert story.status_code == 201, story.text
        story_id = story.json()["id"]
        client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json={
                "entry_type": "career_story",
                "entry_id": story_id,
                "field": "title",
                "text": "Halved the build time",
            },
        )
        edited = client.patch(
            f"/api/v1/profile/stories/{story_id}",
            headers=auth_headers,
            json={"title": "ビルド時間を三分の一にした"},
        )
        assert edited.status_code == 200, edited.text

        report = client.get(READINESS, headers=auth_headers).json()

        assert report["stale_translations"] == []

    def test_but_it_is_still_stored(self, client, auth_headers, session, profile, approved):
        """Filtered out of one document's report, not discarded. The other
        document still prints it, and the user still approved it."""
        story_id = client.post(
            "/api/v1/profile/stories",
            headers=auth_headers,
            json={
                "title": "ビルド時間を半分にした",
                "challenge": "ビルドが遅かった",
                "action": "キャッシュを導入した",
                "result": "半分になった",
            },
        ).json()["id"]
        client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json={
                "entry_type": "career_story",
                "entry_id": story_id,
                "field": "title",
                "text": "Halved the build time",
            },
        )

        listed = client.get(TRANSLATIONS, headers=auth_headers).json()

        assert "Halved the build time" in [row["text"] for row in listed]


class TestWhenTheSourceDoesNotChange:
    def test_nothing_is_reported(self, client, auth_headers, approved):
        """The distinguishing half. A report that called every approval
        stale would pass every test above."""
        report = client.get(READINESS, headers=auth_headers).json()

        assert report["stale_translations"] == []

    def test_an_unrelated_edit_leaves_it_alone(self, client, auth_headers, approved):
        """Staleness is about the field that was approved, not about the
        entry. Editing the employer does not withdraw an approval of the
        job title."""
        response = client.patch(
            f"/api/v1/profile/experiences/{approved.id}",
            headers=auth_headers,
            json={"employer_name": "株式会社サンプル商事"},
        )
        assert response.status_code == 200, response.text

        assert client.get(READINESS, headers=auth_headers).json()["stale_translations"] == []

    def test_editing_back_to_the_original_is_not_a_change(self, client, auth_headers, approved):
        """The digest is of the text, so a round trip ends where it
        started. A stored timestamp would say otherwise."""
        _edit(client, auth_headers, approved, "部長")
        _edit(client, auth_headers, approved, "課長")

        assert client.get(READINESS, headers=auth_headers).json()["stale_translations"] == []

    def test_re_approving_clears_it(self, client, auth_headers, approved):
        """The way out, and the only way: the user looks at the new source
        and says again what it should read in English."""
        _edit(client, auth_headers, approved, "部長")

        client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json={
                "entry_type": "work_experience",
                "entry_id": str(approved.id),
                "field": "job_title",
                "text": "Department Head, platform team",
            },
        )

        assert client.get(READINESS, headers=auth_headers).json()["stale_translations"] == []
