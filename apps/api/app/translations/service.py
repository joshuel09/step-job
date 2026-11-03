"""Operations on stored English renderings.

One of them so far: removing an entry's renderings when the entry goes.
FR-024 allows no stored English to outlive the entry it is a translation
of, and `entry_id` cannot be a foreign key — it points at one of four
tables depending on `entry_type` — so nothing in the database enforces it.
This module is the enforcement, and the tests in
`tests/integration/test_translation_flow.py` are the foreign key.
"""

import logging
import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.translations.models import EntryTranslation, TranslatableEntry

logger = logging.getLogger(__name__)


def delete_for_entry(
    session: Session,
    profile_id: uuid.UUID,
    entry_type: TranslatableEntry,
    entry_id: uuid.UUID,
) -> int:
    """Remove every rendering stored against one entry. Returns how many.

    Scoped by profile as well as by entry, so a `entry_id` that collided
    across profiles could not reach another user's rows. Returning the
    count rather than nothing is what lets the caller log a deletion that
    took English with it.
    """
    removed = session.execute(
        delete(EntryTranslation).where(
            EntryTranslation.profile_id == profile_id,
            EntryTranslation.entry_type == entry_type,
            EntryTranslation.entry_id == entry_id,
        )
    ).rowcount

    if removed:
        logger.info(
            "translations deleted with their entry",
            extra={
                "profile_id": profile_id,
                "entry_id": entry_id,
                "entry_type": entry_type.value,
                "count": removed,
            },
        )
    return removed
