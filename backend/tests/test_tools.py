import json

import pytest

from app.services.copilot.data import get_store
from app.services.copilot.tools import ConfirmationRequired, registry

run = registry.run


def test_all_14_registered_and_two_need_confirmation():
    assert len(registry.tools) == 14
    assert {t.name for t in registry.tools.values() if t.requires_confirmation} == {"update_alert_status", "generate_case_report"}
    assert all(s.parameters["type"] == "object" for s in registry.specs())


def test_dashboard_and_details():
    assert run("get_dashboard_stats", {})["data"]["flagged_accounts"] == 6
    d = run("get_account_details", {"account_id": "ACC_9001"})["data"]
    assert d["community_id"] == "COM_1" and d["risk_level"] == "High" and d["card"].startswith("*" * 12)


def test_masking_no_raw_card_or_phone_anywhere():
    s, a = get_store(), get_store().accounts["ACC_9001"]
    blob = json.dumps(run("get_account_details", {"account_id": "ACC_9001"})) + json.dumps(
        run("generate_case_report", {"account_id": "ACC_9001"}, confirmed=True))
    assert a["card"] not in blob and a["phone"] not in blob


def test_neighbors_and_search():
    r = run("get_neighbors", {"account_id": "ACC_9010", "direction": "in"})
    assert len(r["data"]) == 15 and r["data"][0]["hops"] == 1
    t = run("search_transactions", {"receiver_id": "ACC_9010"})
    assert "15 matching" in t["summary"] and len(t["data"]) <= 20
    assert any("IGNORE ALL PREVIOUS" in x["note"] for x in t["data"])  # untrusted text present as data


def test_top_risky_alerts():
    top = run("get_top_risky_accounts", {"limit": 3})["data"]
    assert top[0]["account_id"] == "ACC_9020" and top[0]["risk_level"] == "Critical"
    assert run("get_alerts", {"risk_level": "Critical"})["data"][0]["account_id"] == "ACC_9020"


def test_cycles_and_path():
    c = run("find_cycles", {"account_id": "ACC_9001"})["data"]
    assert c[0]["cycle"][0] == "ACC_9001" and c[0]["length"] == 4
    assert run("find_cycles", {"min_amount": 10**9})["data"] == []
    p = run("find_money_path", {"source_id": "ACC_9001", "target_id": "ACC_9003"})
    assert p["data"][0]["from"] == "ACC_9001"
    assert "No money path" in run("find_money_path", {"source_id": "ACC_9003", "target_id": "ACC_1100"})["summary"]


def test_community_explain_compare_patterns():
    assert run("get_community", {"account_id": "ACC_9002"})["data"]["id"] == "COM_1"
    assert run("get_community", {"community_id": "COM_2"})["data"]["member_count"] == 16
    e = run("get_risk_explanation", {"account_id": "ACC_9020"})["data"]
    assert [x["rule"] for x in e["contributions"]][0] == "FAN_OUT"
    assert len(run("compare_accounts", {"account_ids": ["ACC_9001", "ACC_9010"]})["data"]) == 2
    assert {x["rule"] for x in run("detect_patterns", {"account_id": "ACC_9030"})["data"]} == {"VELOCITY"}


def test_output_cap_and_validation():
    r = run("get_neighbors", {"account_id": "ACC_9010", "direction": "in"})
    assert len(r["data"]) == 15
    big = run("search_transactions", {})
    assert len(big["data"]) == 20 and len(big["referenced_nodes"]) <= 20
    assert "not found" in run("get_account_details", {"account_id": "ACC_0"})["summary"]
    assert "Invalid input" in run("get_account_details", {"account_id": "bob"})["summary"]
    assert "Invalid input" in run("get_top_risky_accounts", {"limit": 500})["summary"]
    assert "Invalid date" in run("search_transactions", {"start_date": "yesterday"})["summary"]
    assert "Unknown tool" in run("drop_tables", {})["summary"]


def test_actions_never_run_unconfirmed():
    s = get_store()
    aid = next(a["id"] for a in s.alerts.values() if a["status"] == "open")
    with pytest.raises(ConfirmationRequired):
        run("update_alert_status", {"alert_id": aid, "status": "closed"})
    assert s.alerts[aid]["status"] == "open"
    r = run("update_alert_status", {"alert_id": aid, "status": "closed", "note": "ok"}, confirmed=True)
    assert r["data"]["new_status"] == "closed"
    s.alerts[aid]["status"] = "open"
    assert "not found" in run("update_alert_status", {"alert_id": "ALR_999", "status": "closed"}, confirmed=True)["summary"]
