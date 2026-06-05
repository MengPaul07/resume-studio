import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from src.api import routes_v3
from src.api import routes_resources
from src.config import settings
from src.errors import AppError
from src.utils.context import set_user_id, set_lang


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle."""
    # Silence litellm warnings about missing optional deps (botocore etc.)
    import logging as _logging
    _logging.getLogger("LiteLLM").setLevel(_logging.ERROR)
    _logging.getLogger("litellm").setLevel(_logging.ERROR)

    print(f"[startup] {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    print(f"   DEBUG mode: {settings.DEBUG}")
    print(f"   LLM Model: {settings.LLM_MODEL}")
    _auto_seed_jd_library()
    yield
    print("[shutdown] Application shutdown")


def _auto_seed_jd_library():
    """Seed the JD FAISS index from fixtures if it's empty."""
    import json
    from pathlib import Path
    from src.services.rag.jd_repository import JdRepository

    repo = JdRepository()
    # Quick check: if there are already embeddings, skip
    try:
        count = repo.store._conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        if count > 0:
            print(f"   JD library: {count} items indexed")
            return
    except Exception:
        repo.store.clear()

    jds_dir = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "jds"
    if not jds_dir.exists():
        print("   JD library: no fixtures found, skipping seed")
        return

    total = 0
    for fpath in sorted(jds_dir.glob("*.json")):
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            items = data.get("items", []) if isinstance(data, list) else data.get("items", [])
            if items:
                total += repo.seed(items)
        except Exception as exc:
            print(f"   [warn] seed {fpath.name}: {exc}")
    print(f"   JD library: auto-seeded {total} items from fixtures")


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


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=500, content=exc.to_dict())


@app.middleware("http")
async def extract_user_id(request, call_next):
    uid = request.headers.get("X-User-Id", "")
    lang = request.headers.get("X-User-Lang", "zh")
    if uid:
        set_user_id(uid)
    set_lang(lang if lang in ("zh", "en") else "zh")
    response = await call_next(request)
    return response


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
