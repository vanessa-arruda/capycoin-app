from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Covers a 5 MB photo and its note. Every other request is small JSON.
MAX_REQUEST_BYTES = 5 * 1024 * 1024
TOO_LARGE = "The request must be 5 MB or less"

# Swagger UI and ReDoc load scripts and styles, so they get no CSP.
_DOC_PATHS = ("/docs", "/redoc")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # Browsers apply this only over HTTPS.
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}
API_CSP = "default-src 'none'; frame-ancestors 'none'"


async def security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    # Responses hold personal data; don't let browsers or proxies keep them.
    response.headers.setdefault("Cache-Control", "no-store")
    if not request.url.path.startswith(_DOC_PATHS):
        response.headers.setdefault("Content-Security-Policy", API_CSP)
    return response


class LimitRequestSize:
    """Reject request bodies over max_bytes with 413.

    Uvicorn has no body limit, and the app reads a whole upload before it
    checks access, so without this anyone could fill the disk with uploads.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_REQUEST_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        length = Headers(scope=scope).get("content-length", "")
        if length.isdigit() and int(length) > self.max_bytes:
            response = JSONResponse({"detail": TOO_LARGE}, status_code=413)
            await response(scope, receive, send)
            return

        received = 0

        # Counts what is actually sent, for chunked bodies or a wrong length.
        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    # FastAPI passes HTTPException through while reading a body.
                    raise HTTPException(413, TOO_LARGE)
            return message

        await self.app(scope, limited_receive, send)
