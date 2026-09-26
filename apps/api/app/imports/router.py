"""The /profile/imports resource tree.

As elsewhere, no route takes a profile or user identifier — the owner comes from
the verified session, so a caller cannot import into someone else's profile or
read someone else's imports.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.career import service as career_service
from app.core.identity import CallerIdentity, current_identity
from app.db.session import get_session
from app.imports import schemas, service
from app.imports.models import ImportStatus, SourceKind

router = APIRouter(prefix="/api/v1", tags=["imports"])

Caller = Annotated[CallerIdentity, Depends(current_identity)]
Db = Annotated[Session, Depends(get_session)]


@router.get("/profile/imports", response_model=list[schemas.ImportOut])
def list_imports(
    session: Db,
    caller: Caller,
    status_filter: Annotated[ImportStatus | None, Query(alias="status")] = None,
):
    """Past imports, so a user can see where a profile entry came from."""
    profile = career_service.require_profile(session, caller.user_id)
    return service.list_for(session, profile, status_filter)


@router.post(
    "/profile/imports",
    response_model=schemas.ImportDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def create_paste_import(session: Db, caller: Caller, body: schemas.PasteImportIn):
    """Import from pasted text.

    Extraction runs here and, for text of ordinary length, finishes before the
    response. A source that takes longer is handed to the worker and the client
    follows this import until it settles.
    """
    profile = career_service.require_profile(session, caller.user_id)

    record = service.create(session, profile, SourceKind.pasted_text)
    service.run(session, profile, record, body.text)
    return record


@router.get("/profile/imports/{import_id}", response_model=schemas.ImportDetailOut)
def get_import(session: Db, caller: Caller, import_id: uuid.UUID):
    """Follow an import to its outcome."""
    profile = career_service.require_profile(session, caller.user_id)
    return service.get(session, profile, import_id)


@router.post("/profile/imports/{import_id}/cancel", response_model=schemas.ImportOut)
def cancel_import(session: Db, caller: Caller, import_id: uuid.UUID):
    """Abandon an import before its proposals reach review (FR-018)."""
    profile = career_service.require_profile(session, caller.user_id)
    return service.cancel(session, profile, import_id)
