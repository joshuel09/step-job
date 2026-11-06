"""The /profile/documents/resume surface.

No route takes a profile identifier — the owner comes from the verified
session. Generated documents are not retained, so there is no route to
fetch one by id: a document is produced and streamed, and the snapshot is
what persists.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.career import service as career_service
from app.core.identity import CallerIdentity, current_identity
from app.db.session import get_session
from app.resume import schemas, service

router = APIRouter(prefix="/api/v1", tags=["documents"])

Caller = Annotated[CallerIdentity, Depends(current_identity)]
Db = Annotated[Session, Depends(get_session)]


@router.post("/profile/documents/resume")
def generate_resume(
    session: Db,
    caller: Caller,
    body: schemas.ResumeRequest | None = None,
    preview: Annotated[bool, Query()] = False,
):
    """Produce an English resume and stream it.

    With `preview` the identical document is returned for display rather
    than download — only the disposition differs, so a user never previews
    one thing and downloads another.

    This route calls no model. Every word is a value recorded in the
    profile or an English version the user approved; an entry with no
    stored English version renders as recorded and is reported by the
    readiness route.
    """
    profile = career_service.require_profile(session, caller.user_id)
    request = body or schemas.ResumeRequest()

    pdf, pages, snapshot = service.generate(
        session,
        profile,
        paper_size=request.paper_size,
        include_skills=request.include_skills,
    )

    disposition = "inline" if preview else "attachment"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="resume.pdf"',
            # How long the document runs, so the interface can say when a
            # long career has produced more pages than the convention
            # expects (FR-007).
            "X-Document-Pages": str(pages),
            # What it was based on, so its statements stay traceable after
            # the entries change (FR-015).
            "X-Snapshot-Id": str(snapshot.id),
        },
    )
