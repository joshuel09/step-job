"""The import surface must match the contract the client is generated from."""

from pathlib import Path

import pytest
import yaml
from app.main import app

CONTRACT = (
    Path(__file__).resolve().parents[4]
    / "specs"
    / "002-ai-resume-import"
    / "contracts"
    / "openapi.yaml"
)

# Arrives with User Story 2.
DEFERRED = {"/profile/imports/upload"}


@pytest.fixture(scope="module")
def contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text())


@pytest.fixture(scope="module")
def served() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/profile/imports"):
            out.setdefault(path.removeprefix("/api/v1"), set()).update(
                m for m in route.methods if m not in {"HEAD", "OPTIONS"}
            )
    return out


def test_every_implemented_path_is_served(contract, served):
    documented = set(contract["paths"]) - DEFERRED
    assert documented <= set(served), f"missing: {sorted(documented - set(served))}"


def test_documented_methods_are_served(contract, served):
    gaps = {}
    for path, spec in contract["paths"].items():
        if path in DEFERRED:
            continue
        documented = {m.upper() for m in spec if m != "parameters"}
        missing = documented - served.get(path, set())
        if missing:
            gaps[path] = sorted(missing)
    assert not gaps, f"documented but not served: {gaps}"


def test_the_status_filter_is_documented(contract):
    params = contract["paths"]["/profile/imports"]["get"].get("parameters", [])
    assert any(p["name"] == "status" for p in params)


def test_the_import_schema_carries_no_filename(contract):
    """FR-019b, asserted against the contract itself.

    A name such as the company someone was applying to reveals their job search,
    so it must not be in the shape at all — not merely omitted by the code.
    """
    properties = contract["components"]["schemas"]["Import"]["properties"]
    assert "filename" not in properties
    assert "file_name" not in properties


def test_failure_reasons_distinguish_an_outage_from_a_bad_document(contract):
    """The two look alike to a user and have opposite remedies (FR-017b)."""
    values = set(contract["components"]["schemas"]["FailureReason"]["enum"])
    assert {"service_unavailable", "unreadable_document"} <= values
