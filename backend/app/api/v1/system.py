"""Read endpoints the UI shell needs (dashboard, graph explorer, account page, @mention search)."""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import User, current_user
from app.services.copilot.data import get_store
from app.services.copilot.tools import registry

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
