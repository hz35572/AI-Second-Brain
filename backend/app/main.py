import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.logging_config import configure_logging, stop_logging_listener
from app.db.session import close_db

configure_logging(settings)
logger = logging.getLogger(__name__)


def _json_safe_validation_errors(errors: list[dict]) -> list[dict]:
    safe_errors: list[dict] = []
    for error in errors:
        safe_error = dict(error)
        ctx = safe_error.get("ctx")
        if isinstance(ctx, dict):
            safe_error["ctx"] = {
                key: value if isinstance(value, str | int | float | bool | type(None)) else str(value)
                for key, value in ctx.items()
            }
        safe_errors.append(safe_error)
    return safe_errors


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepare local storage paths and close DB connections on shutdown."""
    _ = app
    os.makedirs(settings.storage_dir, exist_ok=True)
    os.makedirs(settings.upload_tmp_dir, exist_ok=True)
    logger.info("Application startup complete in %s environment", settings.ENVIRONMENT)
    yield
    await close_db()
    stop_logging_listener()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Second Brain API",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request, exc: StarletteHTTPException):  # noqa: ANN001
        if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": "ERR_HTTP", "message": str(exc.detail), "details": {}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request, exc: RequestValidationError):  # noqa: ANN001
        return JSONResponse(
            status_code=422,
            content={
                "code": "ERR_INVALID_ARGUMENT",
                "message": "参数错误",
                "details": {"errors": _json_safe_validation_errors(exc.errors())},
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request, exc: Exception):  # noqa: ANN001
        logger.exception("Unhandled application exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"code": "ERR_INTERNAL_SERVER_ERROR", "message": "服务器内部错误", "details": {}},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    app.include_router(api_router, prefix=settings.API_V1_STR)
    return app


app = create_app()
