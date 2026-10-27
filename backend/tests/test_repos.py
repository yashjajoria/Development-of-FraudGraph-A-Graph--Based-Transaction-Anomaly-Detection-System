import pytest

from app.core.db import Base, SessionLocal, engine
from app.models import copilot  # noqa: F401
from app.repositories.copilot import FeedbackRepo, MessageRepo, PendingActionRepo, SessionRepo


@pytest.fixture
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        yield s


def test_session_lifecycle_and_ownership(db):
    r = SessionRepo(db)
    s = r.create("alice", "Why risky?")
    assert r.get(s.id, "alice") and r.get(s.id, "bob") is None  # owner-scoped
    m = MessageRepo(db).add(s.id, "user", "hi")
    MessageRepo(db).add(s.id, "assistant", "hello", tool_calls=[{"tool": "x"}], blocks={"referenced_nodes": ["ACC_1"]})
    FeedbackRepo(db).upsert(m.id, "up", None)
    FeedbackRepo(db).upsert(m.id, "down", "wrong")  # upsert, not duplicate
    a = PendingActionRepo(db).create(s.id, "update_alert_status", {"alert_id": "ALR_001"})
    assert [x.role for x in MessageRepo(db).list(s.id)] == ["user", "assistant"]
    assert PendingActionRepo(db).get(a.id).status == "pending"
    r.delete(s)
    assert r.list("alice") == [] and MessageRepo(db).list(s.id) == []
