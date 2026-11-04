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


class RenderingAlternative(BaseModel):
    """A phrase that could reasonably render more than one way.

    This is the feature's central difficulty made into a type. 課長 is
    "Manager", "Section Chief" or "Department Head", and those are three
    different claims about the user's seniority. No check can tell which one
    is true — the answer is a fact about their job that only they hold.

    So the ambiguity is returned rather than resolved. A single confident
    rendering would make the product's choice of English word into a claim
    about someone's career, which is what Principle IV forbids; handing back
    the options moves the choice to the person who knows (research.md R-004).
    """

    phrase: str = Field(description="The phrase in the source text, exactly as it appears")
    options: list[str] = Field(
        min_length=2,
        description=(
            "The readings this phrase could take. At least two: one option is "
            "not an alternative, it is a rendering, and belongs in the draft."
        ),
    )
    note: str | None = Field(
        default=None, description="What distinguishes the options, in one line"
    )


class TranslationDraft(BaseModel):
    """A suggestion, not a claim.

    Stored nowhere. It reaches a document only through an approval, which is
    the user's authorship rather than the model's (plan.md G13).

    What this schema does **not** have is the point of it. There is no field
    for a summary, a seniority, a headcount, a duration or an outcome, so a
    provider cannot return an embellishment through it — not because the
    prompt asks it not to, but because there is nowhere to put one. The only
    text it may produce is a rendering of the text it was given.
    """

    text: str = Field(description="The English rendering of the source text, and nothing more")
    source_text: str = Field(
        description=(
            "The text this renders, echoed back so the user compares the two "
            "rather than approving English against nothing."
        )
    )
    alternatives: list[RenderingAlternative] = Field(
        default_factory=list,
        description=(
            "Phrases that could reasonably render more than one way. Empty "
            "when the rendering is unambiguous."
        ),
    )
