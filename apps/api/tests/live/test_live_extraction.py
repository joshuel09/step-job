"""One smoke test against a real provider.

Marked `live` and skipped unless a key is present, so continuous integration
never calls a model. Run it deliberately:

    AI_PROVIDER=openai OPENAI_API_KEY=... uv run pytest -m live -v

What it checks is not whether the model extracted well. It checks that the
guarantee holds against a real one: every field that reached a proposal carries
a passage found in the source. If the model fabricates, the verifier drops the
field — that is the system working, not failing, and this test passes either
way as long as nothing unverified survives.
"""

import os

import pytest
from app.imports.evidence import quote_is_supported

pytestmark = pytest.mark.live

RESUME = """\
Example Person

Software Engineer, Example Corp
April 2021 to March 2024
Built and maintained internal services used across the company.

Junior Developer, Sample Industries
June 2018 to March 2021
Worked on the billing system and its reporting tools.

Skills: Ruby, PostgreSQL, TypeScript
"""


@pytest.fixture
def live_provider():
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("no provider key; the live smoke test is opt-in")

    from app.ai.openai_provider import OpenAIProvider

    return OpenAIProvider()


def test_a_real_model_returns_something_extractable(live_provider):
    from app.imports.extraction import extract

    outcome = extract(live_provider, RESUME)

    assert outcome.entries, "expected at least one entry from a plainly written resume"


def test_every_surviving_field_is_supported_by_the_source(live_provider):
    """The guarantee, against a model that can actually fabricate."""
    from app.imports.extraction import extract

    outcome = extract(live_provider, RESUME)

    for entry in outcome.entries:
        for name, record in entry.evidence.items():
            assert quote_is_supported(record["quote"], RESUME), (
                f"{name} reached a proposal with a quote absent from the source"
            )


def test_dropped_fields_are_reported_rather_than_hidden(live_provider):
    """A model that invents should show up as dropped fields, not as silence."""
    from app.imports.extraction import extract

    outcome = extract(live_provider, RESUME)

    # Not an assertion about the count — a good model drops nothing. Only that
    # the number is available, so a run can be inspected.
    assert outcome.dropped_fields >= 0
    assert outcome.dropped_entries >= 0
