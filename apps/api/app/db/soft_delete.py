"""Excluding soft-deleted profiles from every read.

FR-027 requires that profile data inside the 30-day recovery window is not
readable by any other feature and appears in no generated document. Enforcing
that per endpoint would make it a convention each new route has to remember, and
one forgetful route would leak deleted career data. Applying it here, at the
data-access layer, makes it structural instead (constitution gate G6).

`with_deleted()` exists for the purge job and for restore, which are the only two
operations that legitimately need to see a deleted profile.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

INCLUDE_DELETED = "include_deleted"


@event.listens_for(Session, "do_orm_execute")
def _filter_soft_deleted(state: Any) -> None:
    if not state.is_select:
        return
    if state.session.info.get(INCLUDE_DELETED) or state.execution_options.get(INCLUDE_DELETED):
        return

    # Imported lazily so that models can import this module for its side effects.
    from app.career.models import CareerProfile

    state.statement = state.statement.options(
        with_loader_criteria(
            CareerProfile,
            lambda cls: cls.deleted_at.is_(None),
            include_aliases=True,
        )
    )


@contextmanager
def with_deleted(session: Session) -> Iterator[Session]:
    """Temporarily see soft-deleted profiles. Only restore and purge may use this."""
    session.info[INCLUDE_DELETED] = True
    try:
        yield session
    finally:
        session.info.pop(INCLUDE_DELETED, None)
