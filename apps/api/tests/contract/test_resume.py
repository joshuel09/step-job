"""The English resume route against what its contract promises.

`test_contracts.py` checks that every documented path and method is served.
It does not check that a route's documented responses and headers actually
happen, which is the gap a client written from the contract falls into.
These tests read the contract and hold the route to it.
"""

import uuid
from pathlib import Path

import pytest
import yaml

CONTRACT = (
    Path(__file__).resolve().parents[4]
    / "specs"
    / "005-english-resume"
    / "contracts"
    / "openapi.yaml"
)
ROUTE = "/profile/documents/resume"
PATH = f"/api/v1{ROUTE}"


@pytest.fixture(scope="module")
def contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture
def generated(client, auth_headers, resume_profile):
    response = client.post(PATH, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return response


class TestDocumentedResponses:
    def test_the_success_media_type_is_the_one_documented(self, contract, generated):
        documented = contract["paths"][ROUTE]["post"]["responses"]["200"]["content"]

        assert generated.headers["content-type"].split(";")[0] in documented

    def test_every_documented_header_is_sent(self, contract, generated):
        documented = contract["paths"][ROUTE]["post"]["responses"]["200"]["headers"]

        for name in documented:
            assert name in generated.headers, name

    def test_the_page_count_is_the_integer_it_is_documented_as(self, contract, generated):
        schema = contract["paths"][ROUTE]["post"]["responses"]["200"]["headers"][
            "X-Document-Pages"
        ]["schema"]
        assert schema["type"] == "integer"

        assert int(generated.headers["X-Document-Pages"]) >= 1

    def test_the_snapshot_id_is_the_uuid_it_is_documented_as(self, contract, generated):
        schema = contract["paths"][ROUTE]["post"]["responses"]["200"]["headers"]["X-Snapshot-Id"][
            "schema"
        ]
        assert schema["format"] == "uuid"

        assert uuid.UUID(generated.headers["X-Snapshot-Id"])

    def test_the_disposition_is_attachment_unless_previewing(self, generated):
        assert "attachment" in generated.headers["Content-Disposition"]

    def test_and_inline_when_previewing(self, client, auth_headers, resume_profile):
        response = client.post(f"{PATH}?preview=true", headers=auth_headers, json={})

        assert response.status_code == 200, response.text
        assert "inline" in response.headers["Content-Disposition"]

    def test_a_profile_that_cannot_produce_one_gets_the_documented_422(
        self, contract, client, auth_headers, session, user_id
    ):
        from app.career import models, service

        profile = service.get_or_create_profile(session, user_id)
        session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
        session.flush()

        refused = client.post(PATH, headers=auth_headers, json={})

        assert "422" in contract["paths"][ROUTE]["post"]["responses"]
        assert refused.status_code == 422, refused.text
        assert refused.json()["code"] == "validation_failed"

    def test_no_profile_at_all_gets_the_documented_404(self, contract, client, auth_headers):
        missing = client.post(PATH, headers=auth_headers, json={})

        assert "404" in contract["paths"][ROUTE]["post"]["responses"]
        assert missing.status_code == 404, missing.text


class TestDocumentedRequest:
    def test_the_body_is_optional_as_documented(
        self, contract, client, auth_headers, resume_profile
    ):
        """`required: false`, so a client that sends nothing gets the
        defaults rather than a 422 about a body it was told it could omit."""
        assert contract["paths"][ROUTE]["post"]["requestBody"]["required"] is False

        response = client.post(PATH, headers=auth_headers)

        assert response.status_code == 200, response.text

    def test_every_documented_paper_size_is_accepted(
        self, contract, client, auth_headers, resume_profile
    ):
        documented = contract["components"]["schemas"]["PaperSize"]["enum"]
        assert documented, "the contract offers no paper sizes"

        for size in documented:
            response = client.post(PATH, headers=auth_headers, json={"paper_size": size})
            assert response.status_code == 200, (size, response.text)

    def test_the_documented_default_paper_size_is_what_a_client_gets(
        self, contract, client, auth_headers, resume_profile
    ):
        """A default stated in the contract and not matched by the server is
        the kind of difference nobody sees until a document comes out on the
        wrong paper."""
        from app.resume.schemas import ResumeRequest

        documented = contract["components"]["schemas"]["PaperSize"]["default"]

        assert str(ResumeRequest().paper_size) == documented

    def test_an_undocumented_paper_size_is_refused(self, client, auth_headers, resume_profile):
        response = client.post(PATH, headers=auth_headers, json={"paper_size": "b5"})

        assert response.status_code == 422, response.text

    def test_include_skills_defaults_as_documented(self, contract):
        from app.resume.schemas import ResumeRequest

        documented = contract["components"]["schemas"]["ResumeRequest"]["properties"][
            "include_skills"
        ]["default"]

        assert ResumeRequest().include_skills is documented


class TestHeadersReachTheBrowser:
    """The interface and the API are separate origins.

    Every test above reads these headers through a test client, which is not
    subject to the browser's rules. A cross-origin fetch sees only a short
    safelist unless the server says otherwise, so without this the page count
    and the snapshot id would be undefined in the interface while every test
    on this page still passed.
    """

    ORIGIN = "http://localhost:3000"

    def test_the_documented_headers_are_exposed_to_a_cross_origin_caller(
        self, contract, client, auth_headers, resume_profile
    ):
        response = client.post(PATH, headers={**auth_headers, "Origin": self.ORIGIN}, json={})
        assert response.status_code == 200

        exposed = {
            h.strip().lower()
            for h in response.headers.get("access-control-expose-headers", "").split(",")
        }
        documented = contract["paths"][ROUTE]["post"]["responses"]["200"]["headers"]
        assert {name.lower() for name in documented} <= exposed


class TestTheRouteIsNoLongerDeferred:
    def test_it_is_served(self, client, auth_headers, resume_profile):
        """T037. `test_contracts.py` fails if a path is both served and
        listed as deferred, so this is the behavioural half of taking it
        off that list."""
        assert client.post(PATH, headers=auth_headers, json={}).status_code == 200

    def test_the_readiness_route_is_still_honestly_deferred(self, client, auth_headers):
        """It is User Story 2, and claiming otherwise would make the
        deferred list the thing that is wrong."""
        assert client.get(f"{PATH}/readiness", headers=auth_headers).status_code == 404
