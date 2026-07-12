"""FastAPI application factory.

No business logic lives here — only app wiring: routers, middleware,
exception handlers, and docs configuration. See CLAUDE.md.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(debug=settings.debug)
    logger = get_logger()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "%s v%s starting up (environment=%s)",
            settings.app_name,
            settings.app_version,
            settings.environment,
        )
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "LucidUI backend: deterministic UI analysis (app.metrics), LLM interpretation "
            "(app.llm), and independent UIClip evaluation (app.uiclip) for an uploaded "
            "screenshot, plus a ready-to-render `presentation` view over all three "
            "(app.presentation). Comparison between LucidUI and UIClip is not implemented "
            "yet (see ROADMAP.md Phase 6)."
        ),
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS_ALLOW_ORIGINS defaults to "*" for Phase 1 development convenience.
    # Production deployments must restrict this to known origins and should
    # not combine a wildcard origin with allow_credentials=True — see
    # ROADMAP.md Phase 11 ("Secure CORS").
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
