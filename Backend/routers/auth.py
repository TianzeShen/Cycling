from fastapi import APIRouter, HTTPException

try:
    from Backend.schemas import AuthLoginRequest, AuthRegisterRequest, AuthUserResponse
    from Backend.services.auth_service import (
        UsernameTakenError,
        get_user_identity,
        login_with_username,
        register_username,
    )
except ModuleNotFoundError:
    from schemas import AuthLoginRequest, AuthRegisterRequest, AuthUserResponse
    from services.auth_service import (
        UsernameTakenError,
        get_user_identity,
        login_with_username,
        register_username,
    )


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthUserResponse, summary="Bind a username to the current guest UUID")
def register_auth_user(payload: AuthRegisterRequest) -> AuthUserResponse:
    try:
        return register_username(payload)
    except UsernameTakenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/login", response_model=AuthUserResponse, summary="Recover a user UUID by username")
def login_auth_user(payload: AuthLoginRequest) -> AuthUserResponse:
    try:
        return login_with_username(payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/me", response_model=AuthUserResponse, summary="Resolve current identity by UUID")
def get_auth_me(user_id: str) -> AuthUserResponse:
    return get_user_identity(user_id)
