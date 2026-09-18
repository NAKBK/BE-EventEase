from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.database import get_engine
from app.core.errors import register_error_handlers
from app.modules.auth.controller import router as auth_router
from app.modules.events.controller import router as events_router
from app.modules.users.controller import router as needs_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="EventEase API", version="0.1.0")
    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(events_router, prefix="/api/events")
    app.include_router(needs_router, prefix="/api/me")

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            from app.core.errors import APIError

            raise APIError(503, "DATABASE_UNAVAILABLE", "Database tidak tersedia")
        return {"status": "ok"}

    return app


app = create_app()
