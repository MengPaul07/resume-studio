import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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


frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.exists(frontend_dist):
    # Serve built React frontend (SPA)
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "message": f"Welcome to {settings.APP_NAME} (Frontend build not found)",
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
