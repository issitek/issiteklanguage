"""Aplicación FastAPI de Issitek Language."""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .errors import AppError
from .routers import attempts, auth, consents, courses, health, progress, recordings, tts, users
from .storage import get_storage

logger = logging.getLogger("issitek.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # El almacenamiento S3 puede tardar unos segundos en aceptar conexiones: reintentar.
    for attempt in range(1, 31):
        try:
            get_storage().ensure_buckets()
            logger.info("Buckets S3 listos.")
            break
        except Exception as exc:  # noqa: BLE001
            if attempt == 30:
                logger.warning("No se pudieron asegurar los buckets S3: %s", exc)
            else:
                await asyncio.sleep(1)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Issitek Language API",
        version="0.1.0",
        description="API de Issitek Language (talkdrill.com) — Fase 1",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": getattr(request.state, "request_id", ""),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": str(first.get("msg", "Datos inválidos.")),
                    "request_id": getattr(request.state, "request_id", ""),
                }
            },
        )

    app.include_router(health.router)
    prefix = "/api/v1"
    for router in (
        auth.router,
        users.router,
        courses.router,
        attempts.router,
        progress.router,
        consents.router,
        recordings.router,
        tts.router,
    ):
        app.include_router(router, prefix=prefix)

    @app.get("/")
    def root() -> dict:
        return {"service": "issitek-api", "docs": "/docs", "api": prefix}

    return app


app = create_app()
