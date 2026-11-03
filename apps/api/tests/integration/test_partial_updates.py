"""A PATCH changes what it names and nothing else.

The four sections that share one registrar — education, certifications,
skills and languages — validated their PATCH bodies with the same schema as
their POST, so every partial update had to resend the entry's main field.
Two things follow, and both are worse than the inconvenience:

- A field could only be set by sending a field it has nothing to do with,
  which is how feature 005's English names turned out to be unsettable on
  two of the three entry types that carry them.
- A user who resends the main field to satisfy the validator is one typo
  away from overwriting the fact the document is built on.

The explicit-null cases are here for the opposite reason: a PATCH may leave
a field out, but it may not blank one the entry cannot be without. Omission
and null are different requests and only one of them is allowed.
"""

import pytest


@pytest.fixture
def profile(session, user_id):
    from app.career import service

    return service.get_or_create_profile(session, user_id)


def _create(client, auth_headers, section: str, body: dict) -> str:
    created = client.post(f"/api/v1/profile/{section}", headers=auth_headers, json=body)
    assert created.status_code == 201, created.text
    return created.json()["id"]


class TestOneFieldAtATime:
    def test_a_qualification_without_resending_the_institution(self, client, auth_headers, profile):
        entry = _create(client, auth_headers, "education", {"institution": "サンプル大学"})

        patched = client.patch(
            f"/api/v1/profile/education/{entry}",
            headers=auth_headers,
            json={"qualification": "学士"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["qualification"] == "学士"
        assert patched.json()["institution"] == "サンプル大学"

    def test_an_issuer_without_resending_the_name(self, client, auth_headers, profile):
        entry = _create(client, auth_headers, "certifications", {"name": "基本情報技術者"})

        patched = client.patch(
            f"/api/v1/profile/certifications/{entry}",
            headers=auth_headers,
            json={"issuer": "情報処理推進機構"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["issuer"] == "情報処理推進機構"
        assert patched.json()["name"] == "基本情報技術者"

    def test_a_level_without_resending_the_skill(self, client, auth_headers, profile):
        entry = _create(client, auth_headers, "skills", {"name": "Python"})

        patched = client.patch(
            f"/api/v1/profile/skills/{entry}",
            headers=auth_headers,
            json={"level": "advanced"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["level"] == "advanced"
        assert patched.json()["name"] == "Python"

    def test_a_proficiency_without_resending_the_language(self, client, auth_headers, profile):
        entry = _create(
            client, auth_headers, "languages", {"language": "日本語", "proficiency": "business"}
        )

        patched = client.patch(
            f"/api/v1/profile/languages/{entry}",
            headers=auth_headers,
            json={"proficiency": "native"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["proficiency"] == "native"
        assert patched.json()["language"] == "日本語"


class TestWhatCannotBeBlanked:
    """Omitting a field and sending it as null are different requests.

    The second one asks to erase something the entry cannot be without, and
    the answer is 422 rather than a 500 from the database — a rejected
    request the client can report, not a crash it cannot explain.
    """

    def test_an_institution_cannot_be_nulled(self, client, auth_headers, profile):
        entry = _create(client, auth_headers, "education", {"institution": "サンプル大学"})

        refused = client.patch(
            f"/api/v1/profile/education/{entry}",
            headers=auth_headers,
            json={"institution": None},
        )
        assert refused.status_code == 422, refused.text

        unchanged = client.get("/api/v1/profile/education", headers=auth_headers)
        assert unchanged.json()[0]["institution"] == "サンプル大学"

    def test_an_employer_name_cannot_be_nulled(self, client, auth_headers, profile):
        created = client.post(
            "/api/v1/profile/experiences",
            headers=auth_headers,
            json={
                "employer_name": "株式会社サンプル",
                "job_title": "エンジニア",
                "started_on": "2020-04-01",
            },
        )
        assert created.status_code == 201, created.text

        refused = client.patch(
            f"/api/v1/profile/experiences/{created.json()['id']}",
            headers=auth_headers,
            json={"employer_name": None},
        )
        assert refused.status_code == 422, refused.text

    def test_a_started_on_cannot_be_nulled(self, client, auth_headers, profile):
        """Unlike ended_on, which means ongoing. One of the pair is nullable
        and the other is not, and the difference is not cosmetic."""
        created = client.post(
            "/api/v1/profile/experiences",
            headers=auth_headers,
            json={
                "employer_name": "株式会社サンプル",
                "job_title": "エンジニア",
                "started_on": "2020-04-01",
            },
        )
        entry = created.json()["id"]

        refused = client.patch(
            f"/api/v1/profile/experiences/{entry}",
            headers=auth_headers,
            json={"started_on": None},
        )
        assert refused.status_code == 422, refused.text

        allowed = client.patch(
            f"/api/v1/profile/experiences/{entry}",
            headers=auth_headers,
            json={"ended_on": None},
        )
        assert allowed.status_code == 200, allowed.text
        assert allowed.json()["ended_on"] is None

    def test_an_english_name_may_be_nulled(self, client, auth_headers, profile):
        """The user withdrawing a name they supplied is a real request, and
        absent is what the column already means (FR-021)."""
        entry = _create(
            client,
            auth_headers,
            "education",
            {"institution": "サンプル大学", "institution_english": "Sample University"},
        )

        cleared = client.patch(
            f"/api/v1/profile/education/{entry}",
            headers=auth_headers,
            json={"institution_english": None},
        )
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["institution_english"] is None
