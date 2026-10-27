"""Read-only tools (1-12). All data comes from the GraphStore; phone/card are masked."""
from datetime import datetime, timezone

import networkx as nx

from app.services.copilot.data import get_store
from app.services.copilot.tools.registry import ToolError, inr, obj, out, registry

ACC = {"type": "string", "pattern": r"^ACC_\d+$", "description": "Account ID like ACC_1023"}
LEVEL = {"type": "string", "enum": ["Low", "Medium", "High", "Critical"]}
LIMIT = {"type": "integer", "minimum": 1, "maximum": 20}


def acct(account_id: str) -> dict:
    a = get_store().accounts.get(account_id)
    if not a:
        raise ToolError(f"Account {account_id} not found")
    return a


def mask(v: str) -> str:
    return "*" * (len(v) - 4) + v[-4:]


def _risk_row(a: str) -> dict:
    s = get_store()
    return {"account_id": a, "type": s.accounts[a]["type"], "risk_score": s.risk[a]["score"],
            "risk_level": s.risk[a]["level"], "rules": [r["rule"] for r in s.risk[a]["rules"]]}


def _ts(v: str | None) -> datetime | None:
    if not v:
        return None
    try:
        d = datetime.fromisoformat(v)
    except ValueError:
        raise ToolError(f"Invalid date '{v}', use ISO format like 2026-10-20")
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


@registry.register("Overall dashboard numbers: totals, fraud rate, amount at risk, active alerts.", obj({}))
def get_dashboard_stats() -> dict:
    s = get_store()
    flagged = {a for a, r in s.risk.items() if r["score"] >= 50}
    hit = [t for t in s.txns if t["sender"] in flagged or t["receiver"] in flagged]
    by_level = {l: sum(1 for r in s.risk.values() if r["level"] == l) for l in ("Low", "Medium", "High", "Critical")}
    d = {"total_accounts": len(s.accounts), "total_transactions": len(s.txns), "flagged_accounts": len(flagged),
         "accounts_by_risk_level": by_level, "fraud_rate_pct": round(100 * len(hit) / len(s.txns), 2),
         "amount_at_risk": round(sum(t["amount"] for t in hit), 2),
         "active_alerts": sum(1 for a in s.alerts.values() if a["status"] in ("open", "investigating"))}
    return {"data": d, "referenced_nodes": [], "summary": (
        f"{d['flagged_accounts']} flagged accounts, {d['fraud_rate_pct']}% of transactions touch them, "
        f"{inr(d['amount_at_risk'])} at risk, {d['active_alerts']} active alerts")}


@registry.register("Profile, risk score/level, behavioural features and community of one account.",
                   obj({"account_id": ACC}, ("account_id",)))
def get_account_details(account_id: str) -> dict:
    s, a = get_store(), acct(account_id)
    d = {"id": a["id"], "type": a["type"], "name": a["name"], "phone": mask(a["phone"]), "card": mask(a["card"]),
         "device_id": a["device_id"], "community_id": a["community_id"], "risk_score": s.risk[account_id]["score"],
         "risk_level": s.risk[account_id]["level"], "features": s.features[account_id],
         "alerts": [x["id"] for x in s.alerts.values() if x["account_id"] == account_id]}
    return {"data": d, "referenced_nodes": [account_id],
            "summary": f"{account_id}: risk {d['risk_score']} ({d['risk_level']}), community {d['community_id']}"}


@registry.register("Accounts connected to an account within 1-2 hops, with flow amounts. Direction in=received from, "
                   "out=sent to.", obj({"account_id": ACC, "depth": {"type": "integer", "enum": [1, 2]},
                                        "direction": {"type": "string", "enum": ["in", "out", "both"]},
                                        "min_amount": {"type": "number", "minimum": 0}}, ("account_id",)))
def get_neighbors(account_id: str, depth: int = 1, direction: str = "both", min_amount: float | None = None) -> dict:
    s = get_store()
    acct(account_id)
    seen, flows, frontier = {account_id: 0}, {}, [account_id]
    for hop in range(1, depth + 1):
        nxt = []
        for n in frontier:
            edges = []
            if direction in ("out", "both"):
                edges += [(v, d) for _, v, d in s.G.out_edges(n, data=True)]
            if direction in ("in", "both"):
                edges += [(u, d) for u, _, d in s.G.in_edges(n, data=True)]
            for m, d in edges:
                if m == account_id or (m in seen and seen[m] < hop) or (min_amount and d["amount"] < min_amount):
                    continue
                f = flows.setdefault(m, {"account_id": m, "hops": hop, "txn_count": 0, "total_amount": 0.0,
                                         "risk_level": s.risk[m]["level"]})
                f["txn_count"] += 1
                f["total_amount"] = round(f["total_amount"] + d["amount"], 2)
                if m not in seen:
                    seen[m] = hop
                    nxt.append(m)
        frontier = nxt
    rows = sorted(flows.values(), key=lambda r: -r["total_amount"])
    return out(rows, [account_id] + [r["account_id"] for r in rows],
               f"{len(rows)} accounts within {depth} hop(s) of {account_id} ({direction})")


@registry.register("Search transactions by sender, receiver, amount range and ISO dates. Newest first.",
                   obj({"sender_id": ACC, "receiver_id": ACC, "min_amount": {"type": "number", "minimum": 0},
                        "max_amount": {"type": "number", "minimum": 0}, "start_date": {"type": "string"},
                        "end_date": {"type": "string"}, "limit": LIMIT}))
def search_transactions(sender_id=None, receiver_id=None, min_amount=None, max_amount=None, start_date=None,
                        end_date=None, limit=20) -> dict:
    for i in (sender_id, receiver_id):
        if i:
            acct(i)
    lo, hi = _ts(start_date), _ts(end_date)
    rows = [t for t in get_store().txns
            if (not sender_id or t["sender"] == sender_id) and (not receiver_id or t["receiver"] == receiver_id)
            and (min_amount is None or t["amount"] >= min_amount) and (max_amount is None or t["amount"] <= max_amount)
            and (not lo or t["ts"] >= lo) and (not hi or t["ts"] <= hi)]
    rows.sort(key=lambda t: t["ts"], reverse=True)
    total = sum(t["amount"] for t in rows)
    res = [{"id": t["id"], "sender": t["sender"], "receiver": t["receiver"], "amount": t["amount"],
            "timestamp": t["ts"].isoformat(), "note": t["note"][:80]} for t in rows[:limit]]  # note = untrusted text
    nodes = [x for r in res for x in (r["sender"], r["receiver"])]
    o = out(res, nodes, f"{len(rows)} matching transactions totalling {inr(total)}")
    if len(rows) > limit:
        o["summary"] += f" (showing {limit})"
    return o


@registry.register("Highest-risk accounts, optionally filtered by risk level or account type.",
                   obj({"limit": LIMIT, "risk_level": LEVEL, "account_type": {"type": "string", "enum": ["user", "merchant"]}}))
def get_top_risky_accounts(limit: int = 10, risk_level: str | None = None, account_type: str | None = None) -> dict:
    s = get_store()
    ids = [a for a in s.accounts if (not risk_level or s.risk[a]["level"] == risk_level)
           and (not account_type or s.accounts[a]["type"] == account_type)]
    ids.sort(key=lambda a: -s.risk[a]["score"])
    rows = [_risk_row(a) for a in ids[:limit]]
    return out(rows, ids[:limit], f"Top {len(rows)} of {len(ids)} matching accounts by risk score")


@registry.register("List alerts, filter by status, risk level or pattern type (cycle, fan_in, fan_out, velocity, "
                   "shared_device, high_value).",
                   obj({"status": {"type": "string", "enum": ["open", "investigating", "confirmed_fraud", "false_positive", "closed"]},
                        "risk_level": LEVEL, "pattern_type": {"type": "string"}, "limit": LIMIT}))
def get_alerts(status=None, risk_level=None, pattern_type=None, limit=20) -> dict:
    rows = [{**a, "created_at": a["created_at"].isoformat()} for a in get_store().alerts.values()
            if (not status or a["status"] == status) and (not risk_level or a["risk_level"] == risk_level)
            and (not pattern_type or a["pattern_type"] == pattern_type.lower())]
    rows.sort(key=lambda a: -a["risk_score"])
    rows = rows[:limit]
    return out(rows, [a["account_id"] for a in rows], f"{len(rows)} alerts")


@registry.register("Find circular money flows (laundering loops). Optionally only cycles through one account.",
                   obj({"account_id": ACC, "max_length": {"type": "integer", "minimum": 2, "maximum": 6},
                        "min_amount": {"type": "number", "minimum": 0}}))
def find_cycles(account_id: str | None = None, max_length: int = 5, min_amount: float | None = None) -> dict:
    D = get_store().D
    if account_id:
        acct(account_id)
    H = D.edge_subgraph([(u, v) for u, v, d in D.edges(data=True) if not min_amount or d["amount"] >= min_amount])
    rows = []
    for c in nx.simple_cycles(H, length_bound=max_length):
        if account_id and account_id not in c:
            continue
        i = c.index(min(c))
        c = c[i:] + c[:i]  # canonical start so output is stable
        amt = sum(D[c[k]][c[(k + 1) % len(c)]]["amount"] for k in range(len(c)))
        rows.append({"cycle": c + [c[0]], "length": len(c), "total_amount": round(amt, 2)})
    rows.sort(key=lambda r: -r["total_amount"])
    return out(rows, [n for r in rows[:20] for n in r["cycle"]], f"{len(rows)} cycle(s) found")


@registry.register("Shortest money-flow path between two accounts (up to max_hops), with amount per hop.",
                   obj({"source_id": ACC, "target_id": ACC, "max_hops": {"type": "integer", "minimum": 1, "maximum": 6}},
                       ("source_id", "target_id")))
def find_money_path(source_id: str, target_id: str, max_hops: int = 6) -> dict:  # ponytail: shortest only, not strongest
    D = get_store().D
    acct(source_id), acct(target_id)
    try:
        p = nx.shortest_path(D, source_id, target_id)
    except nx.NetworkXNoPath:
        p = None
    if not p or len(p) - 1 > max_hops:
        return {"data": [], "referenced_nodes": [], "summary": f"No money path from {source_id} to {target_id} within {max_hops} hops"}
    hops = [{"from": a, "to": b, "amount": round(D[a][b]["amount"], 2), "txn_count": D[a][b]["count"]} for a, b in zip(p, p[1:])]
    return out(hops, p, f"Path of {len(hops)} hop(s): {' -> '.join(p)}; bottleneck {inr(min(h['amount'] for h in hops))}")


@registry.register("A fraud community/ring: members, internal money moved, average risk. Give community_id or account_id.",
                   obj({"community_id": {"type": "string", "pattern": r"^COM_\d+$"}, "account_id": ACC}))
def get_community(community_id: str | None = None, account_id: str | None = None) -> dict:
    s = get_store()
    if account_id:
        community_id = acct(account_id)["community_id"]
        if not community_id:
            return {"data": None, "referenced_nodes": [account_id], "summary": f"{account_id} is not in any community"}
    if not community_id:
        raise ToolError("Provide community_id or account_id")
    c = s.communities.get(community_id)
    if not c:
        raise ToolError(f"Community {community_id} not found")
    m = set(c["members"])
    total = sum(t["amount"] for t in s.txns if t["sender"] in m and t["receiver"] in m)
    avg = round(sum(s.risk[a]["score"] for a in m) / len(m), 1)
    d = {"id": c["id"], "label": c["label"], "member_count": len(m), "internal_amount": round(total, 2),
         "avg_risk": avg, "members": [_risk_row(a) for a in sorted(m, key=lambda a: -s.risk[a]["score"])]}
    d["members"] = d["members"][:20]
    return {"data": d, "referenced_nodes": c["members"][:20], "summary": (
        f"{c['id']} ({c['label']}): {len(m)} members, {inr(total)} moved internally, avg risk {avg}")}


@registry.register("Why an account is risky: top contributing rules with points, and reasons.",
                   obj({"account_id": ACC}, ("account_id",)))
def get_risk_explanation(account_id: str) -> dict:
    acct(account_id)
    r = get_store().risk[account_id]
    contrib = sorted(r["rules"], key=lambda x: -x["points"])
    d = {"risk_score": r["score"], "risk_level": r["level"],
         "contributions": [{"rule": x["rule"], "name": x["name"], "points": x["points"], "reason": x["detail"]} for x in contrib]}
    return {"data": d, "referenced_nodes": [account_id],
            "summary": f"{account_id} scores {r['score']} ({r['level']}) from {len(contrib)} triggered rule(s)"}


@registry.register("Side-by-side features and risk for 2-5 accounts.",
                   obj({"account_ids": {"type": "array", "items": ACC, "minItems": 2, "maxItems": 5, "uniqueItems": True}},
                       ("account_ids",)))
def compare_accounts(account_ids: list) -> dict:
    s = get_store()
    for i in account_ids:
        acct(i)
    rows = [{**_risk_row(i), **s.features[i]} for i in account_ids]
    return out(rows, account_ids, f"Compared {len(rows)} accounts")


@registry.register("Detect fraud patterns on one account: fan-in, fan-out, velocity burst, shared device, cycle, high value.",
                   obj({"account_id": ACC}, ("account_id",)))
def detect_patterns(account_id: str) -> dict:
    acct(account_id)
    rules = get_store().risk[account_id]["rules"]
    return {"data": rules, "referenced_nodes": [account_id],
            "summary": f"{len(rules)} pattern(s) on {account_id}: " + (", ".join(r["rule"] for r in rules) or "none")}
