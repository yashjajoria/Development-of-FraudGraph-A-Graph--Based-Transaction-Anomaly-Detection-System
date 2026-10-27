import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.api.v1 import auth, copilot, system
from app.core.config import settings
from app.core.db import Base, engine
from app.models import copilot as _models  # noqa: F401  (registers tables)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="FraudGraph AI", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_methods=["*"],
                   allow_headers=["*"])
for r in (auth.router, copilot.router, system.router):
    app.include_router(r, prefix="/api/v1")


@app.get("/health")
def health():
    with engine.connect() as c:
        return {"status": "ok", "db": c.execute(text("select version()")).scalar()}


# Serve the built frontend (Docker image) with SPA fallback; API routes above take priority.
_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.is_dir():
    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = (_dist / path).resolve()
        return FileResponse(f if path and f.is_file() and _dist in f.parents else _dist / "index.html")
