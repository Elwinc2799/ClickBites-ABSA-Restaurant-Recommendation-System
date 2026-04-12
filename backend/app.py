import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from database import get_pool, close_pool
from routers import business, review, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: attempt DB pool — non-fatal so Space starts even if pooler isn't ready yet
    try:
        await get_pool()
    except Exception as e:
        print(f"[startup] DB pool not ready: {e} — will retry per-request")
    yield
    # Shutdown: close pool
    await close_pool()


app = FastAPI(
    title="ClickBites API",
    version="2.0.0",
    description="Restaurant recommendation system with ABSA",
    lifespan=lifespan,
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(business.router)
app.include_router(review.router)
app.include_router(user.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


# Handle JSON body for login (was request.get_json() in Flask)
@app.middleware("http")
async def json_body_middleware(request: Request, call_next):
    return await call_next(request)
