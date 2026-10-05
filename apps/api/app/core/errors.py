"""Error shapes matching the Error and ValidationError schemas in the contract."""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base for errors that map onto a documented response."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class UnauthorisedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorised"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationFailed(AppError):
    """A rejection that names the offending field and explains why.

    FR-014 requires the interface be able to show the reason rather than a
    generic failure, so every rejection carries field-level detail.
    """

    # Literal rather than the starlette constant: the name changed between
    # starlette versions, and the code did not.
    status_code = 422
    code = "validation_failed"

    def __init__(self, failures: list[tuple[str, str]], message: str = "Validation failed") -> None:
        super().__init__(message)
        self.failures = [{"field": field, "reason": reason} for field, reason in failures]


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    body: dict[str, object] = {"code": exc.code, "message": exc.message}
    if isinstance(exc, ValidationFailed):
        body["failures"] = exc.failures
    return JSONResponse(status_code=exc.status_code, content=body)


# Where a rejection came from. Stripped from the field path, because a user
# reading "proficiency" understands it and "body.proficiency" is noise.
_LOCATIONS = {"body", "query", "path", "header", "cookie"}


def _field(location: tuple) -> str:
    """A pydantic `loc` as the field name the interface shows."""
    parts = [str(p) for p in location]
    if parts and parts[0] in _LOCATIONS:
        parts = parts[1:]
    return ".".join(parts) or "body"


async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Give schema-level rejections the same shape as everything else.

    Without this, a request that fails pydantic validation — a wrong enum, a
    missing required field, a malformed date — returns FastAPI's own
    `{"detail": [...]}`. That is not the documented ValidationError, so the
    interface cannot read it field by field and falls back to a generic
    failure, which FR-014 exists to prevent. These are the most common
    mistakes a user makes, so they are the ones that most need naming.
    """
    failures = [(_field(error["loc"]), error["msg"]) for error in exc.errors()]
    return await app_error_handler(_, ValidationFailed(failures))
