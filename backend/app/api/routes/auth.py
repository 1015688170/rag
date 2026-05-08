from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.auth import (
    SESSION_COOKIE_NAME,
    AuthError,
    create_session_token,
    session_max_age,
    validate_session_token,
    verify_password,
)
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthenticatedResponse(BaseModel):
    authenticated: bool
    username: str


class LogoutResponse(BaseModel):
    authenticated: bool


@router.post("/login", response_model=AuthenticatedResponse)
async def login(payload: LoginRequest, response: Response) -> AuthenticatedResponse:
    if not verify_password(settings, payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_session_token(settings, settings.admin_username)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=session_max_age(settings),
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return AuthenticatedResponse(authenticated=True, username=settings.admin_username)


@router.get("/me", response_model=AuthenticatedResponse)
async def me(request: Request) -> AuthenticatedResponse:
    try:
        payload = validate_session_token(settings, request.cookies.get(SESSION_COOKIE_NAME))
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated") from exc
    return AuthenticatedResponse(authenticated=True, username=str(payload["username"]))


@router.post("/logout", response_model=LogoutResponse)
async def logout(response: Response) -> LogoutResponse:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=settings.session_cookie_secure,
        samesite="lax",
        httponly=True,
    )
    return LogoutResponse(authenticated=False)
