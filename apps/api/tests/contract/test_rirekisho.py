"""The document routes against what the contract promises.

`test_contracts.py` checks that every documented path and method is served. It
does not check that a route's documented responses and headers actually happen,
which is the gap a client written from the contract would fall into. These
tests read the contract and hold the routes to it.
"""

import uuid
from pathlib import Path

import pytest
import yaml

CONTRACT = (
    Path(__file__).resolve().parents[4]
    / "specs"
    / "003-rirekisho-generator"
    / "contracts"
    / "openapi.yaml"
)
ROUTE = "/profile/documents/rirekisho"
PATH = f"/api/v1{ROUTE}"


@pytest.fixture(scope="module")
def contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))


@pytest.fixture
def generated(client, auth_headers, rirekisho_profile):
    response = client.post(PATH, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return response


class TestDocumentedResponses:
    def test_the_success_media_type_is_the_one_documented(self, contract, generated):
        documented = contract["paths"][ROUTE]["post"]["responses"]["200"]["content"]
        assert set(documented) == {generated.headers["content-type"]}

    def test_every_documented_response_header_is_sent(self, contract, generated):
        documented = contract["paths"][ROUTE]["post"]["responses"]["200"]["headers"]
        missing = [name for name in documented if name not in generated.headers]
        assert missing == []

    def test_the_snapshot_header_is_a_uuid_as_documented(self, generated):
        uuid.UUID(generated.headers["X-Snapshot-Id"])

    def test_the_page_header_is_an_integer_as_documented(self, generated):
        assert int(generated.headers["X-Document-Pages"]) >= 1

    def test_a_caller_without_an_identity_is_refused(self, client):
        assert client.post(PATH).status_code == 401

    def test_a_caller_with_no_profile_gets_the_documented_404(self, client, auth_headers):
        assert client.post(PATH, headers=auth_headers).status_code == 404

    def test_a_rejection_matches_the_documented_validation_shape(self, client, auth_headers):
        assert client.post("/api/v1/profile", headers=auth_headers).status_code == 201

        response = client.post(PATH, headers=auth_headers, json={})
        assert response.status_code == 422

        body = response.json()
        assert set(body) >= {"code", "message", "failures"}
        for failure in body["failures"]:
            assert set(failure) >= {"field", "reason"}


class TestRequestBody:
    def test_the_body_is_optional_as_documented(self, client, auth_headers, rirekisho_profile):
        assert contract_body_required() is False
        assert client.post(PATH, headers=auth_headers).status_code == 200

    @pytest.mark.parametrize("convention", ["seireki", "wareki"])
    def test_every_documented_date_convention_is_accepted(
        self, client, auth_headers, rirekisho_profile, convention
    ):
        response = client.post(PATH, headers=auth_headers, json={"date_convention": convention})
        assert response.status_code == 200, response.text

    @pytest.mark.parametrize("paper", ["a4", "b5"])
    def test_every_documented_paper_size_is_accepted(
        self, client, auth_headers, rirekisho_profile, paper
    ):
        response = client.post(PATH, headers=auth_headers, json={"paper_size": paper})
        assert response.status_code == 200, response.text

    def test_a_value_outside_the_documented_enum_is_refused(
        self, client, auth_headers, rirekisho_profile
    ):
        response = client.post(PATH, headers=auth_headers, json={"paper_size": "letter"})
        assert response.status_code == 422

    def test_the_enums_served_are_the_enums_documented(self, contract):
        """A client generated from the contract offers exactly these choices."""
        from app.rirekisho.schemas import DateConvention, PaperSize

        schemas = contract["components"]["schemas"]
        assert set(schemas["DateConvention"]["enum"]) == {str(v) for v in DateConvention}
        assert set(schemas["PaperSize"]["enum"]) == {str(v) for v in PaperSize}


class TestPreview:
    def test_preview_is_documented_and_defaults_to_download(self, contract, generated):
        names = [p["name"] for p in contract["paths"][ROUTE]["post"]["parameters"]]
        assert "preview" in names
        assert generated.headers["Content-Disposition"].startswith("attachment")

    def test_preview_returns_the_document_for_display(
        self, client, auth_headers, rirekisho_profile
    ):
        response = client.post(f"{PATH}?preview=true", headers=auth_headers, json={})
        assert response.status_code == 200
        assert response.headers["Content-Disposition"].startswith("inline")

    def test_previewing_and_downloading_give_the_same_document(
        self, client, auth_headers, rirekisho_profile
    ):
        """A user must never preview one thing and download another."""
        preview = client.post(f"{PATH}?preview=true", headers=auth_headers, json={})
        download = client.post(PATH, headers=auth_headers, json={})

        assert _without_ids(preview.content) == _without_ids(download.content)


def contract_body_required() -> bool:
    data = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return data["paths"][ROUTE]["post"]["requestBody"].get("required", False)


def _without_ids(pdf: bytes) -> bytes:
    """Strip what differs between two renders of the same content.

    Two PDFs produced a moment apart carry different creation timestamps and
    document ids. Comparing raw bytes would fail on those alone and prove
    nothing about whether the pages match.
    """
    import io
    import re

    from pypdf import PdfReader

    pages = PdfReader(io.BytesIO(pdf)).pages
    text = "\n".join(p.extract_text() or "" for p in pages)
    return re.sub(r"\s+", " ", text).strip().encode("utf-8")


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
        self, contract, client, auth_headers, rirekisho_profile
    ):
        response = client.post(PATH, headers={**auth_headers, "Origin": self.ORIGIN}, json={})
        assert response.status_code == 200

        exposed = {
            h.strip().lower()
            for h in response.headers.get("access-control-expose-headers", "").split(",")
        }
        documented = contract["paths"][ROUTE]["post"]["responses"]["200"]["headers"]
        assert {name.lower() for name in documented} <= exposed
