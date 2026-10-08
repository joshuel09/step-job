"""What the routes actually return, against what the contracts promise.

`test_contracts.py` checks that documented paths exist and documented methods
are served. Neither says anything about the body. A route could answer with a
shape its contract does not describe and every one of those tests would pass,
while the generated client compiled against a shape the API never produces.

So these tests send real requests and validate the real responses. The error
shapes are covered alongside the success ones, because `Error` and
`ValidationError` are shared by all three features and drift quietly.

UNVALIDATED below is the honest edge of this file, in the same spirit as
DEFERRED in `test_contracts.py`: an operation is either checked here or named
there. Adding a route without doing one of the two fails the last test.
"""

import uuid

import pytest
from jsonschema import Draft202012Validator

from .schemas import contract, response_schema

CAREER = "001-master-career-profile"
IMPORTS = "002-ai-resume-import"
DOCUMENTS = "003-rirekisho-generator"
SHOKUMU = "004-shokumu-keirekisho"

# Every (feature, path, method, status) this file has validated. Recorded as the
# tests run so the coverage check below reflects what actually happened rather
# than what someone intended.
VALIDATED: set[tuple[str, str, str, str]] = set()


def check(feature: str, path: str, method: str, status: int, body) -> None:
    """Validate one response body against its documented schema.

    Reports every mismatch at once, each with the field it is about. A
    validator that stops at the first problem turns one contract fix into a
    dozen runs.
    """
    schema = response_schema(feature, path, method, status)
    errors = sorted(Draft202012Validator(schema).iter_errors(body), key=lambda e: e.json_path)
    if errors:
        detail = "\n".join(f"  {e.json_path}: {e.message}" for e in errors)
        raise AssertionError(
            f"{feature}: {method.upper()} {path} -> {status} does not match its contract:\n{detail}"
        )
    VALIDATED.add((feature, path, method.lower(), str(status)))


@pytest.fixture
def profile(client, auth_headers):
    created = client.post("/api/v1/profile", headers=auth_headers)
    assert created.status_code == 201, created.text
    return created.json()


# --- the profile itself ------------------------------------------------------


class TestProfile:
    def test_reading_a_profile(self, client, auth_headers, profile):
        response = client.get("/api/v1/profile", headers=auth_headers)
        assert response.status_code == 200
        check(CAREER, "/profile", "get", 200, response.json())

    def test_changing_the_interface_language(self, client, auth_headers, profile):
        response = client.patch(
            "/api/v1/profile", headers=auth_headers, json={"interface_locale": "ja"}
        )
        assert response.status_code == 200
        check(CAREER, "/profile", "patch", 200, response.json())

    def test_completeness(self, client, auth_headers, profile):
        response = client.get("/api/v1/profile/completeness", headers=auth_headers)
        assert response.status_code == 200
        check(CAREER, "/profile/completeness", "get", 200, response.json())

    def test_setting_an_identity(self, client, auth_headers, profile):
        response = client.put(
            "/api/v1/profile/identity",
            headers=auth_headers,
            json={"full_name_latin": "Taro Yamada", "full_name_japanese": "山田太郎"},
        )
        assert response.status_code == 200
        check(CAREER, "/profile/identity", "put", 200, response.json())

    def test_deleting_a_profile(self, client, auth_headers, profile):
        response = client.delete("/api/v1/profile", headers=auth_headers)
        assert response.status_code == 200
        check(CAREER, "/profile", "delete", 200, response.json())

    def test_restoring_a_profile(self, client, auth_headers, profile):
        assert client.delete("/api/v1/profile", headers=auth_headers).status_code == 200
        response = client.post("/api/v1/profile/restore", headers=auth_headers)
        assert response.status_code == 200
        check(CAREER, "/profile/restore", "post", 200, response.json())


# --- the repeated section shape ----------------------------------------------

# One valid create body per section, taken from the contract's required fields.
SECTIONS = {
    "experiences": {
        "employer_name": "Example Corp",
        "job_title": "Software Engineer",
        "started_on": "2021-04-01",
        "source_language": "en",
    },
    "education": {"institution": "Example University", "qualification": "BSc"},
    "certifications": {"name": "Example Certification"},
    "skills": {"name": "Python"},
    "languages": {"language": "Japanese", "proficiency": "business"},
}


@pytest.mark.parametrize("section", sorted(SECTIONS))
class TestSections:
    def test_creating_an_entry(self, client, auth_headers, profile, section):
        response = client.post(
            f"/api/v1/profile/{section}", headers=auth_headers, json=SECTIONS[section]
        )
        assert response.status_code == 201, response.text
        check(CAREER, f"/profile/{section}", "post", 201, response.json())

    def test_listing_entries(self, client, auth_headers, profile, section):
        client.post(f"/api/v1/profile/{section}", headers=auth_headers, json=SECTIONS[section])
        response = client.get(f"/api/v1/profile/{section}", headers=auth_headers)
        assert response.status_code == 200
        check(CAREER, f"/profile/{section}", "get", 200, response.json())

    def test_rejecting_an_invalid_entry(self, client, auth_headers, profile, section):
        """The shared ValidationError shape, which the interface reads field by field."""
        response = client.post(f"/api/v1/profile/{section}", headers=auth_headers, json={})
        assert response.status_code == 422, response.text
        check(CAREER, f"/profile/{section}", "post", 422, response.json())


class TestOneExperience:
    """The per-entry routes, which only `experiences` documents in full."""

    @pytest.fixture
    def experience_id(self, client, auth_headers, profile) -> str:
        created = client.post(
            "/api/v1/profile/experiences", headers=auth_headers, json=SECTIONS["experiences"]
        )
        assert created.status_code == 201, created.text
        return created.json()["id"]

    def test_reading_one(self, client, auth_headers, experience_id):
        response = client.get(f"/api/v1/profile/experiences/{experience_id}", headers=auth_headers)
        assert response.status_code == 200
        check(CAREER, "/profile/experiences/{experience_id}", "get", 200, response.json())

    def test_changing_one(self, client, auth_headers, experience_id):
        response = client.patch(
            f"/api/v1/profile/experiences/{experience_id}",
            headers=auth_headers,
            json={"job_title": "Senior Software Engineer"},
        )
        assert response.status_code == 200
        check(CAREER, "/profile/experiences/{experience_id}", "patch", 200, response.json())

    def test_reading_one_that_is_not_there(self, client, auth_headers, profile):
        response = client.get(f"/api/v1/profile/experiences/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404
        check(CAREER, "/profile/experiences/{experience_id}", "get", 404, response.json())


# The per-entry path parameter is named per section in the contract.
ENTRY_PARAM = {
    "education": "entry_id",
    "certifications": "entry_id",
    "skills": "entry_id",
    "languages": "entry_id",
}

PATCHES = {
    "education": {"qualification": "MSc"},
    "certifications": {"issuer": "Example Board"},
    "skills": {"level": "advanced"},
    "languages": {"proficiency": "native"},
}


@pytest.mark.parametrize("section", sorted(PATCHES))
def test_changing_one_entry(client, auth_headers, profile, section):
    created = client.post(
        f"/api/v1/profile/{section}", headers=auth_headers, json=SECTIONS[section]
    )
    assert created.status_code == 201, created.text

    entry_id = created.json()["id"]
    # These routes document the whole entry as the body rather than a partial
    # one, so a change is sent as the full record.
    response = client.patch(
        f"/api/v1/profile/{section}/{entry_id}",
        headers=auth_headers,
        json={**SECTIONS[section], **PATCHES[section]},
    )
    assert response.status_code == 200, response.text
    check(
        CAREER,
        f"/profile/{section}/{{{ENTRY_PARAM[section]}}}",
        "patch",
        200,
        response.json(),
    )


class TestJapanAndPreferences:
    def test_setting_the_japan_profile(self, client, auth_headers, profile):
        response = client.put(
            "/api/v1/profile/japan", headers=auth_headers, json={"nationality": "Philippines"}
        )
        assert response.status_code == 200, response.text
        check(CAREER, "/profile/japan", "put", 200, response.json())

    def test_setting_preferences(self, client, auth_headers, profile):
        response = client.put(
            "/api/v1/profile/preferences", headers=auth_headers, json={"currency": "JPY"}
        )
        assert response.status_code == 200, response.text
        check(CAREER, "/profile/preferences", "put", 200, response.json())


def test_listing_proposals(client, auth_headers, profile):
    response = client.get("/api/v1/profile/proposals", headers=auth_headers)
    assert response.status_code == 200
    check(CAREER, "/profile/proposals", "get", 200, response.json())


# --- stories -----------------------------------------------------------------


class TestStories:
    STORY = {
        "title": "Led a migration",
        "challenge": "The service was slow.",
        "action": "Rewrote the query layer.",
        "result": "Response times fell.",
        "source_language": "en",
    }

    def test_creating_a_story(self, client, auth_headers, profile):
        response = client.post("/api/v1/profile/stories", headers=auth_headers, json=self.STORY)
        assert response.status_code == 201, response.text
        check(CAREER, "/profile/stories", "post", 201, response.json())

    def test_changing_a_story(self, client, auth_headers, profile):
        created = client.post("/api/v1/profile/stories", headers=auth_headers, json=self.STORY)
        assert created.status_code == 201, created.text
        response = client.patch(
            f"/api/v1/profile/stories/{created.json()['id']}",
            headers=auth_headers,
            json={"title": "Led the migration"},
        )
        assert response.status_code == 200, response.text
        check(CAREER, "/profile/stories/{story_id}", "patch", 200, response.json())

    def test_listing_stories(self, client, auth_headers, profile):
        client.post("/api/v1/profile/stories", headers=auth_headers, json=self.STORY)
        response = client.get("/api/v1/profile/stories", headers=auth_headers)
        assert response.status_code == 200
        check(CAREER, "/profile/stories", "get", 200, response.json())


# --- imports -----------------------------------------------------------------


class TestImports:
    def test_listing_imports(self, client, auth_headers, profile):
        response = client.get("/api/v1/profile/imports", headers=auth_headers)
        assert response.status_code == 200
        check(IMPORTS, "/profile/imports", "get", 200, response.json())

    def test_starting_an_import(self, client, auth_headers, profile, source_text):
        response = client.post(
            "/api/v1/profile/imports", headers=auth_headers, json={"text": source_text}
        )
        assert response.status_code == 201, response.text
        check(IMPORTS, "/profile/imports", "post", 201, response.json())

    def test_reading_one_import(self, client, auth_headers, profile, source_text):
        created = client.post(
            "/api/v1/profile/imports", headers=auth_headers, json={"text": source_text}
        )
        assert created.status_code == 201
        response = client.get(
            f"/api/v1/profile/imports/{created.json()['id']}", headers=auth_headers
        )
        assert response.status_code == 200
        check(IMPORTS, "/profile/imports/{import_id}", "get", 200, response.json())

    def test_reading_an_import_that_is_not_there(self, client, auth_headers, profile):
        response = client.get(f"/api/v1/profile/imports/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404
        check(IMPORTS, "/profile/imports/{import_id}", "get", 404, response.json())


# --- documents ---------------------------------------------------------------


class TestDocuments:
    def test_refusing_a_profile_without_a_name(self, client, auth_headers, profile):
        """The 422 a generated client must be able to read field by field."""
        response = client.post("/api/v1/profile/documents/rirekisho", headers=auth_headers, json={})
        assert response.status_code == 422, response.text
        check(DOCUMENTS, "/profile/documents/rirekisho", "post", 422, response.json())

    def test_generating_without_a_profile(self, client, auth_headers):
        response = client.post("/api/v1/profile/documents/rirekisho", headers=auth_headers, json={})
        assert response.status_code == 404
        check(DOCUMENTS, "/profile/documents/rirekisho", "post", 404, response.json())


# --- the shared unauthorised shape -------------------------------------------


UNAUTHORISED = [
    (CAREER, "/profile", "get", "/api/v1/profile"),
    (CAREER, "/profile/completeness", "get", "/api/v1/profile/completeness"),
    (CAREER, "/profile/experiences", "get", "/api/v1/profile/experiences"),
    (IMPORTS, "/profile/imports", "get", "/api/v1/profile/imports"),
]


@pytest.mark.parametrize(("feature", "documented", "method", "url"), UNAUTHORISED)
def test_an_unauthorised_caller_gets_the_documented_shape(client, feature, documented, method, url):
    response = client.request(method.upper(), url)
    assert response.status_code == 401
    check(feature, documented, method, 401, response.json())


# --- coverage of this file itself --------------------------------------------

# Documented 2xx JSON responses this file does not validate, each for a reason.
# In the same spirit as DEFERRED in `test_contracts.py`: an operation is either
# checked above or named here, and the last test holds that line. Without it,
# adding a route would quietly reduce coverage while everything still passed.
UNVALIDATED: set[tuple[str, str, str, str]] = {
    # Needs a proposal, which only an import produces. The shapes are exercised
    # end to end in `tests/integration/test_proposal_review.py`; what is missing
    # is the schema check, not the behaviour.
    (CAREER, "/profile/proposals", "post", "201"),
    (CAREER, "/profile/proposals/{proposal_id}/accept", "post", "201"),
    (CAREER, "/profile/proposals/{proposal_id}/merge", "post", "200"),
    # Same: covered behaviourally by `tests/integration/test_snapshot_traceability.py`.
    (CAREER, "/profile/snapshots", "post", "201"),
    (CAREER, "/profile/snapshots/{snapshot_id}", "get", "200"),
    # Multipart, so it needs a real file rather than a JSON body.
    (IMPORTS, "/profile/imports/upload", "post", "201"),
    # Needs an import still running, which is a timing setup rather than a shape.
    (IMPORTS, "/profile/imports/{import_id}/cancel", "post", "200"),
    # Not built yet — it is also in DEFERRED in `test_contracts.py`, and arrives
    # with Phase 6. Remove from both lists together.
    (DOCUMENTS, "/profile/documents/rirekisho/readiness", "get", "200"),
    # Feature 004 is planned, not built. Its contract exists so the client and
    # the contract tests see it; these come off this list as the routes land.
    (SHOKUMU, "/profile/documents/shokumu-keirekisho/readiness", "get", "200"),
}


def _documented_success_responses() -> set[tuple[str, str, str, str]]:
    """Every 2xx JSON response across every feature contract."""
    out: set[tuple[str, str, str, str]] = set()
    for feature in (CAREER, IMPORTS, DOCUMENTS, SHOKUMU):
        for path, spec in contract(feature)["paths"].items():
            for method, operation in spec.items():
                if method == "parameters":
                    continue
                for code, response in operation["responses"].items():
                    content = response.get("content") or {}
                    if code.startswith("2") and "application/json" in content:
                        out.add((feature, path, method, code))
    return out


def test_every_documented_success_response_is_validated_or_named():
    """Keeps this file honest as the contracts grow.

    Runs last on purpose: VALIDATED is filled by the tests above as they
    execute, so running this one alone (or under `-k`) reports everything as
    uncovered. That is a property of the approach, not a failure.
    """
    uncovered = _documented_success_responses() - VALIDATED - UNVALIDATED

    assert not uncovered, (
        "documented 2xx JSON responses with no schema check and no entry in "
        "UNVALIDATED:\n" + "\n".join(f"  {o}" for o in sorted(uncovered))
    )

    stale = UNVALIDATED & VALIDATED
    assert not stale, f"named as unvalidated but actually validated: {sorted(stale)}"
