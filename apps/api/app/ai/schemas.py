"""The structured shape a provider must return.

Every field a provider fills must arrive with the passage of source text it was
taken from. That is not a convention the prompt asks for politely — it is the
shape, so a response without quotes fails validation before any application code
sees it.

The quote is what the verifier checks against the source (research.md R-001). A
value the model invented has no passage behind it and cannot survive that check,
which is how Principle IV stops being an instruction and becomes an invariant.
"""

import enum

from pydantic import BaseModel, Field


class ExtractedField(BaseModel):
    """One value, and the words it came from."""

    value: str = Field(description="The extracted value, exactly as the source states it")
    quote: str = Field(
        description=(
            "The passage of the source text this value was taken from, copied "
            "verbatim. If no passage supports the value, omit the field entirely "
            "rather than supplying a quote that is not in the source."
        )
    )


class ExtractedEntryType(enum.StrEnum):
    work_experience = "work_experience"
    education = "education"
    certification = "certification"
    skill = "skill"
    language = "language"


class SourceLanguage(enum.StrEnum):
    en = "en"
    ja = "ja"


class ExtractedEntry(BaseModel):
    """One piece of career information found in a source.

    Fields are optional throughout. A source that does not state a job title
    produces an entry without one — that is a correct result, and inventing the
    missing part is the failure this feature exists to avoid (FR-008).
    """

    entry_type: ExtractedEntryType
    source_language: SourceLanguage = Field(
        description="The language the source text for this entry was written in"
    )
    fields: dict[str, ExtractedField] = Field(
        default_factory=dict,
        description=(
            "Only fields the source actually supports. Omit anything the "
            "document does not state; do not infer, round or complete values."
        ),
    )


class ExtractionResult(BaseModel):
    """Everything a provider found in one source."""

    entries: list[ExtractedEntry] = Field(default_factory=list)
    not_found: list[ExtractedEntryType] = Field(
        default_factory=list,
        description=(
            "Kinds of career information looked for and not present, so the user "
            "can see what the document lacked rather than assume it was lost."
        ),
    )
