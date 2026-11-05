"""The import walk the boundary tests lean on, checked against every form.

A guard's failure mode is not a false alarm. It is reporting nothing while
the thing it guards is wide open — so the forms of import are listed here
rather than trusted, including the two that have already slipped past a
version of this walk: `from app import ai`, where the interesting name is
in the alias list, and `from ..imports.dates import year_to_era`, where
`node.module` says `imports.dates` and means something else entirely.
"""

from pathlib import Path

import pytest

from tests.unit.import_graph import (
    FIXTURE_PREFIX,
    imported_modules,
    package_of,
    reaches,
)

APP = Path(__file__).resolve().parents[2] / "app"


@pytest.mark.parametrize(
    "line",
    [
        "import app.imports.dates",
        "import app.imports",
        "from app.imports.dates import year_to_era",
        "from app.imports import dates",
        "from app import imports",
        "from ..imports.dates import year_to_era",
        "from ..imports import dates",
        "from .. import imports",
    ],
    ids=lambda line: line,
)
def test_every_way_of_reaching_the_era_module_is_seen(line, write_module):
    """The relative forms are the ones a naive walk misses. `node.module`
    for `from ..imports.dates import x` is `imports.dates`, which looks
    absolute and is not."""
    found = reaches(write_module("documents", "probe", line), "app.imports", root=APP)

    assert found, f"{line!r} was not seen"


@pytest.mark.parametrize(
    "line",
    [
        "from datetime import date",
        "import re",
        "from app.career import models",
        "from app.documents.typography import FONT_NAME",
        "from . import typography",
        "from .typography import FONT_NAME",
    ],
    ids=lambda line: line,
)
def test_an_unrelated_import_is_not_reported(line, write_module):
    """A guard that fires on everything is a guard nobody keeps."""
    found = reaches(write_module("documents", "probe", line), "app.imports", root=APP)

    assert not found, f"{line!r} was reported as reaching the era module: {found}"


@pytest.mark.parametrize(
    ("package", "expected"),
    [("documents", "app.documents.typography"), ("resume", "app.resume.sections")],
)
def test_a_relative_import_resolves_against_the_file_and_not_the_text(
    package, expected, write_module
):
    """The same line means two different modules in two different packages.

    A sibling import is what shows it: `from ..imports import dates` is
    `app.imports` from either package, so a test using that one would pass
    with the path ignored entirely.
    """
    path = write_module(package, "probe", f"from .{expected.split('.')[-1]} import nothing")

    assert expected in imported_modules(path, root=APP)


class TestAnIndirectPath:
    """Reachability, not the first line of it.

    "The era table is not reachable from the English formatter" is a claim
    about what can be got to. A module that imports a sibling which imports
    the era table satisfies a direct-import check — one hop, a diff nobody
    would question, and the guarantee gone.
    """

    def test_one_hop_away_is_still_reachable(self, write_module):
        """A module that imports a sibling which imports the era table."""
        write_module("documents", "helper", "from app.imports.dates import year_to_era")
        entry = write_module(
            "documents", "probe", f"from app.documents.{FIXTURE_PREFIX}helper import year_to_era"
        )

        assert reaches(entry, "app.imports", root=APP)

    def test_two_hops_away_is_too(self, write_module):
        """One hop could be caught by looking one level further. Two says
        the walk follows rather than peeks."""
        write_module("documents", "a", "from app.imports.dates import year_to_era")
        write_module("documents", "b", f"from app.documents.{FIXTURE_PREFIX}a import year_to_era")
        entry = write_module(
            "documents", "probe", f"from app.documents.{FIXTURE_PREFIX}b import year_to_era"
        )

        assert reaches(entry, "app.imports", root=APP)

    def test_a_cycle_does_not_hang_the_walk(self, write_module):
        """Ordinary in an application's import graph, and fatal to a walk
        that does not remember where it has been — without the visited set
        this does not fail, it never returns."""
        first = write_module(
            "documents", "a", f"from app.documents.{FIXTURE_PREFIX}b import nothing"
        )
        write_module("documents", "b", f"from app.documents.{FIXTURE_PREFIX}a import nothing")

        assert reaches(first, "app.imports", root=APP) == set()

    def test_an_unrelated_neighbour_is_not_followed_into_a_false_positive(self, write_module):
        """Following imports can only widen what is reported, so the test
        that it still reports nothing for a clean module is the one that
        keeps this usable."""
        entry = write_module("documents", "probe", "from app.documents.typography import FONT_NAME")

        assert reaches(entry, "app.imports", root=APP) == set()


def test_the_package_of_a_file_is_what_python_would_call_it():
    assert package_of(APP / "documents" / "dates.py", root=APP) == "app.documents"
    assert package_of(APP / "resume" / "sections.py", root=APP) == "app.resume"


def test_no_fixture_module_is_left_behind():
    """These tests write into the application package, so this is the test
    that says they clean up after themselves.

    An interrupted run can leave one — a timeout kills the process before
    teardown — and a stray `_fixture_*.py` under `app/` is a file that gets
    committed by the next `git add -A`. The fixture sweeps before and after;
    this fails if anything survived both.
    """
    assert list(APP.rglob(f"{FIXTURE_PREFIX}*.py")) == []
