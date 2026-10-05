"""Reading response schemas out of the feature contracts.

`test_contracts.py` proves every documented path and method is served. It says
nothing about what a route returns, so a route can answer with a shape its
contract does not describe and every check still passes. The typed client is
generated from these contracts, which means the web application would compile
against a shape the API does not produce — a runtime failure the build reports
as success.

That is not hypothetical. Feature 002's contract failed to describe `evidence`,
`conflicts` and `import_id`; the TypeScript compiler caught it, and only because
the web code happened to use those fields. Nothing here noticed.
"""

from functools import cache
from pathlib import Path
from typing import Any

import yaml

SPECS = Path(__file__).resolve().parents[4] / "specs"


@cache
def contract(feature: str) -> dict[str, Any]:
    """One feature's contract, parsed once."""
    path = SPECS / feature / "contracts" / "openapi.yaml"
    assert path.exists(), f"no contract for {feature} at {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def response_schema(feature: str, path: str, method: str, status: int | str) -> dict[str, Any]:
    """The schema a route's response is documented to match.

    Returned with the contract's own `components` attached, so the internal
    `#/components/schemas/...` references resolve while validating. Failing to
    find one is an assertion rather than a None: a test that quietly validates
    against nothing is the exact failure this module exists to prevent.
    """
    doc = contract(feature)

    operation = doc["paths"].get(path, {}).get(method.lower())
    assert operation, f"{feature}: {method.upper()} {path} is not in the contract"

    responses = operation["responses"]
    documented = responses.get(str(status))
    assert documented, (
        f"{feature}: {method.upper()} {path} documents no {status} response "
        f"(it documents {sorted(responses)})"
    )

    # A $ref at the response level, as the shared error responses use.
    if "$ref" in documented:
        documented = _resolve(doc, documented["$ref"])

    content = documented.get("content")
    assert content, f"{feature}: {method.upper()} {path} {status} documents no body"

    media = content.get("application/json")
    assert media, (
        f"{feature}: {method.upper()} {path} {status} is not JSON (it is {sorted(content)})"
    )

    return {**media["schema"], "components": doc["components"]}


def _resolve(doc: dict[str, Any], ref: str) -> dict[str, Any]:
    """Follow a local JSON pointer. Only `#/`-rooted references are used here."""
    assert ref.startswith("#/"), f"unsupported external reference: {ref}"
    node: Any = doc
    for part in ref.removeprefix("#/").split("/"):
        node = node[part]
    return node
