"""The translation routes against what their contract promises.

`test_contracts.py` checks that every documented path and method is served,
and `test_response_schemas.py` checks that the bodies match their schemas.
Neither checks that the documented *failures* happen, which is where a
client written from the contract gets hurt: 502 and 503 are documented
separately so the interface can say "try again" to one and not the other,
and a route that returned 500 for both would pass every other test in this
directory.
"""

import uuid
from pathlib import Path

import pytest
import yaml
from app.ai.fake import FakeAIProvider

CONTRACT = (
    Path(__file__).resolve().parents[4]
    / "specs"
    / "005-english-resume"
    / "contracts"
    / "openapi.yaml"
)
ROUTE = "/profile/translations"
DRAFTS_ROUTE = f"{ROUTE}/drafts"
PATH = f"/api/v1{ROUTE}"
DRAFTS = f"/api/v1{DRAFTS_ROUTE}"


@pytest.fixture(scope="module")
def contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture
def profile(client, auth_headers):
    created = client.post("/api/v1/profile", headers=auth_headers)
    assert created.status_code == 201, created.text
    return created.json()


@pytest.fixture
def entry(client, auth_headers, profile) -> str:
    """One role recorded in Japanese. Invented content."""
    created = client.post(
        "/api/v1/profile/experiences",
        headers=auth_headers,
        json={
            "employer_name": "株式会社サンプル",
            "job_title": "課長",
            "started_on": "2019-04-01",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _subject(entry_id: str) -> dict:
    return {"entry_type": "work_experience", "entry_id": entry_id, "field": "job_title"}


def _statuses(contract: dict, route: str, method: str) -> set[str]:
    return set(contract["paths"][route][method]["responses"])


class TestEveryDocumentedStatusActuallyHappens:
    """Each documented status, reached by the condition the contract gives
    as its description. A status nobody can produce is a status the
    interface has written a branch for and will never run."""

    def test_the_documented_set_is_the_one_these_tests_cover(self, contract):
        """If a status is added to the contract, this fails until it is
        either produced below or deliberately excluded here."""
        assert _statuses(contract, ROUTE, "put") == {"200", "401", "404", "422"}
        assert _statuses(contract, ROUTE, "get") == {"200", "401", "404"}
        assert _statuses(contract, f"{ROUTE}/{{translation_id}}", "delete") == {
            "204",
            "401",
            "404",
        }
        assert _statuses(contract, DRAFTS_ROUTE, "post") == {
            "200",
            "401",
            "404",
            "422",
            "502",
            "503",
        }

    def test_approving_returns_200(self, client, auth_headers, entry):
        response = client.put(
            PATH, headers=auth_headers, json=_subject(entry) | {"text": "Manager"}
        )

        assert response.status_code == 200, response.text

    def test_a_blank_approval_returns_422(self, client, auth_headers, entry):
        response = client.put(PATH, headers=auth_headers, json=_subject(entry) | {"text": " "})

        assert response.status_code == 422, response.text

    def test_an_entry_on_no_profile_returns_404(self, client, auth_headers, profile):
        body = _subject(str(uuid.uuid4())) | {"text": "Manager"}

        assert client.put(PATH, headers=auth_headers, json=body).status_code == 404

    def test_listing_without_a_profile_returns_404(self, client, auth_headers):
        assert client.get(PATH, headers=auth_headers).status_code == 404

    def test_an_unauthorised_caller_returns_401(self, client):
        assert client.get(PATH).status_code == 401

    def test_deleting_returns_204_and_no_body(self, client, auth_headers, entry):
        stored = client.put(
            PATH, headers=auth_headers, json=_subject(entry) | {"text": "Manager"}
        ).json()

        response = client.delete(f"{PATH}/{stored['id']}", headers=auth_headers)

        assert response.status_code == 204, response.text
        assert not response.content

    def test_deleting_something_that_is_not_there_returns_404(self, client, auth_headers, profile):
        response = client.delete(f"{PATH}/{uuid.uuid4()}", headers=auth_headers)

        assert response.status_code == 404, response.text

    def test_drafting_returns_200(self, client, auth_headers, entry):
        assert client.post(DRAFTS, headers=auth_headers, json=_subject(entry)).status_code == 200

    def test_drafting_what_is_already_english_returns_422(self, client, auth_headers, profile):
        english = client.post(
            "/api/v1/profile/experiences",
            headers=auth_headers,
            json={
                "employer_name": "Example Corp",
                "job_title": "Software Engineer",
                "started_on": "2021-04-01",
            },
        ).json()["id"]

        response = client.post(DRAFTS, headers=auth_headers, json=_subject(english))

        assert response.status_code == 422, response.text


class TestTheTwoWaysDraftingFails:
    """Documented as two statuses because they are two situations, and a
    person cannot tell them apart from the failure itself. One is worth
    coming back to in five minutes; the other never will be."""

    @pytest.fixture
    def failing(self, monkeypatch):
        def arrange(behaviour: str) -> None:
            monkeypatch.setattr(
                "app.translations.drafting.get_provider",
                lambda: FakeAIProvider(behaviour),
            )

        return arrange

    def test_an_unreachable_service_is_503(self, client, auth_headers, entry, failing):
        failing("unavailable")

        response = client.post(DRAFTS, headers=auth_headers, json=_subject(entry))

        assert response.status_code == 503, response.text

    def test_an_unusable_answer_is_502(self, client, auth_headers, entry, failing):
        failing("invalid")

        response = client.post(DRAFTS, headers=auth_headers, json=_subject(entry))

        assert response.status_code == 502, response.text

    @pytest.mark.parametrize(("behaviour", "status"), [("unavailable", 503), ("invalid", 502)])
    def test_the_documented_error_shape_comes_back(
        self, client, auth_headers, entry, failing, contract, behaviour, status
    ):
        """Both are documented as `Error`, so both must carry a code and a
        message the interface can show rather than a bare status."""
        failing(behaviour)

        response = client.post(DRAFTS, headers=auth_headers, json=_subject(entry))

        assert response.status_code == status, response.text
        documented = contract["components"]["schemas"]["Error"]["required"]
        assert set(documented) <= set(response.json()), response.text

    def test_a_momentary_outage_is_retried_rather_than_reported(
        self, client, auth_headers, entry, monkeypatch
    ):
        """The distinguishing case. Without it, a route that gave up on the
        first failure would pass both tests above — and a user would lose a
        draft to a dropped connection."""
        provider = FakeAIProvider(fail_times=1)
        monkeypatch.setattr("app.translations.drafting.get_provider", lambda: provider)

        response = client.post(DRAFTS, headers=auth_headers, json=_subject(entry))

        assert response.status_code == 200, response.text
        assert provider.calls == 2


class TestWhatTheListRouteIsDocumentedToTake:
    def test_the_stale_filter_is_a_documented_parameter(self, contract):
        documented = {p["name"] for p in contract["paths"][ROUTE]["get"].get("parameters", [])}

        assert "stale" in documented

    def test_it_narrows_the_list(self, client, auth_headers, entry):
        client.put(PATH, headers=auth_headers, json=_subject(entry) | {"text": "Manager"})

        assert len(client.get(PATH, headers=auth_headers).json()) == 1
        assert client.get(f"{PATH}?stale=true", headers=auth_headers).json() == []
        assert len(client.get(f"{PATH}?stale=false", headers=auth_headers).json()) == 1
