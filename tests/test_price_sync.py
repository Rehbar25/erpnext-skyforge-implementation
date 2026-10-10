"""Supplier SOAP integration: the service contract and the price-update business rules."""

import threading

import pytest
from zeep.exceptions import Fault

from integration import supplier_soap_service as svc
from integration.price_sync import fetch_price_list, plan_updates


@pytest.fixture(scope="module")
def wsdl():
    srv = svc.serve(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}{svc.PATH}?wsdl"
    srv.shutdown()


def test_soap_price_list_roundtrip(wsdl):
    pl_id, lines = fetch_price_list(wsdl)
    assert pl_id == svc.PRICE_LIST_ID
    assert len(lines) == len(svc.PRICE_LIST)
    esc = next(ln for ln in lines if ln["part_no"] == "AP-ESC-B32-30")
    assert esc == {"part_no": "AP-ESC-B32-30", "description": "ESC 30A BLHeli_32", "price": 1020.0,
                   "currency": "INR", "lead_days": 35, "valid_from": "2026-10-01"}


def test_soap_fault_on_unknown_account(wsdl):
    with pytest.raises(Fault, match="Unknown partner account"):
        fetch_price_list(wsdl, account_id="NOT-OURS")


def test_soap_outage_raises(wsdl, monkeypatch):
    monkeypatch.setenv("AEROPARTS_MAINTENANCE", "1")
    with pytest.raises(Fault, match="maintenance"):
        fetch_price_list(wsdl)


PART_MAP = {"P-1": "A", "P-2": "B", "P-3": "C", "P-4": "D"}
CURRENT = {k: {"price": 100.0, "lead_days": 28} for k in "ABCD"}


def line(part, price, lead=28, currency="INR"):
    return {"part_no": part, "description": "", "price": price, "currency": currency,
            "lead_days": lead, "valid_from": "2026-10-01"}


def by_item(actions):
    return {a.get("item") or a["part_no"]: a for a in actions}


def test_plan_applies_small_changes_and_holds_large_ones():
    acts = by_item(plan_updates([line("P-1", 107), line("P-2", 150), line("P-3", 100)], PART_MAP, CURRENT))
    assert acts["A"]["action"] == "apply"
    assert acts["B"]["action"] == "hold"           # +50% needs a human
    assert acts["C"]["action"] == "unchanged"
    assert acts["D"]["action"] == "missing_from_feed"


def test_plan_lead_time_only_change_is_applied():
    acts = by_item(plan_updates([line("P-1", 100, lead=35)], PART_MAP, CURRENT))
    assert acts["A"]["action"] == "apply" and acts["A"]["new_lead"] == 35


def test_plan_rejects_bad_lines_and_flags_unmapped():
    acts = by_item(plan_updates([line("P-1", 100, currency="USD"), line("P-2", 0), line("P-99", 50)],
                                PART_MAP, CURRENT))
    assert acts["A"]["action"] == "rejected"
    assert acts["B"]["action"] == "rejected"
    assert acts["P-99"]["action"] == "unmapped"


def test_plan_against_real_feed():
    lines = [line(p, price, lead) for p, _d, price, lead in svc.PRICE_LIST]
    part_map = {"AP-ESC-B32-30": "ESC-30A", "AP-FC-H743": "FC-H7", "AP-RX-ELRS24": "RX-ELRS"}
    current = {"ESC-30A": {"price": 950.0, "lead_days": 28}, "FC-H7": {"price": 11500.0, "lead_days": 28},
               "RX-ELRS": {"price": 1200.0, "lead_days": 28}}
    acts = by_item(plan_updates(lines, part_map, current))
    assert acts["ESC-30A"]["action"] == "apply"
    assert acts["FC-H7"]["action"] == "hold"
    assert acts["RX-ELRS"]["action"] == "missing_from_feed"
    assert acts["AP-BLM-2207-1950"]["action"] == "unmapped"
