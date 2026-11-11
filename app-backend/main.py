from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware import security_headers
from api.routers import (
    approvals,
    auth,
    health,
    households,
    invitations,
    kids,
    me,
    members,
    notifications,
    prizes,
    tasks,
    wallet,
)
from core.config import settings
from core.errors import AppError, handle_app_error

app = FastAPI(
    title="Capycoin API",
    description="Backend API for Capycoin kids financial app",
    version="0.1.0",
)
app.add_exception_handler(AppError, handle_app_error)
app.middleware("http")(security_headers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    # The session token goes in the Authorization header; no cookies are used.
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
)


@app.get("/")
async def root():
    return {"message": "Welcome to the Capycoin API! 🎉"}


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(households.router)
app.include_router(households.household)
app.include_router(members.router)
app.include_router(invitations.router)
app.include_router(invitations.accept_router)
app.include_router(kids.router)
app.include_router(tasks.router)
app.include_router(prizes.router)
app.include_router(wallet.router)
app.include_router(approvals.submissions)
app.include_router(approvals.claims)
app.include_router(notifications.router)
