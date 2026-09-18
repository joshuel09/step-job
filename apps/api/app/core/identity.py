"""Establishing who is calling.

Per research.md R-006, authentication happens at the web layer. The API receives
a verified identity and derives the profile owner from it. It never accepts a
user identifier from the path or body as the means of deciding whose data to
return, which is why no route in this feature takes a profile id.
"""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Header

from app.core.errors import UnauthorisedError


@dataclass(frozen=True)
class CallerIdentity:
    user_id: UUID


async def current_identity(authorization: str | None = Header(default=None)) -> CallerIdentity:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorisedError("A verified session is required.")
    token = authorization.split(" ", 1)[1].strip()
    user_id = _verify(token)
    if user_id is None:
        raise UnauthorisedError("The session could not be verified.")
    return CallerIdentity(user_id=user_id)


def _verify(token: str) -> UUID | None:
    """Resolve a session token to a user.

    Session issuance and verification belong to the web layer; this feature does
    not build sign-in. The local implementation accepts a bare user UUID so the
    API is testable on its own.
    """
    try:
        return UUID(token)
    except ValueError:
        return None
