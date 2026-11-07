"""The whole life of an approved English version.

Quickstart Scenarios 6 to 10 and 19: a draft is asked for and stored
nowhere, an approval is stored and reused, the user's wording survives
character for character, a blank approval is refused, and deleting an entry
takes its English with it.

The deletion tests stand in for a foreign key.
`entry_translation.entry_id` points at one of four tables depending on
`entry_type`, and PostgreSQL has no referential integrity across a
discriminated reference — so there is nothing to rely on, and these are
what rely on it instead (FR-024): one per translatable type, each failing
if the service stops removing that type's rows.

What survives a lost cascade is not a stray row. It is the user's approved
English for something they deleted, still in the profile and now in the
export archive, with no entry left to show it against.
"""

import io
import uuid
from datetime import UTC, date, datetime

import pytest
from app.career import models as career_models
from app.career import service as career
from app.career import stories as story_service
from app.translations.models import EntryTranslation, TranslatableEntry
from pypdf import PdfReader
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


# --- Scenarios 6 to 10: drafting and approving ------------------------------

TRANSLATIONS = "/api/v1/profile/translations"
DRAFTS = f"{TRANSLATIONS}/drafts"


@pytest.fixture
def japanese_role(client, auth_headers, profile):
    """One role recorded in Japanese, with a title and a description.

    Invented content. The title is a glossary word so the fake renders it
    predictably, and the description is a sentence so there is something to
    approve that is longer than a label.
    """
    created = client.post(
        "/api/v1/profile/experiences",
        headers=auth_headers,
        json={
            "employer_name": "株式会社サンプル",
            "job_title": "エンジニア",
            "description": "ビルドが遅かった",
            "started_on": "2019-04-01",
        },
    )
    assert created.status_code == 201, created.text
    return uuid.UUID(created.json()["id"])


def _subject(entry_id: uuid.UUID, field: str = "job_title") -> dict:
    return {
        "entry_type": "work_experience",
        "entry_id": str(entry_id),
        "field": field,
    }


class TestADraftIsOfferedAndNeverPlaced:
    """Scenario 6. The half that matters is that nothing is stored."""

    def test_the_draft_comes_back_with_its_source_beside_it(
        self, client, auth_headers, japanese_role
    ):
        response = client.post(DRAFTS, headers=auth_headers, json=_subject(japanese_role))

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["source_text"] == "エンジニア"
        assert body["text"] == "Engineer"
        assert body["entry_id"] == str(japanese_role)
        assert body["field"] == "job_title"

    def test_asking_for_one_stores_nothing(
        self, client, auth_headers, session, profile, japanese_role
    ):
        client.post(DRAFTS, headers=auth_headers, json=_subject(japanese_role))

        assert _remaining(session, profile) == []
        assert client.get(TRANSLATIONS, headers=auth_headers).json() == []

    def test_a_field_already_in_english_is_refused(self, client, auth_headers, profile, session):
        """Rendering English into English invites the model to improve the
        wording, which is the one thing a draft must not do (FR-013)."""
        english = uuid.UUID(
            client.post(
                "/api/v1/profile/experiences",
                headers=auth_headers,
                json={
                    "employer_name": "Example Corp",
                    "job_title": "Software Engineer",
                    "started_on": "2021-04-01",
                },
            ).json()["id"]
        )

        response = client.post(DRAFTS, headers=auth_headers, json=_subject(english))

        assert response.status_code == 422, response.text

    def test_an_empty_field_is_refused(self, client, auth_headers, japanese_role):
        """The role has no stored description of its own to render once the
        description is cleared; there is nothing to translate, and saying so
        is better than returning an empty draft to approve."""
        cleared = client.patch(
            f"/api/v1/profile/experiences/{japanese_role}",
            headers=auth_headers,
            json={"description": ""},
        )
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["description"] == ""

        response = client.post(
            DRAFTS, headers=auth_headers, json=_subject(japanese_role, "description")
        )

        assert response.status_code == 422, response.text

    def test_another_profile_is_a_404(self, client, auth_headers, session, profile, japanese_role):
        """An entry id that is not on this profile is not found, which is
        also all this route will say about whose it might be.

        The caller has a profile and a role of their own, so the 404 is
        about whose entry it is and not about the caller having nothing.
        """
        other = career.get_or_create_profile(session, uuid.uuid4())
        theirs = career_models.WorkExperience(
            profile_id=other.id,
            employer_name="株式会社サンプル",
            employer_name_normalised="サンプル",
            job_title="エンジニア",
            started_on=date(2019, 4, 1),
        )
        session.add(theirs)
        session.flush()

        response = client.post(DRAFTS, headers=auth_headers, json=_subject(theirs.id))

        assert response.status_code == 404, response.text


class TestTheAlternativesAreSurfaced:
    """Scenario 7. The product does not choose between "Manager" and
    "Section Chief" on the user's behalf — that is a claim about how senior
    the role was, and it is the user's to make (R-004, FR-013)."""

    @pytest.fixture
    def drafted(self, client, auth_headers, profile):
        entry = uuid.UUID(
            client.post(
                "/api/v1/profile/experiences",
                headers=auth_headers,
                json={
                    "employer_name": "株式会社サンプル",
                    "job_title": "課長",
                    "started_on": "2019-04-01",
                },
            ).json()["id"]
        )
        response = client.post(DRAFTS, headers=auth_headers, json=_subject(entry))
        assert response.status_code == 200, response.text
        return response.json()

    def test_the_ambiguous_phrase_is_named(self, drafted):
        assert [a["phrase"] for a in drafted["alternatives"]] == ["課長"]

    def test_it_carries_more_than_one_reading(self, drafted):
        options = drafted["alternatives"][0]["options"]

        assert len(set(options)) >= 2, options

    def test_the_draft_uses_one_of_the_readings_it_offers(self, drafted):
        """A draft whose wording is absent from the alternatives beside it
        asks the user to choose between options none of which is what they
        are looking at."""
        assert drafted["text"] in drafted["alternatives"][0]["options"]

    def test_an_unambiguous_title_offers_nothing_to_choose(
        self, client, auth_headers, japanese_role
    ):
        """The distinguishing half: a response that always carried
        alternatives would pass every assertion above and mean nothing."""
        response = client.post(DRAFTS, headers=auth_headers, json=_subject(japanese_role))

        assert response.json()["alternatives"] == []


class TestApprovedOnceAndReusedThereafter:
    """Scenarios 8 and 9. The same work is not asked for twice, and what is
    reused is the user's wording rather than the draft's."""

    def test_the_approval_is_stored_and_read_back(self, client, auth_headers, japanese_role):
        approved = client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json=_subject(japanese_role) | {"text": "Systems Engineer"},
        )

        assert approved.status_code == 200, approved.text
        assert approved.json()["text"] == "Systems Engineer"
        assert approved.json()["is_stale"] is False

        listed = client.get(TRANSLATIONS, headers=auth_headers).json()
        assert [row["text"] for row in listed] == ["Systems Engineer"]

    def test_approving_again_replaces_rather_than_accumulates(
        self, client, auth_headers, session, profile, japanese_role
    ):
        """Correcting your own wording is not an error, and the unique key
        says there is one approved version per field."""
        body = _subject(japanese_role)
        client.put(TRANSLATIONS, headers=auth_headers, json=body | {"text": "Systems Engineer"})
        client.put(TRANSLATIONS, headers=auth_headers, json=body | {"text": "Platform Engineer"})

        rows = _remaining(session, profile)
        assert [row.approved_text for row in rows] == ["Platform Engineer"]

    def test_the_users_wording_reaches_the_document_and_the_drafts_does_not(
        self, client, auth_headers, japanese_role
    ):
        """Scenario 9, character for character (FR-019, SC-011).

        The draft of ビルドが遅かった is "The build was slow". The user says
        something else, and what a prospective employer reads is what the
        user said."""
        drafted = client.post(
            DRAFTS, headers=auth_headers, json=_subject(japanese_role, "description")
        ).json()
        assert drafted["text"] == "The build was slow"

        mine = "Rebuilt the CI pipeline and cut the feedback loop to minutes."
        client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json=_subject(japanese_role, "description") | {"text": mine},
        )
        client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json=_subject(japanese_role) | {"text": "Systems Engineer"},
        )
        _with_a_name(client, auth_headers)

        page = _rendered(client, auth_headers)

        assert mine in page
        assert drafted["text"] not in page

    def test_the_spacing_the_user_typed_is_kept(
        self, client, auth_headers, session, profile, japanese_role
    ):
        """Stored exactly as given means exactly. A system that stripped the
        text would be editing the only thing on the page that is the user's
        own words."""
        client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json=_subject(japanese_role) | {"text": "  Systems Engineer  "},
        )

        assert [row.approved_text for row in _remaining(session, profile)] == [
            "  Systems Engineer  "
        ]


class TestAnApprovedBlankIsNotAnEnglishVersion:
    """Scenario 10 (FR-025). An approved blank would take the entry out of
    the document with nothing to say it had gone, which is worse than having
    no English version at all."""

    @pytest.mark.parametrize("text", ["", "   ", "\n", "\t "])
    def test_it_is_refused(self, client, auth_headers, japanese_role, text):
        response = client.put(
            TRANSLATIONS, headers=auth_headers, json=_subject(japanese_role) | {"text": text}
        )

        assert response.status_code == 422, response.text

    def test_nothing_is_stored_by_the_refusal(
        self, client, auth_headers, session, profile, japanese_role
    ):
        client.put(TRANSLATIONS, headers=auth_headers, json=_subject(japanese_role) | {"text": " "})

        assert _remaining(session, profile) == []

    def test_a_previous_approval_survives_a_refused_one(
        self, client, auth_headers, session, profile, japanese_role
    ):
        """A blank must not be a way to clear an approval by accident. The
        route for removing one is the delete route, which the user reaches
        deliberately."""
        body = _subject(japanese_role)
        client.put(TRANSLATIONS, headers=auth_headers, json=body | {"text": "Systems Engineer"})

        client.put(TRANSLATIONS, headers=auth_headers, json=body | {"text": "   "})

        assert [row.approved_text for row in _remaining(session, profile)] == ["Systems Engineer"]


class TestRemovingAnApproval:
    def test_the_entry_reverts_to_having_none(
        self, client, auth_headers, session, profile, japanese_role
    ):
        stored = client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json=_subject(japanese_role) | {"text": "Systems Engineer"},
        ).json()

        removed = client.delete(f"{TRANSLATIONS}/{stored['id']}", headers=auth_headers)

        assert removed.status_code == 204, removed.text
        assert _remaining(session, profile) == []

    def test_another_profiles_approval_is_not_found(
        self, client, auth_headers, session, profile, japanese_role
    ):
        """The caller has an approval of their own, so a route that deleted
        by id alone would find the other profile's row rather than answer
        404 because there was nothing anywhere."""
        client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json=_subject(japanese_role) | {"text": "Systems Engineer"},
        )
        other = career.get_or_create_profile(session, uuid.uuid4())
        _approved(session, other, TranslatableEntry.skill, uuid.uuid4())
        theirs = _remaining(session, other)[0]

        response = client.delete(f"{TRANSLATIONS}/{theirs.id}", headers=auth_headers)

        assert response.status_code == 404, response.text
        assert len(_remaining(session, other)) == 1


class TestAFieldTheEntryDoesNotHave:
    """422 rather than 404: the entry was found, and what cannot be done is
    what was asked of it. A rendering stored against a column the entry does
    not carry is a row nothing will ever read back."""

    @pytest.mark.parametrize("field", ["employer_name", "challenge", "nonsense"])
    def test_approving_one_is_refused(self, client, auth_headers, japanese_role, field):
        response = client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json=_subject(japanese_role, field) | {"text": "Example Corp"},
        )

        assert response.status_code == 422, response.text

    def test_the_fields_it_does_have_are_named(self, client, auth_headers, japanese_role):
        response = client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json=_subject(japanese_role, "employer_name") | {"text": "Example Corp"},
        )

        assert "job_title" in response.json()["message"]

    def test_an_employer_name_is_not_one_of_them(self, client, auth_headers, japanese_role):
        """And it never will be. A company's English name is the name it
        uses, not a rendering of its Japanese one, so it is a column on the
        entry and nothing drafts it (FR-021, R-002)."""
        response = client.put(
            TRANSLATIONS,
            headers=auth_headers,
            json=_subject(japanese_role, "employer_name") | {"text": "Sample Corporation"},
        )

        assert "employer_name" not in response.json()["message"]


def _with_a_name(client, auth_headers) -> None:
    """A resume needs a name before it can be produced (FR-006)."""
    client.put(
        "/api/v1/profile/identity",
        headers=auth_headers,
        json={"full_name_latin": "Taro Yamada"},
    )


def _rendered(client, auth_headers) -> str:
    response = client.post("/api/v1/profile/documents/resume", headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(response.content)).pages
    )
