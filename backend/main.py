from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from backend.core.config import settings
from backend.core.logging import configure_logging
from backend.database import SessionLocal, engine
from backend.routers import auth, tasks


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, send_default_pii=False)
    yield
    await engine.dispose()


app = FastAPI(title="Flunky", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router, prefix="/v1")
app.include_router(tasks.router, prefix="/v1")
# Keep the original API functional while clients migrate to /v1.
app.include_router(auth.router, include_in_schema=False)
app.include_router(tasks.router, include_in_schema=False)


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = str(uuid4())
    request.state.request_id = request_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    try:
        response = await call_next(request)
    except Exception:
        structlog.get_logger().exception("request_failed")
        response = JSONResponse(
            {
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "request_id": request_id,
                }
            },
            status_code=500,
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["Cache-Control"] = "no-store"
    structlog.get_logger().info(
        "request", method=request.method, path=request.url.path, status=response.status_code
    )
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        {
            "detail": exc.detail,
            "error": {
                "code": str(exc.status_code),
                "message": str(exc.detail),
                "request_id": request.state.request_id,
            },
        },
        status_code=exc.status_code,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Do not echo rejected input: it can include passwords or access tokens.
    return JSONResponse(
        {
            "detail": "Invalid request",
            "error": {
                "code": "validation_error",
                "message": "Invalid request; check the API schema",
                "request_id": request.state.request_id,
            },
        },
        status_code=422,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> JSONResponse:
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT version_num FROM alembic_version"))
        return JSONResponse({"status": "ready"})
    except SQLAlchemyError:
        return JSONResponse(
            {"status": "not_ready", "message": "Database unavailable or migrations missing"},
            status_code=503,
        )
