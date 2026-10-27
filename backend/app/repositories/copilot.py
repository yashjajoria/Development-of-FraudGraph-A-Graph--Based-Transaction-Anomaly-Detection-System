from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.copilot import CopilotFeedback, CopilotMessage, CopilotPendingAction, CopilotSession


class SessionRepo:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, title: str = "New chat") -> CopilotSession:
        s = CopilotSession(user_id=user_id, title=title)
        self.db.add(s)
        self.db.commit()
        return s

    def get(self, session_id: str, user_id: str) -> CopilotSession | None:
        """Scoped to the owner: users can never read each other's sessions."""
        s = self.db.get(CopilotSession, session_id)
        return s if s and s.user_id == user_id else None

    def list(self, user_id: str) -> list[CopilotSession]:
        q = select(CopilotSession).where(CopilotSession.user_id == user_id).order_by(CopilotSession.updated_at.desc())
        return list(self.db.scalars(q))

    def touch(self, s: CopilotSession, title: str | None = None) -> None:
        s.updated_at = datetime.now(timezone.utc)
        if title:
            s.title = title
        self.db.commit()

    def delete(self, s: CopilotSession) -> None:
        self.db.execute(delete(CopilotPendingAction).where(CopilotPendingAction.session_id == s.id))
        ids = select(CopilotMessage.id).where(CopilotMessage.session_id == s.id)
        self.db.execute(delete(CopilotFeedback).where(CopilotFeedback.message_id.in_(ids)))
        self.db.execute(delete(CopilotMessage).where(CopilotMessage.session_id == s.id))
        self.db.delete(s)
        self.db.commit()


class MessageRepo:
    def __init__(self, db: Session):
        self.db = db

    def add(self, session_id: str, role: str, content: str, tool_calls=None, blocks=None) -> CopilotMessage:
        m = CopilotMessage(session_id=session_id, role=role, content=content, tool_calls=tool_calls, blocks=blocks)
        self.db.add(m)
        self.db.commit()
        return m

    def list(self, session_id: str) -> list[CopilotMessage]:
        q = select(CopilotMessage).where(CopilotMessage.session_id == session_id).order_by(CopilotMessage.created_at)
        return list(self.db.scalars(q))

    def get(self, message_id: str) -> CopilotMessage | None:
        return self.db.get(CopilotMessage, message_id)


class FeedbackRepo:
    def __init__(self, db: Session):
        self.db = db

    def upsert(self, message_id: str, rating: str, comment: str | None) -> CopilotFeedback:
        f = self.db.get(CopilotFeedback, message_id) or CopilotFeedback(message_id=message_id, rating=rating)
        f.rating, f.comment = rating, comment
        self.db.add(f)
        self.db.commit()
        return f


class PendingActionRepo:
    def __init__(self, db: Session):
        self.db = db

    def create(self, session_id: str, tool: str, args: dict) -> CopilotPendingAction:
        a = CopilotPendingAction(session_id=session_id, tool=tool, args=args)
        self.db.add(a)
        self.db.commit()
        return a

    def get(self, action_id: str) -> CopilotPendingAction | None:
        return self.db.get(CopilotPendingAction, action_id)

    def set_status(self, a: CopilotPendingAction, status: str) -> None:
        a.status = status
        self.db.commit()
