from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, parents, children, activities, rewards

app = FastAPI(
    title="Capycoin API",
    description="Backend API for Capycoin kids financial app",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(parents.router)
app.include_router(children.router)
app.include_router(activities.router)
app.include_router(rewards.router)


@app.get("/")
async def root():
    return {"message": "Welcome to the Capycoin API!"}
