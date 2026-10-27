import asyncio
import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal, get_db
from app.core.security import User, check_rate_limit, current_user, require_roles
from app.repositories.copilot import FeedbackRepo, MessageRepo, PendingActionRepo, SessionRepo
from app.services.copilot.agent import CopilotAgent
from app.services.copilot.prompts import SUGGESTIONS
from app.services.copilot.tools import registry
from app.services.llm import get_provider

router = APIRouter(prefix="/copilot", tags=["copilot"])


def provider_dep():
    return get_provider()  # tests override this with a MockProvider


class Context(BaseModel):
    page: str = Field("unknown", max_length=20)
    account_id: str | None = Field(None, pattern=r"^ACC_\d+$")
    selected_nodes: list[str] = Field(default_factory=list, max_length=20)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=settings.max_input_chars)
    session_id: str | None = None
    context: Context | None = None


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post("/chat")
async def chat(body: ChatIn, user: User = Depends(current_user), provider=Depends(provider_dep),
               db: Session = Depends(get_db)):
    check_rate_limit(user.username)
    sessions, msgs = SessionRepo(db), MessageRepo(db)
    if body.session_id:
        s = sessions.get(body.session_id, user.username)
        if not s:
            raise HTTPException(404, "Session not found")
    else:
        s = sessions.create(user.username, body.message.strip()[:50])  # title from first question
    sid = s.id
    history = [{"role": m.role, "content": m.content} for m in msgs.list(sid)]
    msgs.add(sid, "user", body.message)
    sessions.touch(s)
    ctx = body.context.model_dump() if body.context else None

    async def stream():
        yield sse("session", {"session_id": sid})
        text, blocks, final, failed = "", None, None, False
        with SessionLocal() as sdb:  # own DB session: the request-scoped one may close before streaming ends
            def create_action(tool, args):
                return PendingActionRepo(sdb).create(sid, tool, args).id
            confirmations = []
            try:
                async for ev in CopilotAgent(provider).run(history, body.message, ctx, user.username, create_action):
                    name, data = ev["event"], ev["data"]
                    if name == "_final":
                        final = data
                        continue
                    if name == "token":
                        text += data["text"]
                    elif name == "blocks":
                        blocks = data
                    elif name == "confirmation_required":
                        confirmations.append(data)
                    elif name == "error":
                        failed = True
                    yield sse(name, data)
            finally:  # also runs when the client hits Stop (generator cancelled): keep the partial answer
                if not failed and (final or text):
                    b = dict(blocks or {})
                    if confirmations:
                        b["confirmations"] = confirmations
                    m = MessageRepo(sdb).add(sid, "assistant", (final or {}).get("content", text),
                                             (final or {}).get("tool_calls"), b or None)
                    SessionRepo(sdb).touch(sessions.get(sid, user.username) or s)
                    mid = m.id
                else:
                    mid = None
        if mid:
            yield sse("done", {"message_id": mid})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class ConfirmIn(BaseModel):
    approve: bool


@router.post("/confirm/{action_id}")
async def confirm(action_id: str, body: ConfirmIn, user: User = Depends(require_roles("admin", "analyst")),
                  db: Session = Depends(get_db)):
    repo = PendingActionRepo(db)
    a = repo.get(action_id)
    if not a or not SessionRepo(db).get(a.session_id, user.username):
        raise HTTPException(404, "Action not found")
    if a.status != "pending":
        raise HTTPException(409, f"Action already {a.status}")
    if not body.approve:
        repo.set_status(a, "rejected")
        return {"status": "rejected", "result": None}
    result = await asyncio.to_thread(registry.run, a.tool, a.args, True)  # the only place actions execute
    repo.set_status(a, "approved")
    return {"status": "approved", "result": result}


@router.get("/sessions")
def list_sessions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": s.id, "title": s.title, "created_at": s.created_at, "updated_at": s.updated_at}
            for s in SessionRepo(db).list(user.username)]


@router.get("/sessions/{session_id}")
def get_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = SessionRepo(db).get(session_id, user.username)
    if not s:
        raise HTTPException(404, "Session not found")
    actions = PendingActionRepo(db)
    out = []
    for m in MessageRepo(db).list(session_id):
        blocks = dict(m.blocks or {})
        for c in blocks.get("confirmations", []):  # attach live status so a reload shows the right card state
            a = actions.get(c["action_id"]) if c.get("action_id") else None
            c["status"] = a.status if a else "unknown"
        out.append({"id": m.id, "role": m.role, "content": m.content, "tool_calls": m.tool_calls,
                    "blocks": blocks or None, "created_at": m.created_at})
    return {"id": s.id, "title": s.title, "messages": out}


class RenameIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)


@router.patch("/sessions/{session_id}")
def rename_session(session_id: str, body: RenameIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = SessionRepo(db).get(session_id, user.username)
    if not s:
        raise HTTPException(404, "Session not found")
    SessionRepo(db).touch(s, body.title)
    return {"id": s.id, "title": s.title}


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = SessionRepo(db).get(session_id, user.username)
    if not s:
        raise HTTPException(404, "Session not found")
    SessionRepo(db).delete(s)


class FeedbackIn(BaseModel):
    message_id: str
    rating: str = Field(pattern="^(up|down)$")
    comment: str | None = Field(None, max_length=1000)


@router.post("/feedback")
def feedback(body: FeedbackIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = MessageRepo(db).get(body.message_id)
    if not m or not SessionRepo(db).get(m.session_id, user.username):
        raise HTTPException(404, "Message not found")
    FeedbackRepo(db).upsert(body.message_id, body.rating, body.comment)
    return {"ok": True}


@router.get("/suggestions")
def suggestions(page: str = Query("default", max_length=20), account_id: str | None = Query(None, pattern=r"^ACC_\d+$"),
                user: User = Depends(current_user)):
    key = page if page in SUGGESTIONS else "default"
    if key == "account" and not account_id:
        key = "default"
    return {"suggestions": [q.format(a=account_id) for q in SUGGESTIONS[key]]}
