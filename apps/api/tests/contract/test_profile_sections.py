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

# Every documented path is now implemented. Kept as an empty set so a future
# story can defer a path explicitly rather than by omission.
DEFERRED: set[str] = set()


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


def test_documented_methods_are_all_served(contract):
    """Every documented method on every implemented path.

    Checking a hand-picked list of paths let a documented GET slip through
    unimplemented, because PATCH and DELETE on the same path made it look served.
    """
    served: dict[str, set[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/profile"):
            key = path.removeprefix("/api/v1")
            served.setdefault(key, set()).update(
                m for m in route.methods if m not in {"HEAD", "OPTIONS"}
            )

    gaps: dict[str, list[str]] = {}
    for path, spec in contract["paths"].items():
        if path in DEFERRED:
            continue
        documented = {m.upper() for m in spec if m != "parameters"}
        missing = documented - served.get(path, set())
        if missing:
            gaps[path] = sorted(missing)

    assert not gaps, f"documented but not served: {gaps}"
