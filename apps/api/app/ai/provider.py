"""The model boundary.

Constitution §2 requires all model access go through a single abstraction, with
no provider SDK called from feature code (gate G12). This module is that
abstraction: feature code imports the protocol and the exceptions, nothing else.

The three failure classes are separate because they look alike to a user and are
not alike at all. An unreadable document will never succeed; an unavailable
service is worth returning to. Collapsing them would leave the interface unable
to tell someone whether trying again is worth their time (FR-017b).
"""

from typing import Protocol, runtime_checkable

from app.ai.schemas import ExtractionResult, TranslationDraft


class AIError(Exception):
    """Base for every failure crossing the model boundary."""


class ProviderUnavailable(AIError):
    """The service could not be reached, refused the request, or timed out.

    Worth retrying, and worth telling the user to come back later.
    """


class ProviderResponseInvalid(AIError):
    """The service responded, but with something that is not a valid result.

    Distinct from unavailability: the service is up and answering, it just
    produced something unusable. Retried a bounded number of times, then
    reported as a failed extraction rather than an outage.
    """


class NoExtractableContent(AIError):
    """The text held nothing that could be extracted.

    Not an error condition to retry. The document was read and understood to
    contain no career information, which is a correct outcome (FR-016).
    """


@runtime_checkable
class AIProvider(Protocol):
    """Propose things about text. Two operations, both of them proposals.

    "One operation, deliberately" was the first version of this docstring, and
    the sentence that followed it is the one that mattered: a provider is given
    text and nothing else. It receives no database access, no profile, and no
    ability to write anything — it proposes, and deterministic code decides.

    Drafting a translation keeps every one of those properties. It takes text
    and two languages, returns a proposal, and touches nothing. What would
    breach the rule is an operation that took a profile, or wrote, or returned
    something the application stored without a person in between; this does
    none of those (research.md R-003).

    Every provider must return extracted values carrying the passage of source
    text they came from. What the application does with that is not the
    provider's concern, and no provider is trusted to have got it right — the
    verifier checks (research.md R-001).
    """

    def extract_career_information(self, text: str) -> ExtractionResult:
        """Return what the text contains.

        Raises:
            ProviderUnavailable: the service could not be reached.
            ProviderResponseInvalid: the response could not be understood.
        """
        ...

    def draft_translation(
        self, text: str, source_language: str, target_language: str
    ) -> TranslationDraft:
        """Suggest a rendering of this text, for a person to accept or rewrite.

        A suggestion and not a document (FR-018). Nothing stores what this
        returns and no generator can reach it; a draft becomes part of a
        resume only when the user approves it, at which point the words are
        theirs.

        Where a phrase could reasonably render more than one way, the options
        belong in `alternatives` rather than being chosen here. 課長 is
        "Manager", "Section Chief" or "Department Head", and picking one would
        make the product's word choice into a claim about the user's
        seniority (research.md R-004).

        Raises:
            ProviderUnavailable: the service could not be reached.
            ProviderResponseInvalid: the response could not be understood.
        """
        ...
