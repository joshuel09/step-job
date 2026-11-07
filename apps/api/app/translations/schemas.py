"""Request and response models for the translation routes.

**Nothing here knows a provider exists.** The draft request is in this
module because it is an ordinary request body; the draft *response* is in
`drafting.py` beside the call that produces it. That split is not tidiness:
`app/resume/` reads `StoredTranslation` for its readiness report, and
`tests/unit/test_ai_boundary.py` fails the build if anything under
`app/resume/` can reach `app.ai` — through a schema module as readily as
through a service.
"""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.career.schemas import Stated
from app.translations.models import TranslatableEntry


class EntryField(BaseModel):
    """Which field of which entry, the way every route names its subject.

    `field` is a plain string rather than an enumeration. The fields differ
    per entry type — a skill has a name and a story has four parts — so one
    enumeration would accept `challenge` on a skill and the route would
    have to refuse it anyway. The check that matters is against
    `TRANSLATABLE_FIELDS` for the type in hand, and it lives in
    `entries.require_field` where all four routes reach it.
    """

    entry_type: TranslatableEntry
    entry_id: uuid.UUID
    field: Annotated[str, Field(max_length=64)]


class TranslationApproval(EntryField):
    """The user's approved English for one field of one entry.

    Stored exactly as given (FR-019). Not stripped, not case-corrected, not
    normalised: the words are the user's, including the spacing, and a
    document that quietly tidied them would be printing something they did
    not write. `Stated` refuses a blank and leaves everything else alone.
    """

    text: Annotated[str, Stated]


class TranslationDraftRequest(EntryField):
    """Which field to suggest an English rendering of."""


class StoredTranslation(BaseModel):
    """An approved English version, and whether it still matches its source."""

    id: uuid.UUID
    entry_type: TranslatableEntry
    entry_id: uuid.UUID
    field: str
    text: str
    approved_at: datetime

    #: True when the source text has changed since this was approved. The
    #: stored English is still used — the user approved those words and a
    #: typo fix in the Japanese does not withdraw that (FR-023) — and they
    #: are told it may no longer match.
    is_stale: bool

    #: The source as it reads now, present only when stale. On an approval
    #: that still matches, the source is the text the user already approved
    #: against and repeating it would be noise; when it has changed, it is
    #: the thing they need to see.
    source_text: str | None = None
