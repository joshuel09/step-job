"""API entrypoint."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.career.router import router as career_router
from app.core.errors import AppError, app_error_handler, request_validation_handler
from app.core.logging import configure as configure_logging
from app.core.settings import get_settings
from app.imports.router import router as imports_router
from app.rirekisho.router import router as rirekisho_router

configure_logging()
settings = get_settings()

# Response headers a browser is allowed to read. Without this a cross-origin
# fetch sees the document but none of these, because only a short safelist is
# exposed by default — the page count and the snapshot id would silently be
# undefined in the interface while every server-side test still passed.
EXPOSED_HEADERS = ["Content-Disposition", "X-Document-Pages", "X-Snapshot-Id"]

app = FastAPI(
    title="Step Job — Master Career Profile",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.web_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=EXPOSED_HEADERS,
)

app.add_exception_handler(AppError, app_error_handler)
# Schema-level rejections get the documented shape too, so the interface can
# name the offending field rather than showing a generic failure (FR-014).
app.add_exception_handler(RequestValidationError, request_validation_handler)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(career_router)
app.include_router(imports_router)
app.include_router(rirekisho_router)
