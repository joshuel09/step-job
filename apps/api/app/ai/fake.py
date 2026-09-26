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
    SourceLanguage,
)

_DATE = re.compile(r"\b(19|20)\d{2}\b|令和|平成|昭和")


class FakeBehaviour(enum.StrEnum):
    """What the fake does when asked to extract."""

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
                return ExtractionResult(
                    entries=[], not_found=list(ExtractedEntryType)
                )

        return ExtractionResult(entries=[self._entry(text)], not_found=[])

    def _entry(self, text: str) -> ExtractedEntry:
        first_line = next((line for line in text.splitlines() if line.strip()), text)
        language = SourceLanguage.ja if re.search(r"[ぁ-んァ-ン一-龯]", text) else SourceLanguage.en

        quote = self._quote(first_line)
        fields = {"job_title": ExtractedField(value="Software Engineer", quote=quote)}

        # Behaviours that represent a *correct* extraction also quote the
        # employer, so the entry has everything a work experience needs. Only
        # the dishonest behaviours return a partial entry — otherwise a test
        # could pass because a field was missing rather than because the
        # verifier rejected it.
        honest = {FakeBehaviour.extract, FakeBehaviour.whitespace_variant}
        if self.behaviour in honest and "," in first_line:
            employer = first_line.split(",", 1)[1].strip()
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
