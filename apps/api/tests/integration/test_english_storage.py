"""Somewhere for an approved English version to live (feature 005, Phase 2).

Two kinds of English, stored two ways on purpose, and the test for each is
different in kind:

- A **supplied name** is a fact the user states, so the check is that it
  reaches the profile through the routes they already use and comes back as
  written. A column nothing can set is not shipped.
- An **approved rendering** is the product's draft that the user accepted,
  so the check is that one field of one entry holds exactly one of them, and
  that it carries the digest of the source as it read at the time.
"""

import uuid
from datetime import UTC, datetime

import pytest
from app.translations.fingerprint import fingerprint
from app.translations.models import EntryTranslation, NamedEntry, TranslatableEntry
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def profile(session, user_id):
    from app.career import service

    return service.get_or_create_profile(session, user_id)


class TestASuppliedEnglishName:
    def test_an_employer_carries_one(self, client, auth_headers, profile):
        created = client.post(
            "/api/v1/profile/experiences",
            headers=auth_headers,
            json={
                "employer_name": "株式会社サンプル",
                "employer_name_english": "Sample Corporation",
                "job_title": "エンジニア",
                "started_on": "2020-04-01",
            },
        )
        assert created.status_code == 201, created.text
        assert created.json()["employer_name_english"] == "Sample Corporation"

    def test_an_institution_carries_one(self, client, auth_headers, profile):
        created = client.post(
            "/api/v1/profile/education",
            headers=auth_headers,
            json={"institution": "サンプル大学", "institution_english": "Sample University"},
        )
        assert created.status_code == 201, created.text
        assert created.json()["institution_english"] == "Sample University"

    def test_a_certification_carries_both(self, client, auth_headers, profile):
        created = client.post(
            "/api/v1/profile/certifications",
            headers=auth_headers,
            json={
                "name": "基本情報技術者",
                "name_english": "Fundamental Information Technology Engineer",
                "issuer": "情報処理推進機構",
                "issuer_english": "Information-technology Promotion Agency",
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["name_english"] == "Fundamental Information Technology Engineer"
        assert body["issuer_english"] == "Information-technology Promotion Agency"

    def test_it_can_be_added_later(self, client, auth_headers, profile):
        """The usual case: the entry exists and the user supplies the name
        afterwards, from the page that lists what is missing."""
        created = client.post(
            "/api/v1/profile/experiences",
            headers=auth_headers,
            json={
                "employer_name": "株式会社サンプル",
                "job_title": "エンジニア",
                "started_on": "2020-04-01",
            },
        )
        assert created.json()["employer_name_english"] is None

        patched = client.patch(
            f"/api/v1/profile/experiences/{created.json()['id']}",
            headers=auth_headers,
            json={"employer_name_english": "Sample Corporation"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["employer_name_english"] == "Sample Corporation"
        assert patched.json()["employer_name"] == "株式会社サンプル", "the Japanese is untouched"

    def test_absent_means_absent_and_not_a_guess(self, client, auth_headers, profile):
        """FR-021. Nothing transliterates 株式会社サンプル into anything."""
        created = client.post(
            "/api/v1/profile/experiences",
            headers=auth_headers,
            json={
                "employer_name": "株式会社サンプル",
                "job_title": "エンジニア",
                "started_on": "2020-04-01",
            },
        )
        assert created.json()["employer_name_english"] is None


class TestAnApprovedRendering:
    def _translation(self, profile_id, **overrides):
        values = {
            "profile_id": profile_id,
            "entry_type": TranslatableEntry.career_story,
            "entry_id": uuid.uuid4(),
            "field": "title",
            "approved_text": "Cut the build in half",
            "approved_at": datetime.now(UTC),
            "source_fingerprint": fingerprint("ビルド時間を半分にした"),
        }
        values.update(overrides)
        return EntryTranslation(**values)

    def test_it_is_stored_and_read_back_as_approved(self, session, profile):
        row = self._translation(profile.id)
        session.add(row)
        session.flush()

        found = session.scalars(
            select(EntryTranslation).where(EntryTranslation.profile_id == profile.id)
        ).one()
        assert found.approved_text == "Cut the build in half"
        assert found.field == "title"
        assert found.language.value == "en"

    def test_it_carries_the_digest_of_the_source_at_the_time(self, session, profile):
        row = self._translation(profile.id)
        session.add(row)
        session.flush()

        assert row.source_fingerprint == fingerprint("ビルド時間を半分にした")
        assert row.source_fingerprint != fingerprint("ビルド時間を三分の一にした")

    def test_one_field_holds_one_approved_version(self, session, profile):
        """Replaced rather than accumulated: a second row would make "the
        approved text" a question with two answers.

        The duplicate goes in a savepoint, so rolling back the failure
        leaves the surrounding transaction — which the test fixture owns —
        where it was.
        """
        entry = uuid.uuid4()
        session.add(self._translation(profile.id, entry_id=entry))
        session.flush()

        savepoint = session.begin_nested()
        session.add(self._translation(profile.id, entry_id=entry, approved_text="Something else"))
        with pytest.raises(IntegrityError):
            session.flush()
        savepoint.rollback()

        assert (
            len(
                session.scalars(
                    select(EntryTranslation).where(EntryTranslation.entry_id == entry)
                ).all()
            )
            == 1
        )

    def test_two_fields_of_one_entry_are_two_rows(self, session, profile):
        entry = uuid.uuid4()
        session.add(self._translation(profile.id, entry_id=entry, field="title"))
        session.add(self._translation(profile.id, entry_id=entry, field="challenge"))
        session.flush()

        assert (
            len(
                session.scalars(
                    select(EntryTranslation).where(EntryTranslation.entry_id == entry)
                ).all()
            )
            == 2
        )


class TestWhatMayBeDrafted:
    def test_a_certification_is_in_no_translation(self):
        """It holds a name, an issuer and two dates: the first two are proper
        nouns and the last two are not words, so there is nothing on it a
        model could draft (R-002)."""
        assert "certification" not in {entry.value for entry in TranslatableEntry}

    def test_but_it_does_carry_a_supplied_name(self):
        assert "certification" in {entry.value for entry in NamedEntry}

    def test_the_two_lists_are_not_the_same_list(self):
        """A name the user states and a rendering the product drafted are
        different kinds of fact, and only one of them can go stale."""
        assert {e.value for e in TranslatableEntry} != {e.value for e in NamedEntry}

    def test_every_translatable_entry_is_a_table_the_profile_has(self):
        from app.career import models

        tables = {
            "work_experience": models.WorkExperience,
            "education": models.Education,
            "career_story": models.CareerStory,
            "skill": models.Skill,
        }
        assert {e.value for e in TranslatableEntry} == set(tables)
