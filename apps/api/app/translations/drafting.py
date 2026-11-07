"""Asking a model for a suggested English rendering, and storing nothing.

The one place in feature 005 that calls a provider, and its own module for
that reason. `app/resume/` reads `translations/service.py` for the
readiness report, and `tests/unit/test_ai_boundary.py` fails the build if
anything under `app/resume/` can reach `app.ai` transitively — so the
provider call cannot live in the module the resume reads. The separation is
load-bearing, not organisational.

**Nothing here writes.** A draft is returned to the user and forgotten. It
becomes an English version only when the user approves it through
`service.approve`, which is what keeps an unapproved rendering out of every
document (FR-018, SC-010). There is no session write in this file, and a
test asserts that a request for a draft leaves the profile exactly as it
was.
"""

import logging
import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai import get_provider
from app.ai.provider import AIProvider, ProviderResponseInvalid, ProviderUnavailable
from app.ai.schemas import RenderingAlternative
from app.core.errors import UpstreamUnavailable, UpstreamUnusable
from app.core.settings import get_settings
from app.translations import entries, schemas
from app.translations.models import TranslatableEntry

logger = logging.getLogger(__name__)

#: What is being rendered into what. Fixed rather than a parameter: the
#: feature is an English resume for a career recorded in Japanese, and a
#: pair the caller chose would be a pair nothing in the product can store
#: the result of — `entry_translation.language` is the target, and `en` is
#: the only value any document reads.
SOURCE_LANGUAGE = "ja"
TARGET_LANGUAGE = "en"


class TranslationDraft(BaseModel):
    """A suggestion, addressed to the field it is a suggestion for.

    The same three shapes the provider returns, with the subject added back
    on. A draft that travelled without saying which field it was for would
    have to be matched up by whoever asked, and a resume is exactly the
    place where putting one role's English under another role is a mistake
    nobody notices.
    """

    entry_type: TranslatableEntry
    entry_id: uuid.UUID
    field: str

    #: The source as the profile holds it, returned so the user compares
    #: the two rather than approving English against nothing.
    source_text: str
    text: str
    alternatives: list[RenderingAlternative] = []


def draft(
    session: Session,
    profile_id: uuid.UUID,
    request: schemas.TranslationDraftRequest,
    *,
    provider: AIProvider | None = None,
) -> TranslationDraft:
    """Suggest an English rendering of one field. Store nothing.

    Retries are bounded and cover both failures, because both can be
    momentary: a request that could not be delivered, and an answer that
    came back malformed. What is not momentary is reported as what it is —
    503 when the service could not be reached and 502 when it answered with
    something unusable. A person reads those two as the same disappointment
    and they are not the same at all: one is worth coming back to in five
    minutes and the other never will be.
    """
    entry = entries.require(session, profile_id, request.entry_type, request.entry_id)
    entries.require_field(request.entry_type, request.field)
    source = entries.require_translatable(entry, request.field)

    suggested = _ask(provider or get_provider(), source, profile_id)

    logger.info(
        "translation drafted",
        extra={
            "profile_id": profile_id,
            "entry_id": request.entry_id,
            "entry_type": request.entry_type.value,
            "outcome": request.field,
            # How many readings the user is being asked to choose between,
            # never the readings themselves.
            "count": len(suggested.alternatives),
        },
    )

    return TranslationDraft(
        entry_type=request.entry_type,
        entry_id=request.entry_id,
        field=request.field,
        # The profile's text, not the provider's echo of it. A draft is
        # shown beside the source so the user can judge it; the source
        # half of that comparison should come from the profile rather than
        # from the thing being judged.
        source_text=source,
        text=suggested.text,
        alternatives=list(suggested.alternatives),
    )


def _ask(provider: AIProvider, source: str, profile_id: uuid.UUID):
    """Call the provider, bounded, and turn a lasting failure into a status."""
    attempts = max(1, get_settings().ai_max_retries)
    last: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return provider.draft_translation(source, SOURCE_LANGUAGE, TARGET_LANGUAGE)
        except (ProviderUnavailable, ProviderResponseInvalid) as error:
            last = error
            if attempt < attempts:
                logger.info(
                    "translation draft failed, retrying",
                    extra={"profile_id": profile_id, "count": attempt, "outcome": "retry"},
                )

    if isinstance(last, ProviderUnavailable):
        logger.info(
            "translation draft abandoned",
            extra={"profile_id": profile_id, "outcome": "unavailable"},
        )
        raise UpstreamUnavailable(
            "The translation service could not be reached. Please try again shortly."
        )

    logger.info(
        "translation draft abandoned",
        extra={"profile_id": profile_id, "outcome": "unusable"},
    )
    raise UpstreamUnusable(
        "The translation service answered with something we could not read. "
        "Write the English yourself, or try again later."
    )
