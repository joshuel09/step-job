"""Quickstart Scenarios 1, 2, 3, 4 and 13 — the document itself.

Read back out of the PDF with pypdf rather than asserted against the
projection, because the projection is already tested and what a user
receives is the page. A test that checked the dataclasses would pass while
the renderer dropped a section.

Two of these are about absence, which is the harder thing to test and the
easier thing to get wrong:

- No certifications heading when there are no certifications (FR-011).
- No era name anywhere, no matter what the profile holds (FR-004).
"""

import io
import re

import pytest
from pypdf import PdfReader

PATH = "/api/v1/profile/documents/resume"
ERA_NAMES = ("令和", "平成", "昭和", "大正", "明治")

#: Scenario 3 forbids the word 年号 as well as the eras themselves. It is
#: not an era, so it is not in the tuple above — and a document that
#: labelled a field "年号" would carry no era name at all while being
#: exactly the document FR-004 is about.
NOT_IN_AN_ENGLISH_DOCUMENT = (*ERA_NAMES, "年号")


def _response(client, auth_headers, **body):
    response = client.post(PATH, headers=auth_headers, json=body)
    assert response.status_code == 200, response.text
    return response


def _text(pdf: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)


@pytest.fixture
def document(client, auth_headers, resume_profile):
    return _text(_response(client, auth_headers).content)


class TestWhatIsOnThePage:
    def test_the_name_and_both_ways_to_reach_the_person(self, document):
        assert "Taro Yamada" in document
        assert "taro@example.com" in document
        assert "090-0000-0000" in document

    def test_both_employers_appear(self, document):
        assert "Example Corp" in document
        assert "株式会社サンプル" in document

    def test_the_most_recent_role_comes_first(self, document):
        """Reverse-chronological is what a US resume means by order
        (FR-003), and it is the ordering the reader assumes without being
        told — so getting it backwards misleads silently."""
        assert document.index("Example Corp") < document.index("株式会社サンプル")

    def test_each_role_carries_its_title_and_period(self, document):
        """Each, not the most recent. A document that kept the current role
        whole and reduced the earlier one to a company name would satisfy a
        test that looked only at the top of the page — and the older role
        is the half of someone's history they can least afford to lose.
        """
        assert "Software Engineer" in document
        # The exact string. An alternative the fixture can never produce
        # only widens what passes — a month off by one would satisfy it.
        assert "Apr 2021 – Present" in document

        # Recorded in Japanese with no approved English, so it appears as
        # the user wrote it (FR-021).
        assert "エンジニア" in document
        assert "Apr 2013 – Mar 2021" in document

    def test_education_appears(self, document):
        assert "Education" in document
        assert "Example University" in document
        assert "Computer Science" in document

    def test_a_supplied_english_certification_name_is_used(self, document):
        """The user told us what it is called in English, so that is what
        the document says (FR-021)."""
        assert "Fundamental Information Technology Engineer" in document


class TestWhatIsNotOnThePage:
    def test_no_certifications_heading_without_certifications(
        self, client, auth_headers, session, user_id
    ):
        """FR-011. A 履歴書 prints some headings over nothing on purpose — a
        blank 賞罰 is itself a statement. A resume has no such convention,
        and an empty Certifications heading says the applicant tried to
        think of one and failed.
        """
        from datetime import date

        from app.career import models, service

        profile = service.get_or_create_profile(session, user_id)
        session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
        session.add(
            models.WorkExperience(
                profile_id=profile.id,
                employer_name="Example Corp",
                employer_name_normalised="example",
                job_title="Software Engineer",
                started_on=date(2021, 4, 1),
            )
        )
        session.flush()

        document = _text(_response(client, auth_headers).content)

        assert "Example Corp" in document, "the document was produced"
        assert "Certifications" not in document
        assert "Education" not in document
        assert "Skills" not in document

    def test_the_skills_section_goes_when_the_user_says_so(
        self, client, auth_headers, session, resume_profile
    ):
        """Shortening is the user's choice, never the renderer's (FR-007)."""
        from app.career import models

        session.add(models.Skill(profile_id=resume_profile.id, name="PostgreSQL"))
        session.flush()

        with_skills = _text(_response(client, auth_headers).content)
        without = _text(_response(client, auth_headers, include_skills=False).content)

        assert "PostgreSQL" in with_skills and "Skills" in with_skills
        assert "PostgreSQL" not in without and "Skills" not in without

    def test_nothing_from_the_japan_profile_or_the_identity_beyond_contact(
        self, client, auth_headers, session, resume_profile
    ):
        """FR-009 and FR-010. The fixture records a date of birth and an
        address precisely so this has something to not find."""
        from app.career import models

        session.add(
            models.JapanProfile(
                profile_id=resume_profile.id,
                nationality="Example nationality",
                residence_status="Example status",
                disclose_nationality=True,
            )
        )
        session.flush()

        document = _text(_response(client, auth_headers).content)

        assert "東京都千代田区" not in document
        assert "1990" not in document
        assert "Example nationality" not in document
        assert "Example status" not in document


class TestDates:
    def test_a_period_reads_the_way_an_english_resume_writes_one(self, document):
        assert re.search(r"[A-Z][a-z]{2} \d{4} – (Present|[A-Z][a-z]{2} \d{4})", document)

    def test_no_era_name_appears_anywhere(self, document):
        """FR-004. The profile is Japanese; the document is not, and the
        formatter it uses cannot reach the era table at all (R-006)."""
        for word in NOT_IN_AN_ENGLISH_DOCUMENT:
            assert word not in document, word

    def test_a_japanese_interface_locale_changes_none_of_it(
        self, client, auth_headers, session, resume_profile
    ):
        """Scenario 3 says *given a profile whose interface locale is
        Japanese*, and every other test in this class runs on the default
        profile, whose locale is already `en`. All of them would pass
        against a renderer that read the setting and switched calendars for
        a Japanese user, which is the failure FR-004 is about.

        The periods are asserted as exact strings. A document that dropped
        both roles would satisfy the era check on its own.
        """
        from app.career.models import Locale

        resume_profile.interface_locale = Locale.ja
        session.flush()

        document = _text(_response(client, auth_headers).content)

        # Every date on the page, not only the two periods. A renderer that
        # read the locale would be unlikely to convert some sections and
        # not others, but a test that looked at two of four would report
        # success for the version that did.
        assert "Apr 2021 – Present" in document
        assert "Apr 2013 – Mar 2021" in document
        assert "Apr 2009 – Mar 2013" in document
        assert "Apr 2019" in document

        for word in NOT_IN_AN_ENGLISH_DOCUMENT:
            assert word not in document, word
        assert not re.search(r"\d\s*年", document)
        assert not re.search(r"\d\s*月", document)

    def test_no_japanese_date_punctuation_appears_either(self, document):
        """年月日 would be a Japanese date written in Arabic numerals —
        technically era-free and still the wrong document."""
        assert not re.search(r"\d\s*年", document)
        assert not re.search(r"\d\s*月", document)


class TestWhatComesBackWithIt:
    def test_a_snapshot_id_is_returned(self, client, auth_headers, resume_profile):
        import uuid

        response = _response(client, auth_headers)

        assert uuid.UUID(response.headers["X-Snapshot-Id"])

    def test_the_page_count_is_returned(self, client, auth_headers, resume_profile):
        response = _response(client, auth_headers)

        assert int(response.headers["X-Document-Pages"]) >= 1

    def test_a_preview_is_the_same_document_shown_differently(
        self, client, auth_headers, resume_profile
    ):
        """Only the disposition differs, so a user never previews one thing
        and downloads another."""
        download = _response(client, auth_headers)
        preview = client.post(f"{PATH}?preview=true", headers=auth_headers, json={})

        assert preview.status_code == 200, preview.text
        assert "attachment" in download.headers["Content-Disposition"]
        assert "inline" in preview.headers["Content-Disposition"]
        assert _text(download.content) == _text(preview.content)


class TestWhenItCannotBeProduced:
    def test_a_profile_with_no_career_history_is_refused(
        self, client, auth_headers, session, user_id
    ):
        """FR-006, and the refusal names what is missing rather than
        producing a page with headings and nothing under them."""
        from app.career import models, service

        profile = service.get_or_create_profile(session, user_id)
        session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
        session.flush()

        refused = client.post(PATH, headers=auth_headers, json={})

        assert refused.status_code == 422, refused.text
        assert [f["field"] for f in refused.json()["failures"]] == ["experiences"]

    def test_a_profile_with_no_name_is_refused(self, client, auth_headers, session, user_id):
        from datetime import date

        from app.career import models, service

        profile = service.get_or_create_profile(session, user_id)
        session.add(
            models.WorkExperience(
                profile_id=profile.id,
                employer_name="Example Corp",
                employer_name_normalised="example",
                job_title="Software Engineer",
                started_on=date(2021, 4, 1),
            )
        )
        session.flush()

        refused = client.post(PATH, headers=auth_headers, json={})

        assert refused.status_code == 422, refused.text
        assert "identity" in [f["field"] for f in refused.json()["failures"]]

    def test_a_missing_english_version_is_not_a_refusal(self, client, auth_headers, resume_profile):
        """FR-017. The fixture's first employer is Japanese with no
        approved translation, which is the ordinary state of a profile
        partway through this feature. The document is produced; the gap is
        the readiness route's to report, and telling the user at the moment
        they asked for a document is what FR-020 exists to prevent.
        """
        response = client.post(PATH, headers=auth_headers, json={})

        assert response.status_code == 200, response.text
        assert "エンジニア" in _text(response.content), "rendered as recorded, not dropped"
