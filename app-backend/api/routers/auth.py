from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from api.deps import ClientIp, CurrentSession, Db
from core.email import EmailSender, get_email_sender
from schemas.auth import OtpRequest, OtpVerify, PasswordLogin, SessionResponse
from services import auth
from services.auth import NewSession

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_response(new_session: NewSession) -> SessionResponse:
    return SessionResponse.model_validate(
        {
            "token": new_session.token,
            "expires_at": new_session.session.expires_at,
            "user": new_session.user,
        },
        from_attributes=True,
    )


@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
def request_otp(
    payload: OtpRequest,
    db: Db,
    sender: Annotated[EmailSender, Depends(get_email_sender)],
    ip: ClientIp,
) -> None:
    auth.request_otp(db, payload.email, sender, ip)


@router.post(
    "/otp/verify",
    responses={201: {"model": SessionResponse, "description": "Account created"}},
)
def verify_otp(payload: OtpVerify, db: Db, response: Response) -> SessionResponse:
    new_session, created = auth.verify_otp(
        db, payload.email, payload.code, payload.display_name
    )
    if created:
        response.status_code = status.HTTP_201_CREATED
    return _session_response(new_session)


@router.post("/login")
def login(payload: PasswordLogin, db: Db, ip: ClientIp) -> SessionResponse:
    return _session_response(
        auth.login_with_password(db, payload.login, payload.password, ip)
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(session: CurrentSession, db: Db) -> None:
    auth.logout(db, session)
