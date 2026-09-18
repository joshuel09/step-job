"""API entrypoint."""

from fastapi import FastAPI

from app.core.errors import AppError, app_error_handler

app = FastAPI(
    title="Step Job — Master Career Profile",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

app.add_exception_handler(AppError, app_error_handler)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Career routes are registered with User Story 1.
