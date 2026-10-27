from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

_url = settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
# pooled Neon URL; pre_ping survives scale-to-zero; sqlite needs check_same_thread off for FastAPI threads
engine = create_engine(
    _url, pool_pre_ping=True, connect_args={"check_same_thread": False} if _url.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as db:
        yield db
