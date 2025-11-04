from fastapi import APIRouter, Body, Depends, HTTPException, Request, status

from app.api.deps import get_auth_service
from app.core.config import AppSettings, get_settings
from app.schemas.auth import DemoLoginRequest, SessionRequest, TokenRefreshRequest, TokenResponse
from app.services.auth import AuthService, OAuth2Identity

router = APIRouter()


def _extract_oauth_identity(request: Request, settings: AppSettings) -> OAuth2Identity:
    email = request.headers.get(settings.oauth2_proxy_email_header)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Прокси аутентификации не передал email пользователя.",
        )

    subject = request.headers.get(settings.oauth2_proxy_user_header) or email
    name_header = settings.oauth2_proxy_name_header or ""
    name = request.headers.get(name_header) if name_header else None
    return OAuth2Identity(subject=subject, email=email, name=name)


@router.post(
    "/session",
    response_model=TokenResponse,
    summary="Запросить токены MindWell для уже аутентифицированного пользователя.",
)
async def create_session(
    request: Request,
    service: AuthService = Depends(get_auth_service),
    settings: AppSettings = Depends(get_settings),
    payload: SessionRequest = Body(default_factory=SessionRequest),
) -> TokenResponse:
    try:
        identity = _extract_oauth_identity(request, settings)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_agent = payload.user_agent or request.headers.get("user-agent")
    ip_address = payload.ip_address or (request.client.host if request.client else None)

    try:
        return await service.create_session_from_oauth(
            identity,
            session_id=payload.session_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/demo",
    response_model=TokenResponse,
    summary="Получить токены по демо-коду из разрешённого списка.",
)
async def login_with_demo_code(
    payload: DemoLoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    user_agent = payload.user_agent or request.headers.get("user-agent")
    ip_address = payload.ip_address or (request.client.host if request.client else None)

    try:
        return await service.login_with_demo_code(
            payload,
            user_agent=user_agent,
            ip_address=ip_address,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/token/refresh",
    response_model=TokenResponse,
    summary="Обновить пару access/refresh токенов и отозвать предыдущий refresh.",
)
async def refresh_token(
    payload: TokenRefreshRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        enriched_payload = payload.model_copy(
            update={
                "user_agent": payload.user_agent or request.headers.get("user-agent"),
                "ip_address": payload.ip_address
                or (request.client.host if request.client else None),
            }
        )
        return await service.refresh_token(enriched_payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
