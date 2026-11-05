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

from tests.unit.import_graph import imported_modules, package_of, reaches

APP = Path(__file__).resolve().parents[2] / "app"


def _module(tmp_path, line: str, *, at: str) -> Path:
    """Write a throwaway module where a real one would live.

    The location matters: a relative import resolves against the package
    the file sits in, so a fixture written to a temp directory would
    resolve to something no production file could ever mean.
    """
    path = APP / at
    path.write_text(line + "\n")
    return path


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
def test_every_way_of_reaching_the_era_module_is_seen(line):
    """The relative forms are the ones a naive walk misses. `node.module`
    for `from ..imports.dates import x` is `imports.dates`, which looks
    absolute and is not."""
    path = _module(None, line, at="documents/_fixture.py")
    try:
        found = reaches(path, "app.imports", root=APP)
    finally:
        path.unlink()

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
def test_an_unrelated_import_is_not_reported(line):
    """A guard that fires on everything is a guard nobody keeps."""
    path = _module(None, line, at="documents/_fixture.py")
    try:
        found = reaches(path, "app.imports", root=APP)
    finally:
        path.unlink()

    assert not found, f"{line!r} was reported as reaching the era module: {found}"


def test_a_relative_import_resolves_against_the_file_and_not_the_text(tmp_path):
    """The same line means two different modules in two different packages,
    which is why resolution takes the path."""
    for package, expected in (("documents", "app.imports"), ("resume", "app.imports")):
        path = APP / package / "_fixture.py"
        path.write_text("from ..imports import dates\n")
        try:
            assert expected in imported_modules(path, root=APP)
        finally:
            path.unlink()


def test_the_package_of_a_file_is_what_python_would_call_it():
    assert package_of(APP / "documents" / "dates.py", root=APP) == "app.documents"
    assert package_of(APP / "resume" / "sections.py", root=APP) == "app.resume"
