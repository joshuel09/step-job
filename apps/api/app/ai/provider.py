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

from app.ai.schemas import ExtractionResult


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
    """Extract structured career information from text.

    One operation, deliberately. Every provider must return values carrying the
    passage of source text they came from; what the application does with that
    is not the provider's concern, and no provider is trusted to have got it
    right — the verifier checks (research.md R-001).

    A provider is given text and nothing else. It receives no database access, no
    profile, and no ability to write anything: it proposes, and deterministic
    code decides.
    """

    def extract_career_information(self, text: str) -> ExtractionResult:
        """Return what the text contains.

        Raises:
            ProviderUnavailable: the service could not be reached.
            ProviderResponseInvalid: the response could not be understood.
        """
        ...
