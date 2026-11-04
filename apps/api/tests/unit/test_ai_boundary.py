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


def _imported_modules(path: Path) -> set[str]:
    """Every dotted module name imported, not just its first segment.

    `_imported_roots` answers "does this touch `app`", which every module
    does. Telling `app.career` from `app.ai` needs the whole name.
    """
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
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
