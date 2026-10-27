from datetime import datetime, timezone

from sqlalchemy import DateTime, String
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
