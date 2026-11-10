from fastapi import FastAPI

from api.routers import health

app = FastAPI(
    title="Capycoin API",
    description="Backend API for Capycoin kids financial app",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {"message": "Welcome to the Capycoin API! 🎉"}


app.include_router(health.router)
