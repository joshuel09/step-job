"""Reading a module's imports, for the tests that assert something is out of reach.

Several guarantees in this codebase are "module A cannot reach module B":
no feature module reaches a provider SDK (gate G12), nothing under
`app/resume/` reaches `app.ai` (R-005), and the English date formatter
cannot reach the era table (R-006). Each is checked by walking imports, and
each was checked by its own copy of the walk until the copies started
disagreeing with each other.

One copy, because the failure mode of a guard is not that it reports a
problem that is not there. It is that it reports nothing while the thing it
guards is wide open, and a second copy is a second chance at that.
"""

import ast
from importlib.util import resolve_name
from pathlib import Path


def package_of(path: Path, *, root: Path) -> str:
    """The dotted package a file lives in, as Python would name it."""
    parts = path.resolve().relative_to(root.resolve().parent).parts
    return ".".join(parts[:-1])


def imported_modules(path: Path, *, root: Path) -> set[str]:
    """Every dotted module name an import in this file could be naming.

    Three forms have to be handled, and leaving any one out leaves a hole
    that reads exactly like no hole at all:

    - `import app.ai.fake` — the name is in the alias.
    - `from app import ai` — the module is `app` and the interesting part is
      in the alias list, so both have to be joined.
    - `from ..imports.dates import year_to_era` — the module is relative and
      means nothing until it is resolved against the package the file sits
      in. Python keeps the leading dots in `level`, so this is not visible
      in `node.module` at all.

    Over-reports rather than under-reports: `from app.ai.schemas import X`
    contributes `app.ai.schemas.X`, a class rather than a module. A guard
    asking "is anything here named `app.ai`" is unharmed by a name that
    starts with it, and the opposite mistake is the one that matters.
    """
    tree = ast.parse(path.read_text())
    names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            base = _resolve(node, path, root=root)
            if base:
                names.add(base)
            names |= {".".join(filter(None, (base, alias.name))) for alias in node.names}

    return names


def _resolve(node: ast.ImportFrom, path: Path, *, root: Path) -> str:
    if not node.level:
        return node.module or ""

    # `resolve_name` wants the dots back: `from ..imports.dates import x`
    # inside `app.documents` is `..imports.dates` against `app.documents`.
    return resolve_name("." * node.level + (node.module or ""), package_of(path, root=root))


def reaches(path: Path, prefix: str, *, root: Path) -> set[str]:
    """The names this file imports that are, or sit under, `prefix`."""
    return {
        name
        for name in imported_modules(path, root=root)
        if name == prefix or name.startswith(f"{prefix}.")
    }
