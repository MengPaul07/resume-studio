from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import routes_v3
from src.api import routes_resources
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle."""
    print(f"[startup] {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    print(f"   DEBUG mode: {settings.DEBUG}")
    print(f"   LLM Model: {settings.LLM_MODEL}")
    yield
    print("[shutdown] Application shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="resume-builder API with CLI-style session loop (v3).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_v3.router, prefix=settings.API_PREFIX)
app.include_router(routes_resources.router, prefix=settings.API_PREFIX)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "app_name": settings.APP_NAME,
    }


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
