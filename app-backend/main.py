from fastapi import FastAPI

app = FastAPI(
    title="Capycoin API",
    description="Backend API for Capycoin kids financial app",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {"message": "Welcome to the Capycoin API! 🎉"}
