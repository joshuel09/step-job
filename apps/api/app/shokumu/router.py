"""The /profile/documents/shokumu-keirekisho surface.

No route takes a profile identifier — the owner comes from the verified
session. Generated documents are not retained, so there is no route to fetch
one by id: a document is produced and streamed, and the snapshot is what
persists.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.career import service as career_service
from app.core.identity import CallerIdentity, current_identity
from app.db.session import get_session
from app.shokumu import schemas, service

router = APIRouter(prefix="/api/v1", tags=["documents"])

Caller = Annotated[CallerIdentity, Depends(current_identity)]
Db = Annotated[Session, Depends(get_session)]


@router.post("/profile/documents/shokumu-keirekisho")
def generate_shokumu_keirekisho(
    session: Db,
    caller: Caller,
    body: schemas.ShokumuKeirekishoRequest | None = None,
    preview: Annotated[bool, Query()] = False,
):
    """Produce a 職務経歴書 and stream it.

    With `preview` the identical document is returned for display rather than
    download — only the disposition differs, so a user never previews one
    thing and downloads another.
    """
    profile = career_service.require_profile(session, caller.user_id)
    request = body or schemas.ShokumuKeirekishoRequest()

    pdf, pages, snapshot = service.generate(
        session,
        profile,
        arrangement=request.arrangement,
        date_convention=request.date_convention,
        paper_size=request.paper_size,
    )

    disposition = "inline" if preview else "attachment"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="shokumu-keirekisho.pdf"',
            # How long the document runs, so the interface can say when a long
            # career has produced more pages (FR-011).
            "X-Document-Pages": str(pages),
            # What it was based on, so its statements stay traceable after the
            # entries change (FR-017).
            "X-Snapshot-Id": str(snapshot.id),
        },
    )
