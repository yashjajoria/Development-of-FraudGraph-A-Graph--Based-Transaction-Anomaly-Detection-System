from sqlalchemy import create_engine

from app.core.config import settings

_url = settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(_url, pool_pre_ping=True)  # pooled Neon URL; pre_ping survives scale-to-zero
