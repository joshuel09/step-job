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

#: Every throwaway module the boundary tests write starts with this. They
#: are written into `app/` because a relative import resolves against the
#: package a file sits in, so the prefix is how a sweep recognises them
#: without guessing.
FIXTURE_PREFIX = "_fixture_"


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
    """One `from ... import ...`, as an absolute dotted name."""
    if not node.level:
        return node.module or ""

    # `resolve_name` wants the dots back: `from ..imports.dates import x`
    # inside `app.documents` is `..imports.dates` against `app.documents`.
    return resolve_name("." * node.level + (node.module or ""), package_of(path, root=root))


def reaches(path: Path, prefix: str, *, root: Path, through: str | None = None) -> set[str]:
    """The names reachable from this file that are, or sit under, `prefix`.

    Follows imports rather than reading only the first line of them. "The
    era table is not reachable from the English formatter" is a statement
    about reachability, and a check that stopped at direct imports would be
    satisfied by a module that imports a sibling which imports the era
    table — one hop, no diff anybody would question, and the guarantee
    gone.

    `through` bounds the walk to a package, so the search stays inside this
    repository and does not try to open `datetime`. Cycles are ordinary in
    an application's import graph; `seen` is what stops this following one
    forever.

    Package initialisers count. Importing `app.career.models` runs
    `app/career/__init__.py` first, so whatever that file imports is
    reached as surely as if the importing module had named it — and a walk
    that followed only the module named in the import statement would miss
    it entirely. Every ancestor initialiser of every module followed, and
    of the starting file, goes into the queue.
    """
    package = through or prefix.split(".")[0]
    found: set[str] = set()
    seen: set[Path] = set()
    queue = [path.resolve(), *_initialisers(path, root=root)]

    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)

        for name in imported_modules(current, root=root):
            if name == prefix or name.startswith(f"{prefix}."):
                found.add(name)
            elif name == package or name.startswith(f"{package}."):
                nxt = _file_for(name, root=root)
                if nxt is not None:
                    queue.append(nxt)
                    queue.extend(_initialisers(nxt, root=root))

    return found


def _initialisers(path: Path, *, root: Path) -> list[Path]:
    """Every `__init__.py` Python runs on the way to importing this file.

    `import app.career.models` executes `app/__init__.py` and then
    `app/career/__init__.py` before the module itself, so anything those
    import is reached as surely as if the importing module had named it.
    """
    path, root = path.resolve(), root.resolve()
    if root not in path.parents:
        return []

    found = []
    current = path.parent
    while True:
        initialiser = current / "__init__.py"
        if initialiser.is_file():
            found.append(initialiser)
        if current == root:
            return found
        current = current.parent


def _file_for(name: str, *, root: Path) -> Path | None:
    """The file a dotted name refers to, or None if it names no module.

    `from app.ai.schemas import TranslationDraft` contributes
    `app.ai.schemas.TranslationDraft`, which is a class. Resolving it finds
    nothing, and finding nothing is the right answer — the module it came
    from is in the set beside it and will be followed.
    """
    parts = name.split(".")[1:]
    if not parts:
        return None

    module = root.joinpath(*parts).with_suffix(".py")
    if module.is_file():
        return module

    package = root.joinpath(*parts, "__init__.py")
    return package if package.is_file() else None
