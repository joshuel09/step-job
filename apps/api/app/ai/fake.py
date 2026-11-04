"""A provider that never reaches the network.

Every automated test uses this. Continuous integration cannot depend on a paid
external service, and a test whose outcome varies with a model's mood is not a
test.

The behaviours matter as much as the happy path. `fabricate` returns a value with
a quote that is not in the source — exactly what a model does when it invents
something — and the suite asserts that field is dropped. Without a convincing
fabrication to feed it, the test that proves Principle IV holds would be proving
nothing.
"""

import enum
import re

from app.ai.provider import ProviderResponseInvalid, ProviderUnavailable
from app.ai.schemas import (
    ExtractedEntry,
    ExtractedEntryType,
    ExtractedField,
    ExtractionResult,
    RenderingAlternative,
    SourceLanguage,
    TranslationDraft,
)

_DATE = re.compile(r"\b(19|20)\d{2}\b|令和|平成|昭和")
_ROLE = re.compile(r"engineer|developer|designer|manager|エンジニア|デザイナー", re.I)
# Japanese documents separate a role from its employer with 、not a comma, so a
# fake that only knows about ASCII would find nothing in a 職務経歴書.
_SEPARATOR = re.compile(r"[,、]")


# A crude glossary, covering the phrases the fixtures use. Substitution
# rather than anything cleverer: the fake's job is to be the same every time,
# and a test that reads `"Section Manager" in draft.text` should be able to
# see from here why.
_GLOSSARY = {
    "エンジニア": "Engineer",
    "ソフトウェアエンジニア": "Software Engineer",
    "シニアエンジニア": "Senior Engineer",
    "ビルド時間を半分にした": "Halved the build time",
    "ビルドが遅かった": "The build was slow",
    "キャッシュを導入した": "Introduced caching",
    "半分になった": "It halved",
    "大学": "University",
    "情報工学": "Computer Science",
    "学士": "Bachelor's degree",
}

# Phrases whose English is a choice rather than a lookup, and the choices.
# Each is a claim about seniority that only the user can settle, so the fake
# returns the options exactly as a provider should (research.md R-004).
_AMBIGUOUS = {
    "課長": (
        ["Manager", "Section Chief", "Department Head"],
        "Three different claims about how senior the role was.",
    ),
    "部長": (
        ["Director", "General Manager", "Head of Department"],
        "Rank above 課長, but the English word depends on the company's size.",
    ),
    "主任": (
        ["Senior Staff", "Team Lead", "Supervisor"],
        "Whether anyone reported to you is the distinction, and only you know.",
    ),
}

# An ambiguous phrase still has to render as *something* in the draft, and it
# renders as the first option rather than a fourth word of its own. A draft
# whose wording is not among the alternatives beside it asks the user to
# choose between options none of which is what they are looking at.
_RENDERINGS = _GLOSSARY | {phrase: options[0] for phrase, (options, _) in _AMBIGUOUS.items()}


class FakeBehaviour(enum.StrEnum):
    """What the fake does when asked to extract, or to draft a translation."""

    extract = "extract"
    """Return entries quoting the source honestly."""

    fabricate = "fabricate"
    """Return a field whose quote does not appear in the source."""

    quote_missing = "quote_missing"
    """Return a field with an empty quote."""

    whitespace_variant = "whitespace_variant"
    """Quote the source but with line breaks and spacing changed.

    Extracted document text routinely differs from the original this way, so
    this must be accepted — the verifier normalises whitespace.
    """

    near_miss = "near_miss"
    """Quote something close to the source but not actually present.

    The case that would slip through if the verifier ever used fuzzy matching.
    """

    unavailable = "unavailable"
    empty = "empty"
    """No entries extracted; or, for a draft, a rendering with no words in it.

    A provider that answers with a blank is answering, so this is not an
    invalid response — it is a usable-looking draft that says nothing, which
    is the shape FR-025 exists to refuse.
    """

    invalid = "invalid"


class FakeAIProvider:
    """Scripted results, no network access."""

    def __init__(
        self,
        behaviour: FakeBehaviour | str = FakeBehaviour.extract,
        *,
        fail_times: int = 0,
    ) -> None:
        self.behaviour = FakeBehaviour(behaviour)
        # How many calls fail before succeeding, for exercising bounded retry.
        self.fail_times = fail_times
        self.calls = 0

    def extract_career_information(self, text: str) -> ExtractionResult:
        self.calls += 1

        if self.fail_times and self.calls <= self.fail_times:
            raise ProviderUnavailable("scripted transient outage")

        match self.behaviour:
            case FakeBehaviour.unavailable:
                raise ProviderUnavailable("scripted outage")
            case FakeBehaviour.invalid:
                raise ProviderResponseInvalid("scripted unusable response")
            case FakeBehaviour.empty:
                return ExtractionResult(entries=[], not_found=list(ExtractedEntryType))

        return ExtractionResult(entries=[self._entry(text)], not_found=[])

    def _entry(self, text: str) -> ExtractedEntry:
        lines = [line for line in text.splitlines() if line.strip()]

        # A role line, wherever it appears. A document does not helpfully open
        # with one — a resume usually starts with a name — so scanning for it
        # is what a real extraction does and what keeps the fake honest against
        # fixtures as well as pasted snippets.
        first_line = next(
            (line for line in lines if _SEPARATOR.search(line) and _ROLE.search(line)),
            next(iter(lines), text),
        )
        language = SourceLanguage.ja if re.search(r"[ぁ-んァ-ン一-龯]", text) else SourceLanguage.en

        title = "エンジニア" if language is SourceLanguage.ja else "Software Engineer"
        quote = self._quote(first_line)
        fields = {"job_title": ExtractedField(value=title, quote=quote)}

        # Behaviours that represent a *correct* extraction also quote the
        # employer, so the entry has everything a work experience needs. Only
        # the dishonest behaviours return a partial entry — otherwise a test
        # could pass because a field was missing rather than because the
        # verifier rejected it.
        honest = {FakeBehaviour.extract, FakeBehaviour.whitespace_variant}
        if self.behaviour in honest and _SEPARATOR.search(first_line):
            employer = _SEPARATOR.split(first_line, maxsplit=1)[1].strip()
            fields["employer_name"] = ExtractedField(value=employer, quote=self._quote(first_line))

            # A real resume states its dates, and an entry without a start date
            # cannot be accepted into a profile. Modelling that here keeps the
            # happy path honest rather than passing on a technicality.
            dated = next((line for line in text.splitlines() if _DATE.search(line)), None)
            if dated:
                fields["started_on"] = ExtractedField(
                    value="2021-04-01", quote=self._quote(dated.strip())
                )

        return ExtractedEntry(
            entry_type=ExtractedEntryType.work_experience,
            source_language=language,
            fields=fields,
        )

    def _quote(self, line: str) -> str:
        match self.behaviour:
            case FakeBehaviour.fabricate:
                # Nothing like this appears in any source the tests use.
                return "Director of Engineering at a company never mentioned"
            case FakeBehaviour.quote_missing:
                return ""
            case FakeBehaviour.whitespace_variant:
                return re.sub(r"\s+", "\n  ", line)
            case FakeBehaviour.near_miss:
                # One word different: close enough that fuzzy matching would let
                # it through, which is exactly why there is no fuzzy matching.
                if "Engineer" in line:
                    return line.replace("Engineer", "Architect")
                return line + " Ltd"
            case _:
                return line

    def draft_translation(
        self, text: str, source_language: str, target_language: str
    ) -> TranslationDraft:
        """A rendering by substitution, and the ambiguities left unresolved.

        There is no dishonest behaviour scripted here, and that absence is
        the design rather than a gap. The dishonest draft would be one that
        embellished — a seniority, a headcount, an outcome the source does
        not state — and `TranslationDraft` has nowhere to put one. The fake
        cannot return what the schema cannot carry, which is the same reason
        a real provider cannot.

        What *is* scripted is the pair that have nothing to do with content:
        an outage and an unusable answer. Ambiguity is not scripted, because
        it is a property of the text — a source with 課長 in it has a choice
        to offer and one without it does not, whatever the fake is told to
        do.
        """
        self.calls += 1

        if self.fail_times and self.calls <= self.fail_times:
            raise ProviderUnavailable("scripted transient outage")

        match self.behaviour:
            case FakeBehaviour.unavailable:
                raise ProviderUnavailable("scripted outage")
            case FakeBehaviour.invalid:
                raise ProviderResponseInvalid("scripted unusable response")
            case FakeBehaviour.empty:
                return TranslationDraft(text="", source_text=text, alternatives=[])

        rendered = text
        for japanese, english in sorted(_RENDERINGS.items(), key=lambda kv: -len(kv[0])):
            rendered = rendered.replace(japanese, english)

        return TranslationDraft(
            text=rendered,
            source_text=text,
            alternatives=[
                RenderingAlternative(phrase=phrase, options=list(options), note=note)
                for phrase, (options, note) in _AMBIGUOUS.items()
                if phrase in text
            ],
        )
