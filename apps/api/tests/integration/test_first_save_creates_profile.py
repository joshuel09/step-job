"""The first thing a user records makes their profile (#154).

Nothing in the product asks a user to create a profile, and no interface has a
button for it: the profile is the container their entries go in. Before this,
every write from a new account answered 404 because the row did not exist yet,
so FR-001 — users must be able to record and edit their identity — was not
true for anybody on their first visit.

A profile inside its recovery window is the one case that must not be created
through. It still holds the user id, so a second row cannot be written, and
reviving it would undo a deletion the user asked for. FR-027 says a deleted
profile is unreadable, and these tests hold the line that it is also unwritable.
"""

import uuid

from app.career.models import CareerProfile
from app.db.soft_delete import with_deleted
from sqlalchemy import select

IDENTITY = {
    "full_name_latin": "Taro Yamada",
    "full_name_japanese": "山田太郎",
    "furigana": "やまだたろう",
    "date_of_birth": "1990-04-01",
    "address": "東京都渋谷区1-2-3",
    "email": "taro@example.com",
    "phone": "090-1234-5678",
}

EXPERIENCE = {
    "employer_name": "Example Corp",
    "job_title": "Software Engineer",
    "started_on": "2021-04-01",
    "ended_on": None,
    "source_language": "en",
}

STORY = {
    "title": "Cut the build in half",
    "challenge": "The build took forty minutes.",
    "action": "Split it and cached the slow step.",
    "result": "Twenty minutes.",
    "source_language": "en",
}


def _profiles(session, user_id: uuid.UUID) -> list[CareerProfile]:
    """Every profile row for a user, deleted ones included."""
    with with_deleted(session):
        return list(session.scalars(select(CareerProfile).where(CareerProfile.user_id == user_id)))


class TestTheFirstThingRecorded:
    """A new account, with nothing created in advance."""

    def test_identity_saves_and_can_be_read_back(self, client, auth_headers):
        saved = client.put("/api/v1/profile/identity", headers=auth_headers, json=IDENTITY)
        assert saved.status_code == 200, saved.text

        profile = client.get("/api/v1/profile", headers=auth_headers)
        assert profile.status_code == 200
        assert profile.json()["identity"]["full_name_latin"] == "Taro Yamada"

    def test_an_experience_saves(self, client, auth_headers):
        created = client.post("/api/v1/profile/experiences", headers=auth_headers, json=EXPERIENCE)
        assert created.status_code == 201, created.text
        assert client.get("/api/v1/profile", headers=auth_headers).json()["experiences"]

    def test_a_story_saves(self, client, auth_headers):
        created = client.post("/api/v1/profile/stories", headers=auth_headers, json=STORY)
        assert created.status_code == 201, created.text

    def test_a_section_entry_saves(self, client, auth_headers):
        created = client.post(
            "/api/v1/profile/skills",
            headers=auth_headers,
            json={"name": "SQL", "level": "advanced"},
        )
        assert created.status_code == 201, created.text

    def test_japan_fields_save(self, client, auth_headers):
        saved = client.put(
            "/api/v1/profile/japan",
            headers=auth_headers,
            json={"work_authorisation": True},
        )
        assert saved.status_code == 200, saved.text

    def test_preferences_save(self, client, auth_headers):
        saved = client.put(
            "/api/v1/profile/preferences",
            headers=auth_headers,
            json={"desired_roles": ["Engineer"]},
        )
        assert saved.status_code == 200, saved.text

    def test_choosing_a_language_is_enough(self, client, auth_headers):
        """The switch is in every header, so it is often the first thing touched."""
        chosen = client.patch(
            "/api/v1/profile", headers=auth_headers, json={"interface_locale": "ja"}
        )
        assert chosen.status_code == 200, chosen.text
        stored = client.get("/api/v1/profile", headers=auth_headers).json()
        assert stored["interface_locale"] == "ja"

    def test_an_import_can_be_the_first_thing_a_user_does(self, client, auth_headers):
        """Arriving with a resume to paste is a first action like any other."""
        started = client.post(
            "/api/v1/profile/imports",
            headers=auth_headers,
            json={"text": "Software Engineer at Example Corp, 2021 to 2024."},
        )
        assert started.status_code == 201, started.text

    def test_two_saves_make_one_profile(self, client, auth_headers, session, user_id):
        client.put("/api/v1/profile/identity", headers=auth_headers, json=IDENTITY)
        client.post("/api/v1/profile/experiences", headers=auth_headers, json=EXPERIENCE)

        assert len(_profiles(session, user_id)) == 1


class TestReadsStillSayThereIsNothing:
    """Creating on a write does not mean inventing one on a read."""

    def test_reading_a_profile_that_was_never_recorded_is_a_404(self, client, auth_headers):
        assert client.get("/api/v1/profile", headers=auth_headers).status_code == 404

    def test_a_read_leaves_no_profile_behind(self, client, auth_headers, session, user_id):
        client.get("/api/v1/profile", headers=auth_headers)
        assert _profiles(session, user_id) == []

    def test_a_document_still_refuses_without_a_profile(self, client, auth_headers):
        """There is nothing to build a 履歴書 from, which is the documented 404."""
        response = client.post("/api/v1/profile/documents/rirekisho", headers=auth_headers)
        assert response.status_code == 404


class TestADeletedProfileIsNotRevived:
    """FR-027: inside the recovery window the profile is gone, restore aside."""

    def _deleted(self, client, headers) -> None:
        saved = client.put("/api/v1/profile/identity", headers=headers, json=IDENTITY)
        assert saved.status_code == 200, saved.text
        assert client.delete("/api/v1/profile", headers=headers).status_code == 200

    def test_a_write_does_not_bring_it_back(self, client, auth_headers):
        self._deleted(client, auth_headers)

        response = client.put("/api/v1/profile/identity", headers=auth_headers, json=IDENTITY)
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"

    def test_a_write_makes_no_second_profile(self, client, auth_headers, session, user_id):
        self._deleted(client, auth_headers)
        client.post("/api/v1/profile/experiences", headers=auth_headers, json=EXPERIENCE)

        rows = _profiles(session, user_id)
        assert len(rows) == 1, "the user id is unique; a second row cannot exist"
        assert rows[0].deleted_at is not None, "and the one row is still deleted"

    def test_creating_a_profile_outright_is_refused_rather_than_crashing(
        self, client, auth_headers
    ):
        """POST /profile used to reach the unique constraint and return a 500."""
        self._deleted(client, auth_headers)

        assert client.post("/api/v1/profile", headers=auth_headers).status_code == 404

    def test_restore_is_still_the_way_back(self, client, auth_headers):
        self._deleted(client, auth_headers)

        assert client.post("/api/v1/profile/restore", headers=auth_headers).status_code == 200
        identity = client.get("/api/v1/profile", headers=auth_headers).json()["identity"]
        assert identity["full_name_latin"] == "Taro Yamada"
