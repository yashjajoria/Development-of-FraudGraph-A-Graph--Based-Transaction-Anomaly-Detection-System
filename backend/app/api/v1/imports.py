"""Admin CSV imports. All-or-nothing: if any row is invalid nothing is stored and errors list row numbers."""
import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.api.v1.system import NewAccount, create_account_row
from app.core.db import get_db
from app.core.security import User, require_roles
from app.models.account import ManagedTransaction
from app.services.copilot.data import get_store

router = APIRouter(prefix="/import", tags=["import"])
MAX_ACCOUNT_ROWS, MAX_TXN_ROWS = 500, 5000


class CsvIn(BaseModel):
    csv: str = Field(max_length=2_000_000)


def _rows(text: str, required: set[str], limit: int) -> list[dict]:
    r = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    cols = {(c or "").strip().lower() for c in (r.fieldnames or [])}
    if not required <= cols:
        raise HTTPException(422, {"errors": [f"Missing column(s): {', '.join(sorted(required - cols))}"]})
    rows = [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in r]
    if not rows:
        raise HTTPException(422, {"errors": ["File has no data rows"]})
    if len(rows) > limit:
        raise HTTPException(422, {"errors": [f"Too many rows (max {limit})"]})
    return rows


def _fail(errors: list[str]):
    raise HTTPException(422, {"errors": errors[:20] + ([f"…and {len(errors) - 20} more"] if len(errors) > 20 else [])})


@router.post("/accounts")
def import_accounts(body: CsvIn, user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    rows, parsed, errors = _rows(body.csv, {"type", "name"}, MAX_ACCOUNT_ROWS), [], []
    for i, r in enumerate(rows, start=2):  # row 1 is the header
        try:
            parsed.append(NewAccount(type=r["type"].lower(), name=r["name"], phone=r.get("phone") or None,
                                     card=r.get("card") or None, device_id=r.get("device_id") or None))
        except ValidationError as e:
            errors.append(f"Row {i}: {e.errors()[0]['loc'][0]} is invalid")
    if errors:
        _fail(errors)
    ids = [create_account_row(p, user.username, db, commit=False) for p in parsed]
    db.commit()
    return {"imported": len(ids), "account_ids": ids[:50]}


@router.post("/transactions")
def import_transactions(body: CsvIn, user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    s = get_store()
    rows, parsed, errors = _rows(body.csv, {"sender_id", "receiver_id", "amount", "timestamp"}, MAX_TXN_ROWS), [], []
    for i, r in enumerate(rows, start=2):
        try:
            snd, rcv = r["sender_id"].upper(), r["receiver_id"].upper()
            if snd not in s.accounts or rcv not in s.accounts:
                raise ValueError("unknown account")
            if snd == rcv:
                raise ValueError("sender equals receiver")
            amt = float(r["amount"])
            if not 0 < amt <= 1e9:
                raise ValueError("amount out of range")
            ts = datetime.fromisoformat(r["timestamp"])
            ts = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
            if ts > datetime.now(timezone.utc):
                raise ValueError("timestamp in the future")
            parsed.append({"sender": snd, "receiver": rcv, "amount": round(amt, 2), "ts": ts, "note": r.get("note", "")[:200]})
        except (ValueError, KeyError) as e:
            errors.append(f"Row {i}: {e}")
    if errors:
        _fail(errors)
    before = {a for a, x in s.risk.items() if x["score"] >= 25}
    for p in parsed:
        db.add(ManagedTransaction(sender=p["sender"], receiver=p["receiver"], amount=p["amount"], ts=p["ts"],
                                  note=p["note"], created_by=user.username))
    db.commit()
    s.add_transactions(parsed)
    after = {a for a, x in s.risk.items() if x["score"] >= 25}
    return {"imported": len(parsed), "newly_flagged": sorted(after - before)[:50], "total_alerts": len(s.alerts)}
