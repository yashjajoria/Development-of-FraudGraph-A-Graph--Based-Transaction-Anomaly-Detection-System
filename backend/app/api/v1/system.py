"""Read endpoints the UI shell needs (dashboard, graph explorer, account page, @mention search)."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import User, current_user, require_roles
from app.models.account import ManagedAccount
from app.services.copilot.data import get_store
from app.services.copilot.tools import registry
from app.services.copilot.tools.read import mask

router = APIRouter(tags=["system"])


@router.get("/dashboard")
def dashboard(_: User = Depends(current_user)):
    return {"stats": registry.run("get_dashboard_stats", {})["data"],
            "top_risky": registry.run("get_top_risky_accounts", {"limit": 8})["data"]}


@router.get("/accounts/search")
def search_accounts(q: str = Query("", max_length=20), _: User = Depends(current_user)):
    s = get_store()
    q = q.upper().replace("ACC_", "")
    ids = [a for a in s.accounts if a[4:].startswith(q)][:8]
    return [{"id": a, "type": s.accounts[a]["type"], "risk_score": s.risk[a]["score"], "risk_level": s.risk[a]["level"]} for a in ids]


@router.get("/accounts/{account_id}")
def account(account_id: str, _: User = Depends(current_user)):
    r = registry.run("get_account_details", {"account_id": account_id})
    if r["data"] is None:
        raise HTTPException(404, r["summary"])
    nb = registry.run("get_neighbors", {"account_id": account_id, "depth": 1})["data"][:5]
    return {**r["data"], "neighbors": nb,
            "explanation": registry.run("get_risk_explanation", {"account_id": account_id})["data"]}


@router.get("/graph")
def graph(ids: str | None = Query(None, max_length=600), _: User = Depends(current_user)):
    """Default: flagged accounts + 1-hop neighbours. With ids=ACC_1,ACC_2: exactly those nodes."""
    s = get_store()
    if ids:
        keep = {i for i in ids.split(",") if i in s.accounts}
    else:
        flagged = {a for a, r in s.risk.items() if r["score"] >= 25}
        keep = set(flagged)
        for a in flagged:
            keep |= set(s.D.predecessors(a)) | set(s.D.successors(a))
    return {
        "nodes": [{"id": a, "type": s.accounts[a]["type"], "risk_score": s.risk[a]["score"],
                   "risk_level": s.risk[a]["level"], "community_id": s.accounts[a]["community_id"]} for a in sorted(keep)],
        "edges": [{"source": u, "target": v, "amount": d["amount"], "count": d["count"]}
                  for u, v, d in s.D.edges(data=True) if u in keep and v in keep],
    }


class NewAccount(BaseModel):
    type: Literal["user", "merchant"]
    name: str = Field(min_length=1, max_length=60)
    phone: str | None = Field(None, pattern=r"^\+?\d{10,13}$")
    card: str | None = Field(None, pattern=r"^\d{16}$")
    device_id: str | None = Field(None, pattern=r"^[A-Za-z0-9_-]{1,30}$")


@router.post("/accounts", status_code=201)
def create_account(body: NewAccount, user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    """Admin only. Saves to Neon (masked PII) and adds the account to the live graph store."""
    s = get_store()
    n = max([int(i[4:]) for i in s.accounts if int(i[4:]) >= 10000] or [9999]) + 1
    aid = f"ACC_{n}"
    row = ManagedAccount(id=aid, type=body.type, name=body.name.strip(), phone=mask(body.phone) if body.phone else "",
                         card=mask(body.card) if body.card else "", device_id=body.device_id or f"DEV_{n}",
                         created_by=user.username)
    db.add(row)
    db.commit()
    s.add_account(_row_dict(row))
    return account(aid, user)


def _row_dict(r: ManagedAccount) -> dict:
    return {"id": r.id, "type": r.type, "name": r.name, "phone": r.phone, "card": r.card, "device_id": r.device_id}


def load_managed_accounts(db: Session) -> int:
    """Called at startup: re-add admin-created accounts to the in-memory graph."""
    rows = db.query(ManagedAccount).all()
    s = get_store()
    for r in rows:
        if r.id not in s.accounts:
            s.add_account(_row_dict(r))
    return len(rows)
