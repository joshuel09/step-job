"""Finding the entry an approval or a draft is about.

Every translation route names its subject the same way: an entry type, an
entry id and a field. Three things have to be true before anything is
stored or drafted, and they are checked here so that all four routes check
them identically.

**The entry belongs to this profile.** `entry_id` is not a foreign key — it
points at one of four tables depending on `entry_type` — so nothing in the
database would stop an id from someone else's profile being written into
`entry_translation`. The lookup is scoped by `profile_id` and an id that is
not on this profile is a 404, the same answer as an id that does not exist:
whether another user has that entry is not something this route tells
anyone.

**The field exists on that type.** A rendering stored against a column the
entry does not have is a row nothing will ever read back, and the user is
told now rather than discovering later that an approval did nothing.

**There is something there to render.** An empty field has no English
version; neither does one already written in English.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.career.models import CareerStory, Education, Skill, WorkExperience
from app.core.errors import NotFoundError, ValidationFailed
from app.core.text import has_japanese
from app.translations.models import TRANSLATABLE_FIELDS, TranslatableEntry

#: Which table each translatable type lives in. A dictionary rather than a
#: chain of conditionals, so adding a type is a line here and a line in
#: `TRANSLATABLE_FIELDS` — and forgetting the second is a `KeyError` at the
#: first request rather than a rendering stored under a field name nobody
#: reads.
MODELS: dict[TranslatableEntry, type] = {
    TranslatableEntry.work_experience: WorkExperience,
    TranslatableEntry.education: Education,
    TranslatableEntry.skill: Skill,
    TranslatableEntry.career_story: CareerStory,
}


def find(
    session: Session,
    profile_id: uuid.UUID,
    entry_type: TranslatableEntry,
    entry_id: uuid.UUID,
) -> Any | None:
    """The entry, if this profile has it. Otherwise nothing."""
    model = MODELS[entry_type]
    return session.scalars(
        select(model).where(model.profile_id == profile_id, model.id == entry_id)
    ).first()


def require(
    session: Session,
    profile_id: uuid.UUID,
    entry_type: TranslatableEntry,
    entry_id: uuid.UUID,
) -> Any:
    """The entry, or a 404 that says nothing about whose it might be."""
    entry = find(session, profile_id, entry_type, entry_id)
    if entry is None:
        raise NotFoundError("No such entry on this profile.")
    return entry


def require_field(entry_type: TranslatableEntry, field: str) -> None:
    """Refuse a field this type does not carry.

    422 rather than 404: the entry was found, and what cannot be done is
    what was asked of it. The message names what the type does carry, since
    the caller has evidently got the vocabulary wrong and a bare refusal
    leaves them guessing which word was meant.
    """
    allowed = TRANSLATABLE_FIELDS[entry_type]
    if field not in allowed:
        raise ValidationFailed(
            [("field", f"{entry_type.value} has no translatable field '{field}'")],
            f"A {entry_type.value} can have an English version of: {', '.join(allowed)}.",
        )


def source_text(entry: Any, field: str) -> str:
    """What the entry currently holds in that field, never None.

    `description` and `qualification` are nullable, and a null is the same
    situation as an empty string here: there is nothing to render.
    """
    return getattr(entry, field, None) or ""


def require_translatable(entry: Any, field: str) -> str:
    """The source text, refused when there is nothing to translate.

    Two refusals, both 422 and both about the text rather than the request.
    An empty field has no English version to draft. A field already written
    in English has one — it is the text itself, and asking a model to
    render English into English invites it to improve the wording, which is
    the one thing a draft must not do (FR-013).
    """
    text = source_text(entry, field)
    if not text.strip():
        raise ValidationFailed(
            [("field", "this field is empty, so there is nothing to translate")],
            "There is nothing recorded in that field.",
        )
    if not has_japanese(text):
        raise ValidationFailed(
            [("field", "this text is already in English")],
            "That text already reads as English. Approve it as it stands, or edit it.",
        )
    return text
