from fastapi import Request, Response

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
