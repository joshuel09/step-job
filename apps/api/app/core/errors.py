"""Error shapes matching the Error and ValidationError schemas in the contract."""

from fastapi import Request, status
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

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_failed"

    def __init__(self, failures: list[tuple[str, str]], message: str = "Validation failed") -> None:
        super().__init__(message)
        self.failures = [{"field": field, "reason": reason} for field, reason in failures]


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    body: dict[str, object] = {"code": exc.code, "message": exc.message}
    if isinstance(exc, ValidationFailed):
        body["failures"] = exc.failures
    return JSONResponse(status_code=exc.status_code, content=body)
