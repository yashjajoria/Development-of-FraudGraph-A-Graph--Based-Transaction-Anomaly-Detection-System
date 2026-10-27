from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ManagedAccount(Base):
    """Accounts added by admins. Phone/card are stored already masked (last 4 digits only)."""
    __tablename__ = "managed_accounts"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    type: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(60))
    phone: Mapped[str] = mapped_column(String(20), default="")
    card: Mapped[str] = mapped_column(String(20), default="")
    device_id: Mapped[str] = mapped_column(String(30))
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ManagedTransaction(Base):
    __tablename__ = "managed_transactions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sender: Mapped[str] = mapped_column(String(20), index=True)
    receiver: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[float] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(String(200), default="")
    created_by: Mapped[str] = mapped_column(String(64))
