"""The /profile/translations surface.

No route takes a profile identifier — the owner comes from the verified
session, and the entry named in the body is looked up within it. An entry
id belonging to someone else is a 404, the same answer as one that does
not exist.

An approval is addressed by the entry it belongs to rather than by an id of
its own, because that is how the caller knows it: the interface is
approving the English for *this field of this entry*, and whether an
approval already exists is not something it should have to find out first.
Only deletion takes an id, because by then the row is one the user has been
shown.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.career import service as career_service
from app.core.identity import CallerIdentity, current_identity
from app.db.session import get_session
from app.translations import drafting, schemas, service

router = APIRouter(prefix="/api/v1", tags=["translations"])

Caller = Annotated[CallerIdentity, Depends(current_identity)]
Db = Annotated[Session, Depends(get_session)]


@router.get("/profile/translations", response_model=list[schemas.StoredTranslation])
def list_translations(
    session: Db,
    caller: Caller,
    stale: Annotated[bool | None, Query()] = None,
):
    """Every approved English version, with whether its source has changed."""
    profile = career_service.require_profile(session, caller.user_id)
    return service.stored_for_profile(session, profile.id, stale=stale)


@router.put("/profile/translations", response_model=schemas.StoredTranslation)
def approve_translation(session: Db, caller: Caller, body: schemas.TranslationApproval):
    """Store the user's approved English, replacing any previous approval.

    The text is stored exactly as given (FR-019). Whether they wrote it or
    edited a draft is not recorded, because it makes no difference: once
    approved, the words are theirs.
    """
    profile = career_service.require_profile(session, caller.user_id)
    stored = service.approve(session, profile.id, body)
    # Reported through the same function the list route uses, so an approval
    # the user has just made and the same approval read back a moment later
    # cannot describe themselves differently. It is freshly stale only if
    # the source changed between the two statements in `approve`, which it
    # cannot — but the client never has to wonder.
    return service.report(session, profile.id, stored)


@router.delete("/profile/translations/{translation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_translation(session: Db, caller: Caller, translation_id: uuid.UUID):
    """Remove one stored version. The entry reverts to having none."""
    profile = career_service.require_profile(session, caller.user_id)
    service.remove(session, profile.id, translation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/profile/translations/drafts", response_model=drafting.TranslationDraft)
def draft_translation(session: Db, caller: Caller, body: schemas.TranslationDraftRequest):
    """Ask for a suggested rendering. Nothing is stored (FR-018)."""
    profile = career_service.require_profile(session, caller.user_id)
    return drafting.draft(session, profile.id, body)
