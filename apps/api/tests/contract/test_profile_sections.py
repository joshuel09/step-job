"""The implementation must not drift from contracts/openapi.yaml.

The constitution makes that document the source the typed client is generated
from, so a route that exists only in the code is invisible to the web
application, and a documented route that is missing breaks a generated call at
runtime rather than at build time.
"""

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

# Documented but delivered by later stories; listed so the gap is deliberate
# rather than silent.
DEFERRED = {
    "/profile/stories",
    "/profile/stories/{story_id}",
    "/profile/proposals",
    "/profile/proposals/{proposal_id}/accept",
    "/profile/proposals/{proposal_id}/reject",
    "/profile/proposals/{proposal_id}/merge",
}


@pytest.fixture(scope="module")
def contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text())


@pytest.fixture(scope="module")
def implemented() -> set[str]:
    return {
        route.path.removeprefix("/api/v1")
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/v1/profile")
    }


def test_every_user_story_1_path_is_implemented(contract, implemented):
    documented = set(contract["paths"]) - DEFERRED
    missing = documented - implemented
    assert not missing, f"documented but not implemented: {sorted(missing)}"


def test_no_undocumented_profile_paths_exist(contract, implemented):
    undocumented = implemented - set(contract["paths"])
    assert not undocumented, f"implemented but undocumented: {sorted(undocumented)}"


def test_deferred_paths_are_still_documented(contract):
    """Guards the deferral list against drifting out of the contract."""
    assert DEFERRED <= set(contract["paths"])


@pytest.mark.parametrize(
    "path",
    ["/profile", "/profile/experiences", "/profile/japan", "/profile/export"],
)
def test_documented_methods_are_all_served(contract, path):
    documented = {m.upper() for m in contract["paths"][path] if m != "parameters"}
    served: set[str] = set()
    for route in app.routes:
        if getattr(route, "path", "").removeprefix("/api/v1") == path:
            served |= {m for m in route.methods if m not in {"HEAD", "OPTIONS"}}

    assert documented <= served, f"{path}: missing {sorted(documented - served)}"
