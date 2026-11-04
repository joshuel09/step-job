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

from pydantic import BaseModel, Field, field_validator


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
            "The readings this phrase could take. At least two, and different "
            "from each other: one option is not an alternative, it is a "
            "rendering, and belongs in the draft."
        ),
    )
    note: str | None = Field(
        default=None, description="What distinguishes the options, in one line"
    )

    @field_validator("options")
    @classmethod
    def _options_are_a_real_choice(cls, options: list[str]) -> list[str]:
        """Two of the same word is not two options.

        `min_length` counts entries, and ["Manager", "Manager"] has two. A
        user shown that is being asked to choose and given nothing to choose
        between, which is worse than a confident draft: it looks as though
        the ambiguity was surfaced.
        """
        distinct = {option.strip() for option in options if option.strip()}
        if len(distinct) < 2:
            raise ValueError(
                "An alternative needs at least two readings that differ. "
                "A single reading is the draft, not a choice."
            )
        return options


class TranslationDraft(BaseModel):
    """A suggestion, not a claim.

    Stored nowhere. It reaches a document only through an approval, and what
    is stored then is the user's text — whether they wrote it, edited this,
    or accepted it unchanged. That is where Principle IV is held for the
    translation step, and this schema is not it (plan.md G13).

    Being clear about what the shape does and does not buy, because it is
    easy to overstate:

    - It **does** keep an embellishment from becoming a structured fact.
      There is no field for a summary, a seniority, a headcount, a duration
      or an outcome, so a provider cannot return one as data that something
      downstream reads, stores or renders as though the profile stated it.
    - It **does not** stop a model writing "Led a team of twelve" inside
      `text`. `text` is free prose, and no schema can tell a rendering from
      an invention. Nothing mechanical can: unlike extraction, there is no
      passage to check a translation against, because a rendering of 課長
      does not appear in the Japanese.

    So the guarantee is the review, not the type. The draft is shown beside
    its source for a person to compare, and nothing of a model's reaches a
    document that person has not approved.
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
