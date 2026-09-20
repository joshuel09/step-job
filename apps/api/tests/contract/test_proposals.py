"""The proposal surface must match the contract the client is generated from."""

from pathlib import Path

import pytest
import yaml
from app.main import app

CONTRACT = (
    Path(__file__).resolve().parents[4]
    / "specs"
    / "001-master-career-profile"
    / "contracts"
    / "openapi.yaml"
)

PROPOSAL_PATHS = {
    "/profile/proposals",
    "/profile/proposals/{proposal_id}/accept",
    "/profile/proposals/{proposal_id}/reject",
    "/profile/proposals/{proposal_id}/merge",
}


@pytest.fixture(scope="module")
def contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text())


@pytest.fixture(scope="module")
def served() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/profile"):
            out.setdefault(path.removeprefix("/api/v1"), set()).update(
                m for m in route.methods if m not in {"HEAD", "OPTIONS"}
            )
    return out


def test_all_proposal_paths_are_served(served):
    assert PROPOSAL_PATHS <= set(served)


def test_proposal_methods_match_the_contract(contract, served):
    for path in PROPOSAL_PATHS:
        documented = {m.upper() for m in contract["paths"][path] if m != "parameters"}
        assert documented <= served[path], f"{path}: missing {sorted(documented - served[path])}"


def test_the_status_filter_is_documented(contract):
    params = contract["paths"]["/profile/proposals"]["get"].get("parameters", [])
    assert any(p["name"] == "status" for p in params)
