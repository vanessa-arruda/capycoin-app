from fastapi import FastAPI

from api.routers import auth, health, households, invitations, me, members
from core.errors import AppError, handle_app_error

app = FastAPI(
    title="Capycoin API",
    description="Backend API for Capycoin kids financial app",
    version="0.1.0",
)
app.add_exception_handler(AppError, handle_app_error)


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
