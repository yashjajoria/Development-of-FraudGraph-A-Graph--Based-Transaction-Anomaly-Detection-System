import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
