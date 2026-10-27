from fastapi import FastAPI
from sqlalchemy import text

from app.core.db import engine

app = FastAPI(title="FraudGraph AI")


@app.get("/health")
def health():
    with engine.connect() as c:
        return {"status": "ok", "db": c.execute(text("select version()")).scalar()}
