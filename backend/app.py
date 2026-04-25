from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.auth import router as auth_router
from backend.api.routes.export import router as export_router
from backend.api.routes.integrations import router as integrations_router
from backend.api.routes.manager import router as manager_router
from backend.api.routes.periods import router as periods_router
from backend.api.routes.schedule import router as schedule_router
from backend.api.routes.templates import router as templates_router
from backend.core.config import settings
from backend.db import Base, engine


def _get_cors_origins() -> list[str]:
    return [
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
        if origin.strip()
    ]


def create_app() -> FastAPI:
    app = FastAPI(
        title="T2 Schedule API",
        description="Authentication, roles, and scheduling API for T2 website",
        version="1.0.0",
    )

    if settings.AUTO_CREATE_SCHEMA:
        Base.metadata.create_all(bind=engine)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    async def health_check():
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(schedule_router)
    app.include_router(periods_router)
    app.include_router(manager_router)
    app.include_router(export_router)
    app.include_router(templates_router)
    app.include_router(integrations_router)

    return app


app = create_app()

