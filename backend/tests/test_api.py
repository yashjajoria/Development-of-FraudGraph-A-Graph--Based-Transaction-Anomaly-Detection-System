import json

import pytest
from fastapi.testclient import TestClient

from app.api.v1.copilot import provider_dep
from app.core import security
from app.core.db import Base, engine
from app.main import app
from app.services.copilot.data import get_store
from app.services.llm import ToolCall
from app.services.llm.mock_provider import MockProvider

PW = security.settings.demo_password


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    security._hits.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def auth(c, user="analyst"):
    t = c.post("/api/v1/auth/login", json={"username": user, "password": PW}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


def script(*steps):
    app.dependency_overrides[provider_dep] = lambda: MockProvider(list(steps))


def events(resp):
    out = []
    for block in resp.text.strip().split("\n\n"):
        ev, data = block.split("\n", 1)
        out.append((ev[7:], json.loads(data[6:])))
    return out


def test_auth_required_and_bad_login(client):
    assert client.post("/api/v1/copilot/chat", json={"message": "hi"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "analyst", "password": "x"}).status_code == 401
    assert client.get("/api/v1/copilot/sessions", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_chat_stream_persists_and_reloads(client):
    h = auth(client)
    script([ToolCall("c", "get_account_details", {"account_id": "ACC_9001"})], "ACC_9001 is High risk")
    r = client.post("/api/v1/copilot/chat", headers=h, json={"message": "Why is ACC_9001 risky?"})
    ev = events(r)
    names = [n for n, _ in ev]
    assert names[0] == "session" and names[1] == "tool_start" and names[-1] == "done" and "blocks" in names
    sid = ev[0][1]["session_id"]
    s = client.get(f"/api/v1/copilot/sessions/{sid}", headers=h).json()
    assert s["title"].startswith("Why is ACC_9001") and [m["role"] for m in s["messages"]] == ["user", "assistant"]
    assert s["messages"][1]["tool_calls"][0]["tool"] == "get_account_details"
    # follow-up in same session keeps history
    script("Follow-up answer")
    r2 = client.post("/api/v1/copilot/chat", headers=h, json={"message": "and more?", "session_id": sid})
    assert events(r2)[-1][0] == "done" and len(client.get(f"/api/v1/copilot/sessions/{sid}", headers=h).json()["messages"]) == 4


def test_sessions_are_private(client):
    script("hi")
    sid = events(client.post("/api/v1/copilot/chat", headers=auth(client, "analyst"), json={"message": "x"}))[0][1]["session_id"]
    other = auth(client, "admin")
    assert client.get(f"/api/v1/copilot/sessions/{sid}", headers=other).status_code == 404
    assert client.delete(f"/api/v1/copilot/sessions/{sid}", headers=other).status_code == 404
    assert client.delete(f"/api/v1/copilot/sessions/{sid}", headers=auth(client)).status_code == 204


def test_input_limit_and_rate_limit(client):
    h = auth(client)
    assert client.post("/api/v1/copilot/chat", headers=h, json={"message": "x" * 2001}).status_code == 422
    assert client.post("/api/v1/copilot/chat", headers=h, json={"message": "hi", "context": {"account_id": "bad"}}).status_code == 422
    for _ in range(20):
        script("ok")
        assert client.post("/api/v1/copilot/chat", headers=h, json={"message": "hi"}).status_code == 200
    assert client.post("/api/v1/copilot/chat", headers=h, json={"message": "hi"}).status_code == 429


def test_confirmation_flow_and_roles(client):
    s = get_store()
    aid = next(a["id"] for a in s.alerts.values() if a["status"] == "open")
    h = auth(client)
    script([ToolCall("c", "update_alert_status", {"alert_id": aid, "status": "false_positive"})], "Please confirm")
    ev = events(client.post("/api/v1/copilot/chat", headers=h, json={"message": f"close {aid}"}))
    conf = next(d for n, d in ev if n == "confirmation_required")
    assert s.alerts[aid]["status"] == "open"  # not executed
    assert client.post(f"/api/v1/copilot/confirm/{conf['action_id']}", headers=auth(client, "viewer"), json={"approve": True}).status_code == 403
    sid = ev[0][1]["session_id"]
    card = client.get(f"/api/v1/copilot/sessions/{sid}", headers=h).json()["messages"][1]["blocks"]["confirmations"][0]
    assert card["status"] == "pending"
    r = client.post(f"/api/v1/copilot/confirm/{conf['action_id']}", headers=h, json={"approve": True}).json()
    assert r["status"] == "approved" and s.alerts[aid]["status"] == "false_positive"
    assert client.post(f"/api/v1/copilot/confirm/{conf['action_id']}", headers=h, json={"approve": True}).status_code == 409
    s.alerts[aid]["status"] = "open"


def test_reject_does_not_execute(client):
    s = get_store()
    aid = next(a["id"] for a in s.alerts.values() if a["status"] == "open")
    h = auth(client)
    script([ToolCall("c", "update_alert_status", {"alert_id": aid, "status": "closed"})], "confirm?")
    conf = next(d for n, d in events(client.post("/api/v1/copilot/chat", headers=h, json={"message": "x"})) if n == "confirmation_required")
    assert client.post(f"/api/v1/copilot/confirm/{conf['action_id']}", headers=h, json={"approve": False}).json()["status"] == "rejected"
    assert s.alerts[aid]["status"] == "open"


def test_feedback_suggestions_and_data_endpoints(client):
    h = auth(client)
    script("hello")
    ev = events(client.post("/api/v1/copilot/chat", headers=h, json={"message": "hi"}))
    mid = ev[-1][1]["message_id"]
    assert client.post("/api/v1/copilot/feedback", headers=h, json={"message_id": mid, "rating": "up"}).json() == {"ok": True}
    assert client.post("/api/v1/copilot/feedback", headers=h, json={"message_id": mid, "rating": "meh"}).status_code == 422
    assert client.post("/api/v1/copilot/feedback", headers=auth(client, "admin"), json={"message_id": mid, "rating": "up"}).status_code == 404
    sg = client.get("/api/v1/copilot/suggestions?page=account&account_id=ACC_1023", headers=h).json()["suggestions"]
    assert len(sg) == 4 and "ACC_1023" in sg[0]
    assert len(client.get("/api/v1/copilot/suggestions?page=dashboard", headers=h).json()["suggestions"]) == 4
    assert client.get("/api/v1/accounts/ACC_9001", headers=h).json()["risk_level"] == "High"
    assert client.get("/api/v1/accounts/ACC_0", headers=h).status_code == 404
    assert client.get("/api/v1/accounts/search?q=90", headers=h).json()[0]["id"].startswith("ACC_90")
    g = client.get("/api/v1/graph", headers=h).json()
    assert any(n["id"] == "ACC_9001" for n in g["nodes"]) and g["edges"]
    assert client.get("/api/v1/dashboard", headers=h).json()["stats"]["flagged_accounts"] == 6


def test_llm_failure_is_graceful_error_event(client):
    from app.services.llm import ProviderUnavailableError
    import app.services.llm.base as b

    class Down(MockProvider):
        async def _stream(self, m, t):
            raise ProviderUnavailableError("down")
            yield
    app.dependency_overrides[provider_dep] = lambda: Down([])
    b.RETRIES, old = 0, b.RETRIES
    try:
        r = client.post("/api/v1/copilot/chat", headers=auth(client), json={"message": "hi"})
    finally:
        b.RETRIES = old
    ev = events(r)
    assert r.status_code == 200 and ev[-1][0] == "error" and ev[-1][1]["retryable"] is True


def test_admin_creates_account_visible_everywhere(client):
    body = {"type": "user", "name": "New Customer", "phone": "+919876543210", "card": "4111111111111111"}
    for role in ("analyst", "viewer"):
        assert client.post("/api/v1/accounts", headers=auth(client, role), json=body).status_code == 403
    h = auth(client, "admin")
    assert client.post("/api/v1/accounts", headers=h, json={**body, "card": "123"}).status_code == 422
    r = client.post("/api/v1/accounts", headers=h, json=body)
    assert r.status_code == 201
    a = r.json()
    assert int(a["id"][4:]) >= 10000 and a["risk_level"] == "Low" and a["card"].endswith("1111") and "4111111111111111" not in str(a)
    assert client.get(f"/api/v1/accounts/{a['id']}", headers=h).json()["name"] == "New Customer"
    assert client.get(f"/api/v1/accounts/search?q={a['id'][4:]}", headers=h).json()[0]["id"] == a["id"]
    from app.services.copilot.tools import registry
    assert registry.run("get_account_details", {"account_id": a["id"]})["data"]["type"] == "user"  # AI tools see it
    from app.api.v1 import system
    from app.core.db import SessionLocal
    from app.services.copilot.data import get_store
    del get_store().accounts[a["id"]]  # simulate restart: reload from DB
    with SessionLocal() as db:
        assert system.load_managed_accounts(db) >= 1
    assert a["id"] in get_store().accounts


def test_csv_import_detects_new_fraud_and_validates(client):
    from app.services.copilot.data import get_store
    h = auth(client, "admin")
    ac = "type,name\nuser,Ring A\nuser,Ring B\nuser,Ring C\n"
    assert client.post("/api/v1/import/accounts", headers=auth(client, "analyst"), json={"csv": ac}).status_code == 403
    assert client.post("/api/v1/import/accounts", headers=h, json={"csv": "type,name\nplanet,X\n"}).status_code == 422
    ids = client.post("/api/v1/import/accounts", headers=h, json={"csv": ac}).json()["account_ids"]
    assert len(ids) == 3 and get_store().risk[ids[0]]["score"] == 0  # no transactions yet -> nothing to detect
    a, b, c = ids
    bad = f"sender_id,receiver_id,amount,timestamp\n{a},{b},5000,2026-10-01T10:00:00\n{a},ACC_NOPE,5,2026-10-01\n{b},{b},5,2026-10-01\n"
    r = client.post("/api/v1/import/transactions", headers=h, json={"csv": bad})
    assert r.status_code == 422 and "Row 3" in str(r.json()) and "Row 4" in str(r.json())
    n_tx = len(get_store().txns)
    good = "sender_id,receiver_id,amount,timestamp,note\n" + "".join(
        f"{x},{y},{amt},2026-10-01T10:0{i}:00,loop\n" for i, (x, y, amt) in enumerate([(a, b, 9000), (b, c, 8900), (c, a, 8800)]))
    r = client.post("/api/v1/import/transactions", headers=h, json={"csv": good}).json()
    assert r["imported"] == 3 and set(ids) <= set(r["newly_flagged"])
    assert len(get_store().txns) == n_tx + 3
    d = client.get(f"/api/v1/accounts/{a}", headers=h).json()
    assert d["risk_score"] >= 45 and d["risk_level"] == "Medium" and d["explanation"]["contributions"][0]["rule"] == "CYCLE"
    assert any(x["account_id"] == a for x in get_store().alerts.values())
