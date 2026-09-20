"""The /profile resource tree.

No route takes a profile or user identifier: the owner comes from the verified
session (research.md R-006), so a caller cannot ask for someone else's data.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.career import deletion, export, models, proposals, schemas, service, snapshots, stories
from app.core.errors import ConflictError
from app.core.identity import CallerIdentity, current_identity
from app.db.session import get_session

router = APIRouter(prefix="/api/v1", tags=["profile"])

Caller = Annotated[CallerIdentity, Depends(current_identity)]
Db = Annotated[Session, Depends(get_session)]


def _profile(session: Session, caller: CallerIdentity) -> models.CareerProfile:
    return service.require_profile(session, caller.user_id)


def _assemble(session: Session, profile: models.CareerProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "interface_locale": profile.interface_locale,
        "identity": service.get_singleton(session, profile, models.Identity),
        "japan": service.get_singleton(session, profile, models.JapanProfile),
        "preferences": service.get_singleton(session, profile, models.CareerPreference),
        **{name: service.list_entries(session, profile, name) for name in service.SECTION_MODELS},
    }


@router.get("/profile", response_model=schemas.ProfileOut)
def get_profile(session: Db, caller: Caller):
    return _assemble(session, _profile(session, caller))


@router.post("/profile", response_model=schemas.ProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(session: Db, caller: Caller):
    profile = service.get_or_create_profile(session, caller.user_id)
    return _assemble(session, profile)


@router.patch("/profile", response_model=schemas.ProfileOut)
def patch_profile(session: Db, caller: Caller, body: schemas.ProfilePatch):
    """Interface locale only.

    Changing it never alters stored content (FR-023): the entries keep the
    language their author wrote them in.
    """
    profile = _profile(session, caller)
    profile.interface_locale = body.interface_locale
    session.flush()
    return _assemble(session, profile)


@router.delete("/profile", response_model=schemas.DeletionReceiptOut)
def delete_profile(session: Db, caller: Caller):
    profile = _profile(session, caller)
    receipt = deletion.delete_profile(session, profile)
    return {
        "erased_immediately": receipt.erased_immediately,
        "recoverable_until": receipt.recoverable_until.isoformat(),
    }


@router.post("/profile/restore", response_model=schemas.ProfileOut)
def restore_profile(session: Db, caller: Caller):
    profile = deletion.restore_profile(session, caller.user_id)
    return _assemble(session, profile)


@router.get("/profile/completeness")
def get_completeness(session: Db, caller: Caller):
    return service.completeness(session, _profile(session, caller))


@router.post("/profile/export")
def export_profile(session: Db, caller: Caller):
    profile = _profile(session, caller)
    archive = export.build_archive(session, profile)
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="step-job-profile.zip"'},
    )


# --- career stories ---------------------------------------------------------


@router.get("/profile/stories", response_model=list[schemas.CareerStoryOut])
def list_stories(session: Db, caller: Caller, q: str | None = Query(default=None)):
    """Stories, optionally filtered by keyword across all four fields."""
    profile = _profile(session, caller)
    return stories.search(session, profile, q)


@router.post(
    "/profile/stories",
    response_model=schemas.CareerStoryOut,
    status_code=status.HTTP_201_CREATED,
)
def create_story(session: Db, caller: Caller, body: schemas.CareerStoryIn):
    profile = _profile(session, caller)
    return stories.create(session, profile, body.model_dump())


@router.get("/profile/stories/{story_id}", response_model=schemas.CareerStoryOut)
def get_story(session: Db, caller: Caller, story_id: uuid.UUID):
    return stories.get(session, _profile(session, caller), story_id)


@router.patch("/profile/stories/{story_id}", response_model=schemas.CareerStoryOut)
def patch_story(session: Db, caller: Caller, story_id: uuid.UUID, body: schemas.CareerStoryPatch):
    profile = _profile(session, caller)
    return stories.update(session, profile, story_id, body.model_dump(exclude_unset=True))


@router.delete("/profile/stories/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(session: Db, caller: Caller, story_id: uuid.UUID):
    stories.delete(session, _profile(session, caller), story_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- proposed entries -------------------------------------------------------


@router.get("/profile/proposals", response_model=list[schemas.ProposedEntryOut])
def list_proposals(
    session: Db,
    caller: Caller,
    status_filter: Annotated[
        models.ProposalStatus, Query(alias="status")
    ] = models.ProposalStatus.pending,
):
    """Proposals awaiting review. Never part of the profile (FR-018)."""
    profile = _profile(session, caller)
    return proposals.list_for(session, profile, status_filter)


@router.post(
    "/profile/proposals",
    response_model=list[schemas.ProposedEntryOut],
    status_code=status.HTTP_201_CREATED,
)
def submit_proposals(session: Db, caller: Caller, body: list[schemas.ProposedEntryIn]):
    """The contract an import source delivers into. Adds nothing to the profile."""
    profile = _profile(session, caller)
    return proposals.submit(session, profile, [item.model_dump() for item in body])


@router.post(
    "/profile/proposals/{proposal_id}/accept",
    response_model=schemas.AcceptedProposal,
    status_code=status.HTTP_201_CREATED,
)
def accept_proposal(
    session: Db, caller: Caller, proposal_id: uuid.UUID, body: schemas.ProposalAccept | None = None
):
    profile = _profile(session, caller)
    proposal, entry = proposals.accept(
        session, profile, proposal_id, body.payload if body else None
    )
    return {
        "proposal_id": proposal.id,
        "created_entry_id": entry.id,
        "entry_type": proposal.entry_type,
    }


@router.post("/profile/proposals/{proposal_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject_proposal(session: Db, caller: Caller, proposal_id: uuid.UUID):
    proposals.reject(session, _profile(session, caller), proposal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/profile/proposals/{proposal_id}/merge", response_model=schemas.WorkExperienceOut)
def merge_proposal(
    session: Db, caller: Caller, proposal_id: uuid.UUID, body: schemas.ProposalMerge
):
    """Fold a proposal into an existing role. Never automatic (FR-034)."""
    profile = _profile(session, caller)
    return proposals.merge(session, profile, proposal_id, body.target_entry_id, body.payload)


# --- snapshots --------------------------------------------------------------


@router.post(
    "/profile/snapshots",
    response_model=schemas.SnapshotOut,
    status_code=status.HTTP_201_CREATED,
)
def capture_snapshot(session: Db, caller: Caller, body: schemas.SnapshotCapture):
    """Record what a document drew on, at the moment it was generated (FR-028)."""
    profile = _profile(session, caller)
    return snapshots.capture(session, profile, body.document_ref, body.entry_ids)


@router.get("/profile/snapshots/{snapshot_id}", response_model=schemas.SnapshotOut)
def get_snapshot(session: Db, caller: Caller, snapshot_id: uuid.UUID):
    """Return the captured content unchanged, whatever has happened since (FR-029)."""
    profile = _profile(session, caller)
    return snapshots.read(session, profile, snapshot_id)


# --- singleton sections -----------------------------------------------------


@router.put("/profile/identity", response_model=schemas.IdentityOut)
def put_identity(session: Db, caller: Caller, body: schemas.IdentityIn):
    profile = _profile(session, caller)
    return service.put_singleton(session, profile, models.Identity, body.model_dump())


@router.put("/profile/japan", response_model=schemas.JapanProfileOut)
def put_japan(session: Db, caller: Caller, body: schemas.JapanProfileIn):
    profile = _profile(session, caller)
    return service.put_singleton(session, profile, models.JapanProfile, body.model_dump())


@router.put("/profile/preferences", response_model=schemas.CareerPreferenceOut)
def put_preferences(session: Db, caller: Caller, body: schemas.CareerPreferenceIn):
    profile = _profile(session, caller)
    return service.put_singleton(session, profile, models.CareerPreference, body.model_dump())


# --- work experience --------------------------------------------------------


@router.get("/profile/experiences", response_model=list[schemas.WorkExperienceOut])
def list_experiences(session: Db, caller: Caller):
    return service.list_entries(session, _profile(session, caller), "experiences")


@router.post(
    "/profile/experiences",
    response_model=schemas.WorkExperienceOut,
    status_code=status.HTTP_201_CREATED,
)
def create_experience(session: Db, caller: Caller, body: schemas.WorkExperienceIn):
    profile = _profile(session, caller)
    return service.create_experience(session, profile, body.model_dump())


@router.get(
    "/profile/experiences/{experience_id}", response_model=schemas.WorkExperienceDetail
)
def get_experience(session: Db, caller: Caller, experience_id: uuid.UUID):
    """A role with the accomplishments recorded against it (User Story 2)."""
    profile = _profile(session, caller)
    experience = service._owned(session, profile, models.WorkExperience, experience_id)
    return experience


@router.patch("/profile/experiences/{experience_id}", response_model=schemas.WorkExperienceOut)
def patch_experience(
    session: Db, caller: Caller, experience_id: uuid.UUID, body: schemas.WorkExperiencePatch
):
    profile = _profile(session, caller)
    return service.update_experience(
        session, profile, experience_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/profile/experiences/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experience(
    session: Db,
    caller: Caller,
    experience_id: uuid.UUID,
    confirm: bool = Query(default=False),
):
    """FR-013: say what depends on this entry before removing it.

    Without `confirm` the call reports references and changes nothing, so a user
    cannot lose linked accomplishments without being told first.
    """
    profile = _profile(session, caller)
    references = service.references_to_experience(session, profile, experience_id)
    if references and not confirm:
        raise ConflictError(
            "This entry is referenced by other records. Repeat with confirm=true to delete it."
        )
    service.delete_experience(session, profile, experience_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- remaining sections -----------------------------------------------------

_SECTION_SCHEMAS = {
    "education": (schemas.EducationIn, schemas.EducationOut),
    "certifications": (schemas.CertificationIn, schemas.CertificationOut),
    "skills": (schemas.SkillIn, schemas.SkillOut),
    "languages": (schemas.LanguageIn, schemas.LanguageOut),
}


def _register_section(section: str, schema_in: type, schema_out: type) -> None:
    @router.get(f"/profile/{section}", response_model=list[schema_out], name=f"list_{section}")
    def _list(session: Db, caller: Caller):
        return service.list_entries(session, _profile(session, caller), section)

    @router.post(
        f"/profile/{section}",
        response_model=schema_out,
        status_code=status.HTTP_201_CREATED,
        name=f"create_{section}",
    )
    def _create(session: Db, caller: Caller, body: schema_in):  # type: ignore[valid-type]
        profile = _profile(session, caller)
        return service.create_entry(session, profile, section, body.model_dump())

    @router.patch(
        f"/profile/{section}/{{entry_id}}", response_model=schema_out, name=f"patch_{section}"
    )
    def _patch(session: Db, caller: Caller, entry_id: uuid.UUID, body: schema_in):  # type: ignore[valid-type]
        profile = _profile(session, caller)
        return service.update_entry(
            session, profile, section, entry_id, body.model_dump(exclude_unset=True)
        )

    @router.delete(
        f"/profile/{section}/{{entry_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
        name=f"delete_{section}",
    )
    def _delete(session: Db, caller: Caller, entry_id: uuid.UUID):
        profile = _profile(session, caller)
        service.delete_entry(session, profile, section, entry_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


for _section, (_in, _out) in _SECTION_SCHEMAS.items():
    _register_section(_section, _in, _out)
