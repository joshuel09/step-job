"""Constitution gate G12, as a test rather than a claim.

The constitution requires all model access go through a single abstraction, with
no provider SDK called from feature code. That is the kind of rule that holds
for exactly as long as everyone remembers it, so it is checked here instead.
"""

import ast
from pathlib import Path

import pytest
from app.ai import get_provider
from app.ai.provider import AIProvider

APP = Path(__file__).resolve().parents[2] / "app"

# The only module permitted to import a provider SDK.
SDK_GATEWAY = APP / "ai" / "openai_provider.py"

PROVIDER_SDKS = {"openai", "anthropic", "google", "cohere", "mistralai", "ollama"}


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _package_of(path: Path) -> str:
    """The dotted package a file lives in, for resolving relative imports."""
    parts = path.relative_to(APP.parent).parts
    return ".".join(parts[:-1])


def _imported_modules(path: Path) -> set[str]:
    """Every dotted module name an import could be naming.

    `_imported_roots` answers "does this touch `app`", which every module
    does. Telling `app.career` from `app.ai` needs the whole name — and the
    whole name is not always `node.module`:

    - `from app import ai` has module `app` and the thing being imported in
      the alias list, so both have to be joined. This is the form that
      slipped past the first version of this helper, which is the kind of
      hole a guard is supposed to not have.
    - `from ..ai import get_provider` has no module at all until it is
      resolved against the package the file sits in.

    Over-reports rather than under-reports: `from app.ai.schemas import X`
    contributes `app.ai.schemas.X`, which is a class and not a module. A
    guard that answers "is anything here named app.ai" is not harmed by an
    extra name that starts with it, and the opposite mistake is the one
    that matters.
    """
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = _package_of(path).split(".")
                base = ".".join(package[: len(package) - node.level + 1])
            else:
                base = ""
            module = ".".join(filter(None, (base, node.module)))
            if module:
                names.add(module)
            names |= {".".join(filter(None, (module, alias.name))) for alias in node.names}
    return names


def _feature_modules() -> list[Path]:
    return [p for p in APP.rglob("*.py") if p != SDK_GATEWAY]


@pytest.mark.parametrize("module", _feature_modules(), ids=lambda p: str(p.relative_to(APP)))
def test_no_feature_module_imports_a_provider_sdk(module: Path):
    offending = _imported_roots(module) & PROVIDER_SDKS
    assert not offending, (
        f"{module.relative_to(APP)} imports {sorted(offending)} directly. "
        "All model access goes through app.ai (constitution gate G12)."
    )


def test_no_feature_module_imports_the_concrete_provider():
    """Feature code depends on the protocol, never on an implementation."""
    offenders = []
    for module in _feature_modules():
        if module.parent.name == "ai":
            continue
        text = module.read_text()
        if "openai_provider" in text:
            offenders.append(str(module.relative_to(APP)))

    assert not offenders, f"these name a concrete provider: {offenders}"


def test_the_default_provider_never_reaches_the_network():
    """A deployment must opt into calling a real model, not forget to opt out."""
    provider = get_provider()
    assert type(provider).__name__ == "FakeAIProvider"


def test_the_fake_satisfies_the_protocol():
    from app.ai.fake import FakeAIProvider

    assert isinstance(FakeAIProvider(), AIProvider)


def test_the_provider_receives_only_text():
    """The model proposes; it holds no database access and writes nothing."""
    import inspect

    signature = inspect.signature(AIProvider.extract_career_information)
    assert list(signature.parameters) == ["self", "text"]


def test_drafting_a_translation_also_receives_only_text():
    """The second operation (feature 005) keeps the property the first has.

    "One operation, deliberately" was never about the number of methods. It
    was about what a provider is handed: text, and nothing that would let it
    read or write a profile. A `profile`, a `session` or an `entry_id` in
    this signature would be the breach (research.md R-003).
    """
    import inspect

    signature = inspect.signature(AIProvider.draft_translation)
    assert list(signature.parameters) == ["self", "text", "source_language", "target_language"]


@pytest.mark.parametrize(
    "line",
    [
        "from app.ai import get_provider",
        "from app.ai.provider import AIProvider",
        "from app import ai",
        "import app.ai",
        "import app.ai.fake",
        "from ..ai import get_provider",
        "from .. import ai",
    ],
    ids=lambda line: line,
)
def test_the_guard_sees_every_way_of_naming_the_boundary(tmp_path, line):
    """The guard below is only as good as what this helper notices.

    `from app import ai` is the form that slipped past the first version:
    the module is `app` and the interesting part is in the alias list. A
    guard with a hole in it reads exactly like one without, which is why
    the forms are listed here rather than trusted.

    The file is written where a resume module would live, because the
    relative forms resolve against the package they sit in.
    """
    module = APP / "resume" / "_fixture.py"
    module.write_text(line + "\n")
    try:
        names = _imported_modules(module)
    finally:
        module.unlink()

    assert any(name == "app.ai" or name.startswith("app.ai.") for name in names), names


def test_generation_cannot_reach_a_model():
    """R-005 and SC-010, as a shape rather than a promise.

    A document is assembled from approved text in the profile. If anything
    under `app/resume/` could call a provider, "an unapproved draft reached a
    resume" becomes a bug someone can introduce by forgetting a check. With
    no import there is no check to forget.
    """
    offenders = {
        str(module.relative_to(APP)): sorted(reached)
        for module in (APP / "resume").rglob("*.py")
        if (
            reached := {
                name
                for name in _imported_modules(module)
                if name == "app.ai" or name.startswith("app.ai.")
            }
        )
    }
    assert not offenders, f"these reach the model boundary from the render path: {offenders}"
