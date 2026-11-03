"""Quickstart Scenario 19 — deleting an entry takes its English with it.

`entry_translation.entry_id` points at one of four tables depending on
`entry_type`, and PostgreSQL has no referential integrity across a
discriminated reference. So there is no foreign key to rely on, and these
tests are what stands in for one (FR-024): one per translatable type, each
failing if the service stops removing that type's rows.

What survives a lost cascade is not a stray row. It is the user's approved
English for something they deleted, still in the profile and now in the
export archive, with no entry left to show it against.
"""

import uuid
from datetime import UTC, datetime

import pytest
from app.career import service as career
from app.career import stories as story_service
from app.translations.models import EntryTranslation, TranslatableEntry
from sqlalchemy import select


@pytest.fixture
def profile(session, user_id):
    return career.get_or_create_profile(session, user_id)


def _approved(session, profile, entry_type: TranslatableEntry, entry_id: uuid.UUID):
    session.add(
        EntryTranslation(
            profile_id=profile.id,
            entry_type=entry_type,
            entry_id=entry_id,
            field="title",
            approved_text="Cut the build in half",
            approved_at=datetime.now(UTC),
            source_fingerprint="0" * 64,
        )
    )
    session.flush()


def _remaining(session, profile) -> list[EntryTranslation]:
    return list(
        session.scalars(select(EntryTranslation).where(EntryTranslation.profile_id == profile.id))
    )


class TestTheEnglishGoesWithTheEntry:
    def test_a_work_experience(self, client, auth_headers, session, profile):
        created = client.post(
            "/api/v1/profile/experiences",
            headers=auth_headers,
            json={
                "employer_name": "株式会社サンプル",
                "job_title": "エンジニア",
                "started_on": "2020-04-01",
            },
        )
        entry_id = uuid.UUID(created.json()["id"])
        _approved(session, profile, TranslatableEntry.work_experience, entry_id)

        deleted = client.delete(
            f"/api/v1/profile/experiences/{entry_id}?confirm=true", headers=auth_headers
        )
        assert deleted.status_code == 204, deleted.text
        assert _remaining(session, profile) == []

    def test_an_education_entry(self, client, auth_headers, session, profile):
        created = client.post(
            "/api/v1/profile/education",
            headers=auth_headers,
            json={"institution": "サンプル大学"},
        )
        entry_id = uuid.UUID(created.json()["id"])
        _approved(session, profile, TranslatableEntry.education, entry_id)

        assert (
            client.delete(f"/api/v1/profile/education/{entry_id}", headers=auth_headers).status_code
            == 204
        )
        assert _remaining(session, profile) == []

    def test_a_skill(self, client, auth_headers, session, profile):
        created = client.post(
            "/api/v1/profile/skills", headers=auth_headers, json={"name": "Python"}
        )
        entry_id = uuid.UUID(created.json()["id"])
        _approved(session, profile, TranslatableEntry.skill, entry_id)

        assert (
            client.delete(f"/api/v1/profile/skills/{entry_id}", headers=auth_headers).status_code
            == 204
        )
        assert _remaining(session, profile) == []

    def test_a_career_story(self, client, auth_headers, session, profile):
        created = client.post(
            "/api/v1/profile/stories",
            headers=auth_headers,
            json={
                "title": "ビルド時間を半分にした",
                "challenge": "ビルドが遅かった",
                "action": "キャッシュを導入した",
                "result": "半分になった",
            },
        )
        assert created.status_code == 201, created.text
        entry_id = uuid.UUID(created.json()["id"])
        _approved(session, profile, TranslatableEntry.career_story, entry_id)

        assert (
            client.delete(f"/api/v1/profile/stories/{entry_id}", headers=auth_headers).status_code
            == 204
        )
        assert _remaining(session, profile) == []


class TestWhatIsLeftAlone:
    def test_another_entry_keeps_its_english(self, client, auth_headers, session, profile):
        """The deletion is scoped to the entry, not swept across the type."""
        kept, gone = (
            uuid.UUID(
                client.post(
                    "/api/v1/profile/skills", headers=auth_headers, json={"name": name}
                ).json()["id"]
            )
            for name in ("Python", "Go")
        )
        _approved(session, profile, TranslatableEntry.skill, kept)
        _approved(session, profile, TranslatableEntry.skill, gone)

        client.delete(f"/api/v1/profile/skills/{gone}", headers=auth_headers)

        assert [t.entry_id for t in _remaining(session, profile)] == [kept]

    def test_a_story_outlives_the_employer_and_so_does_its_english(
        self, client, auth_headers, session, profile
    ):
        """A story detaches rather than dying when its employer is deleted
        (`ondelete="SET NULL"`), so its English must not be swept up with
        the employer's. The story is still in the profile, and the closing
        section of a 職務経歴書 still prints it."""
        experience = uuid.UUID(
            client.post(
                "/api/v1/profile/experiences",
                headers=auth_headers,
                json={
                    "employer_name": "株式会社サンプル",
                    "job_title": "エンジニア",
                    "started_on": "2020-04-01",
                },
            ).json()["id"]
        )
        story = uuid.UUID(
            client.post(
                "/api/v1/profile/stories",
                headers=auth_headers,
                json={
                    "work_experience_id": str(experience),
                    "title": "ビルド時間を半分にした",
                    "challenge": "ビルドが遅かった",
                    "action": "キャッシュを導入した",
                    "result": "半分になった",
                },
            ).json()["id"]
        )
        _approved(session, profile, TranslatableEntry.career_story, story)

        assert (
            client.delete(
                f"/api/v1/profile/experiences/{experience}?confirm=true", headers=auth_headers
            ).status_code
            == 204
        )

        assert [t.entry_id for t in _remaining(session, profile)] == [story]
        assert story_service.get(session, profile, story) is not None

    def test_another_profile_is_never_reached(self, session, profile, user_id):
        """Scoped by profile as well as by entry, so an `entry_id` that
        collided across profiles could not take someone else's English."""
        from app.translations import service as translations

        other = career.get_or_create_profile(session, uuid.uuid4())
        shared = uuid.uuid4()
        _approved(session, profile, TranslatableEntry.skill, shared)
        _approved(session, other, TranslatableEntry.skill, shared)

        removed = translations.delete_for_entry(
            session, profile.id, TranslatableEntry.skill, shared
        )

        assert removed == 1
        assert len(_remaining(session, other)) == 1
