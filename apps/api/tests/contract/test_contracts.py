"""The implementation must not drift from any feature's contract.

The constitution makes these documents the source the typed client is generated
from, so a route existing only in code is invisible to the web application, and a
documented route that is missing breaks a generated call at runtime rather than
at build time.

Every contract is discovered rather than named. A test that names one file does
not fail when a second feature adds its own — it simply stops covering it, and a
check that silently stops checking is worse than no check, because it still
reports success.

Feature 002 defers nothing: paths belonging to unbuilt stories are listed in
DEFERRED so the gap is deliberate rather than an omission.
"""

from pathlib import Path

import pytest
import yaml
from app.main import app

SPECS = Path(__file__).resolve().parents[4] / "specs"

# Paths documented but not yet implemented, per feature. A path listed here is a
# deliberate deferral; a path missing from both here and the implementation is a
# failure.
DEFERRED: dict[str, set[str]] = {
    "001-master-career-profile": set(),
    # Feature 002 is mid-implementation: file upload arrives with User Story 2.
    "002-ai-resume-import": {
        "/profile/imports/upload",
    },
}


def _contract_files() -> list[Path]:
    found = sorted(SPECS.glob("*/contracts/openapi.yaml"))
    assert found, "no contracts discovered under specs/*/contracts/openapi.yaml"
    return found


CONTRACT_FILES = _contract_files()
FEATURE_IDS = [p.parents[1].name for p in CONTRACT_FILES]


@pytest.fixture(scope="module")
def served() -> dict[str, set[str]]:
    """Every /profile path the application serves, with its methods."""
    out: dict[str, set[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/profile"):
            out.setdefault(path.removeprefix("/api/v1"), set()).update(
                m for m in route.methods if m not in {"HEAD", "OPTIONS"}
            )
    return out


@pytest.mark.parametrize("contract_file", CONTRACT_FILES, ids=FEATURE_IDS)
def test_every_documented_path_is_implemented(contract_file: Path, served):
    feature = contract_file.parents[1].name
    contract = yaml.safe_load(contract_file.read_text())

    documented = set(contract["paths"]) - DEFERRED.get(feature, set())
    missing = documented - set(served)

    assert not missing, f"{feature}: documented but not implemented: {sorted(missing)}"


@pytest.mark.parametrize("contract_file", CONTRACT_FILES, ids=FEATURE_IDS)
def test_every_documented_method_is_served(contract_file: Path, served):
    """Checking paths alone is not enough.

    A documented GET slipped through unimplemented once because PATCH and DELETE
    on the same path made the path look served.
    """
    feature = contract_file.parents[1].name
    contract = yaml.safe_load(contract_file.read_text())
    deferred = DEFERRED.get(feature, set())

    gaps: dict[str, list[str]] = {}
    for path, spec in contract["paths"].items():
        if path in deferred:
            continue
        documented = {m.upper() for m in spec if m != "parameters"}
        missing = documented - served.get(path, set())
        if missing:
            gaps[path] = sorted(missing)

    assert not gaps, f"{feature}: documented but not served: {gaps}"


def test_no_served_path_is_undocumented(served):
    """A route in code that no contract describes is invisible to the client."""
    documented: set[str] = set()
    for contract_file in CONTRACT_FILES:
        documented |= set(yaml.safe_load(contract_file.read_text())["paths"])

    undocumented = set(served) - documented
    assert not undocumented, f"implemented but undocumented: {sorted(undocumented)}"


def test_deferred_paths_are_really_documented():
    """Guards the deferral lists against drifting out of their contracts."""
    for contract_file in CONTRACT_FILES:
        feature = contract_file.parents[1].name
        deferred = DEFERRED.get(feature, set())
        if not deferred:
            continue
        paths = set(yaml.safe_load(contract_file.read_text())["paths"])
        stale = deferred - paths
        assert not stale, f"{feature}: deferred but not in the contract: {sorted(stale)}"


def test_more_than_one_contract_is_covered():
    """The failure this file replaces.

    The previous test named a single contract path. When a second feature added
    its own, nothing failed — coverage just silently stopped at one.
    """
    assert len(CONTRACT_FILES) >= 2, "expected contracts for at least two features"
