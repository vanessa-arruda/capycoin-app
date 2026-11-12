from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Error raised by services and turned into an HTTP response."""

    status_code = 400
    headers: dict[str, str] | None = None

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class Unauthorized(AppError):
    status_code = 401
    headers = {"WWW-Authenticate": "Bearer"}


class Forbidden(AppError):
    status_code = 403


class NotFound(AppError):
    status_code = 404


class Conflict(AppError):
    status_code = 409


class InvalidInput(AppError):
    status_code = 422


class TooManyRequests(AppError):
    status_code = 429


async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
    return JSONResponse(
        {"detail": error.detail}, status_code=error.status_code, headers=error.headers
    )
