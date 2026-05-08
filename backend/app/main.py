from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.search_index import router as search_index_router
from app.core.auth import SESSION_COOKIE_NAME, AuthError, validate_session_token
from app.core.config import settings
from app.core.database import init_db

AUTH_WHITELIST = {
    "/health",
    f"{settings.api_prefix}/auth/login",
    f"{settings.api_prefix}/auth/me",
    f"{settings.api_prefix}/auth/logout",
}


def create_application() -> FastAPI:
    init_db()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.middleware("http")
    async def require_api_session(request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        if request.url.path in AUTH_WHITELIST:
            return await call_next(request)
        if request.url.path.startswith(f"{settings.api_prefix}/"):
            try:
                validate_session_token(settings, request.cookies.get(SESSION_COOKIE_NAME))
            except AuthError:
                return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(chat_router, prefix=settings.api_prefix)
    app.include_router(documents_router, prefix=settings.api_prefix)
    app.include_router(search_index_router, prefix=settings.api_prefix)
    return app


app = create_application()
