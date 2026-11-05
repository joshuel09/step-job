"""Fixtures shared by the unit tests.

`write_module` is here rather than in one of them because two boundary
tests need it — the gate on `app.ai` and the one on the era table — and a
fixture imported from another test module is a fixture that gets
redefined.
"""

from pathlib import Path

import pytest

from tests.unit.import_graph import FIXTURE_PREFIX

APP = Path(__file__).resolve().parents[2] / "app"


@pytest.fixture
def write_module():
    """Write throwaway modules where real ones would live, and remove them.

    The location matters: a relative import resolves against the package a
    file sits in, so a fixture written to a temp directory would resolve to
    something no production module could ever mean. Which means these go
    into `app/` — and anything written into `app/` has to come out again,
    including when the test fails or the process is killed partway.

    Teardown handles the first. The sweep handles the second: it removes
    every fixture module under `app/`, not only the ones this test made, so
    a file left behind by an interrupted run is gone by the next run rather
    than sitting in the tree waiting for the next `git add -A`.
    """

    def _sweep() -> None:
        for stray in APP.rglob(f"{FIXTURE_PREFIX}*.py"):
            stray.unlink()

    _sweep()

    def write(package: str, name: str, line: str) -> Path:
        path = APP / package / f"{FIXTURE_PREFIX}{name}.py"
        path.write_text(line + "\n")
        return path

    yield write
    _sweep()
