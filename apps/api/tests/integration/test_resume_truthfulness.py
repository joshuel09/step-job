"""Quickstart Scenarios 14 and 18 — the document says only what the user said.

Principle IV, as two tests that can fail rather than a sentence in a
constitution.

**Scenario 14** is about addition. A resume with a bare role on it looks
thin, and the obvious kindness is to write a line of summary. That line
would be the product making a claim the applicant has to answer for in an
interview they did not prepare for.

**Scenario 18** is about reach. The projection reads approved English and
renders it; no model is consulted at generation (FR-017). `test_ai_boundary`
walks the imports under `app/resume/` and fails the build if `app.ai` is
reachable. This is the other half, at runtime: with every way of obtaining a
provider replaced by something that raises on sight, the document still
comes out. A model that cannot be got hold of cannot have written anything
on the page.
"""

import io
import re
from datetime import UTC, date, datetime

import pytest
from pypdf import PdfReader
from sqlalchemy import select

PATH = "/api/v1/profile/documents/resume"

#: Every module that holds a reference to `get_provider`, the canonical
#: one included. Checked against the tree rather than trusted, because a
#: module missing from here is a provider the test below cannot disarm.
#: The English this profile's one role has approved, for the scenario that
#: asks what happens when there is some.
APPROVED_TITLE = "Systems Engineer"

BINDINGS = ("app.ai", "app.translations.drafting", "app.imports.service")

#: The ways a resume writes about a person rather than reporting what they
#: did. None of these is a word the profile below contains, so any of them
#: appearing was put there by something other than the user.
CHARACTERISATIONS = (
    "experienced",
    "skilled",
    "motivated",
    "dedicated",
    "proven",
    "passionate",
    "results-driven",
    "senior",
    "junior",
    "lead",
    "expert",
    "responsible for",
    "summary",
    "objective",
    "profile",
)


def _text(pdf: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)


def _lines(pdf: bytes) -> list[str]:
    return [line for line in (raw.strip() for raw in _text(pdf).splitlines()) if line]


def _generate(client, auth_headers) -> bytes:
    response = client.post(PATH, headers=auth_headers, json={})
    assert response.status_code == 200, response.text
    return response.content


@pytest.fixture
def bare_role(session, user_id):
    """A name, and one role with a title and dates. Nothing else.

    No description, no skills, no education, no certifications — the
    profile with the least on it that still produces a document, which is
    the profile a generous renderer would be most tempted to help.
    """
    from app.career import models, service

    profile = service.get_or_create_profile(session, user_id)
    session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
    session.add(
        models.WorkExperience(
            profile_id=profile.id,
            employer_name="Example Corp",
            employer_name_normalised="example",
            job_title="Software Engineer",
            started_on=date(2021, 4, 1),
            ended_on=date(2024, 3, 31),
            description="",
            source_language=models.Locale.en,
        )
    )
    session.flush()
    return profile


class TestItSaysExactlyThatMuch:
    """Scenario 14. Asserted as the whole page, not as a list of absences.

    A test that forbade particular words would pass the day something
    invented a sentence none of them appear in. Four lines are what this
    profile says, so four lines are what the document has.
    """

    @pytest.fixture
    def document(self, client, auth_headers, bare_role):
        return _generate(client, auth_headers)

    def test_the_page_is_what_the_profile_states_and_no_more(self, document):
        assert _lines(document) == [
            "Taro Yamada",
            "Experience",
            "Software Engineer – Example Corp",
            "Apr 2021 – Mar 2024",
        ]

    @pytest.mark.parametrize("word", CHARACTERISATIONS)
    def test_no_word_characterising_the_applicant(self, document, word):
        """Redundant against the assertion above today, and not tomorrow:
        the moment this document grows a second section, the exact-page
        check becomes a check on a longer list and these stay pointed at
        the thing that matters."""
        assert word not in _text(document).lower()

    def test_no_heading_stands_over_nothing(self, document):
        """An "Education" heading with no education under it is a claim
        about a gap the profile never made (FR-011)."""
        text = _text(document)
        for heading in ("Education", "Skills", "Certifications"):
            assert heading not in text

    def test_the_period_is_the_one_recorded(self, document):
        """Not an approximation, and not a duration. "3 years" is a
        statement the profile did not make and a reader would hold the
        applicant to."""
        assert "Apr 2021 – Mar 2024" in _text(document)
        assert re.search(r"\byears?\b", _text(document), re.IGNORECASE) is None


class TestNoModelCanBeReached:
    """Scenario 18, FR-017.

    Not a provider that returns nothing, and not one whose methods raise —
    a *factory* that raises. A provider object that exists and refuses would
    still let a render path ask for one, which is the thing being forbidden.
    """

    class Asked(Exception):
        pass

    @pytest.fixture
    def no_provider(self, monkeypatch):
        """Every binding of `get_provider`, not only the canonical one.

        Two modules did `from app.ai import get_provider`, which binds the
        function into their own namespace — patching `app.ai` alone would
        leave those reachable and the test would prove less than it says.
        """

        def raise_instead():
            raise TestNoModelCanBeReached.Asked("the render path asked for a provider")

        for module in BINDINGS:
            monkeypatch.setattr(f"{module}.get_provider", raise_instead)

    @pytest.fixture
    def japanese_only(self, session, user_id):
        """A role recorded in Japanese with no approved English.

        The case where translating on the spot would be most useful and is
        most forbidden: the document carries the Japanese, legibly, and
        readiness is what tells the user (FR-017).
        """
        from app.career import models, service

        profile = service.get_or_create_profile(session, user_id)
        session.add(models.Identity(profile_id=profile.id, full_name_latin="Taro Yamada"))
        session.add(
            models.WorkExperience(
                profile_id=profile.id,
                employer_name="株式会社サンプル",
                employer_name_normalised="サンプル",
                job_title="システムエンジニア",
                started_on=date(2015, 4, 1),
                ended_on=date(2021, 3, 31),
                description="社内システムの開発を担当。",
                source_language=models.Locale.ja,
            )
        )
        session.flush()
        return profile

    @pytest.fixture
    def approved_english(self, session, japanese_only):
        """English the user approved, which is the scenario's own Given.

        The three tests below run on a profile with nothing approved,
        where there is no stored English for a render path to check,
        refresh or second-guess. The case the scenario names is the one
        where there is.
        """
        from app.career import models
        from app.translations.models import EntryTranslation, TranslatableEntry

        entry = session.scalars(
            select(models.WorkExperience).where(
                models.WorkExperience.profile_id == japanese_only.id
            )
        ).one()
        session.add(
            EntryTranslation(
                profile_id=japanese_only.id,
                entry_type=TranslatableEntry.work_experience,
                entry_id=entry.id,
                field="job_title",
                language=models.Locale.en,
                approved_text=APPROVED_TITLE,
                approved_at=datetime.now(UTC),
                source_fingerprint="0" * 64,
            )
        )
        session.flush()
        return entry

    def test_the_approved_english_is_printed_without_asking_for_any(
        self, client, auth_headers, approved_english, no_provider
    ):
        """Scenario 18 as it is written. A document assembled from approved
        text has no reason to reach a model, and the way to show that is to
        generate one while every provider factory raises.
        """
        document = _text(_generate(client, auth_headers))

        assert APPROVED_TITLE in document
        assert "システムエンジニア" not in document

    def test_a_resume_still_generates(self, client, auth_headers, japanese_only, no_provider):
        document = _text(_generate(client, auth_headers))

        assert "Taro Yamada" in document
        assert "株式会社サンプル" in document

    def test_the_untranslated_text_appears_as_recorded(
        self, client, auth_headers, japanese_only, no_provider
    ):
        """Not transliterated, not paraphrased, not left blank. The user's
        words, which is why this document embeds a CJK font."""
        document = _text(_generate(client, auth_headers))

        assert "システムエンジニア" in document
        assert "社内システムの開発を担当。" in document

    def test_readiness_answers_too(self, client, auth_headers, japanese_only, no_provider):
        """The route that *reports* what needs English must not be the one
        that quietly asks for it."""
        response = client.get(f"{PATH}/readiness", headers=auth_headers)

        assert response.status_code == 200, response.text
        assert response.json()["can_generate"] is True
        assert response.json()["needs_english"]

    def test_the_trap_is_armed(self, no_provider):
        """The three tests above assert that nothing raised, which is what
        a monkeypatch that silently failed to apply would also produce.

        Every binding, not only the canonical one. A fixture that patched
        `app.ai` alone would satisfy a check that asked `app.ai` — and the
        path this scenario is about is a renderer reaching one of the
        other two.
        """
        import importlib

        for module in BINDINGS:
            with pytest.raises(TestNoModelCanBeReached.Asked):
                importlib.import_module(module).get_provider()

    def test_the_list_of_bindings_is_the_whole_list(self):
        """And the list is not maintained by hand.

        A module added tomorrow with `from app.ai import get_provider`
        binds the function into its own namespace, where the fixture above
        would not reach it — and nothing would fail, which is the way a
        guard stops guarding without anyone noticing.
        """
        import ast
        import pathlib

        app = pathlib.Path(__file__).resolve().parents[2] / "app"
        binding = set()
        for path in app.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom) and any(
                    alias.name == "get_provider" for alias in node.names
                ):
                    binding.add(".".join(path.relative_to(app.parent).with_suffix("").parts))

        assert binding <= set(BINDINGS), sorted(binding - set(BINDINGS))
