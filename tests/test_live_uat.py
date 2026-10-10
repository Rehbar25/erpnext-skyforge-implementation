"""Automated UAT evidence against the live ERPNext sandbox (docs/06_uat_test_scripts.md).

Runs after: configure -> migration -> business cycle -> reorder job -> price sync -> one web order.
Negative tests submit in a single call, so a rejected document never leaves a draft behind.
"""

from pathlib import Path

import pytest

from config.configure import COMPANY, DEMO_PASSWORD, WH_FG, WH_STORES
from erp.client import ERPClient, ERPError
from migration.cleanse import cleanse, load_decisions
from migration.load import verify

pytestmark = pytest.mark.live
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def c():
    return ERPClient()


def submitted_one_shot(c, doctype, doc):
    return c.insert(doctype, {**doc, "docstatus": 1})


# ------------------------------------------------------------------ master data & config
def test_uat01_migration_reconciles(c):
    data = cleanse(ROOT / "data/legacy/SkyForge_Master_Data.xlsx", load_decisions(ROOT / "migration/decisions.json"))
    failed = [x for x in verify(c, data) if not x["ok"] and "cost" not in x["check"]]
    # BOM cost checks are excluded: the later price sync legitimately changes them (UAT-12).
    assert failed == []


def test_uat02_multilevel_bom(c):
    bom = c.get("BOM", c.get_list("BOM", filters={"item": "SF-Q250", "is_default": 1})[0]["name"])
    subs = [i for i in bom["items"] if i["item_code"].startswith("SA-")]
    assert len(subs) == 2 and all(i.get("bom_no") for i in subs)


def test_uat03_receipt_without_po_rejected(c):
    with pytest.raises(ERPError, match="Purchase Order number required"):
        submitted_one_shot(c, "Purchase Receipt", {
            "supplier": "VoltCell Energy", "company": COMPANY, "set_warehouse": WH_STORES,
            "items": [{"item_code": "BAT-4S1500", "qty": 5, "rate": 2900, "warehouse": WH_STORES}]})


def test_uat04_delivery_without_sales_order_rejected(c):
    with pytest.raises(ERPError, match="Sales Order required"):
        submitted_one_shot(c, "Delivery Note", {
            "customer": "TerraMap Surveys", "company": COMPANY,
            "items": [{"item_code": "SF-Q250", "qty": 1, "rate": 68000, "warehouse": WH_FG}]})


def test_uat05_negative_stock_blocked(c):
    with pytest.raises(ERPError, match="needed in .*Stores - SFD"):
        submitted_one_shot(c, "Stock Entry", {
            "stock_entry_type": "Material Issue", "company": COMPANY,
            "items": [{"item_code": "CAM-MAP", "qty": 500, "s_warehouse": WH_STORES}]})


def test_uat14_store_keeper_cannot_raise_purchase_orders():
    stores = ERPClient(user="stores@skyforge.example", password=DEMO_PASSWORD)
    with pytest.raises(ERPError, match="403.*does not have doctype access"):
        stores.insert("Purchase Order", {"supplier": "VoltCell Energy", "company": COMPANY,
                                         "schedule_date": "2026-11-01",
                                         "items": [{"item_code": "BAT-4S1500", "qty": 1, "rate": 2900}]})


# ------------------------------------------------------------------ business cycle
def test_uat06_mrp_orders_only_the_shortfall(c):
    pp = c.get_list("Production Plan", filters={"docstatus": 1})[0]["name"]
    rows = c.get_list("Material Request", filters=[["Material Request Item", "production_plan", "=", pp]])
    mr = c.get("Material Request", rows[0]["name"])
    assert sorted((i["item_code"], i["qty"]) for i in mr["items"]) == [("ESC-30A", 14), ("GPS-M10", 4)]


def test_uat07_procure_to_pay_complete(c):
    for po in c.get_list("Purchase Order", filters={"docstatus": 1}, fields=["name", "per_received", "per_billed"]):
        assert po["per_received"] == 100 and po["per_billed"] == 100, po["name"]


def test_uat08_work_orders_completed(c):
    wos = c.get_list("Work Order", filters={"docstatus": 1}, fields=["name", "status", "qty", "produced_qty"])
    assert len(wos) == 9
    assert all(w["status"] == "Completed" and w["produced_qty"] == w["qty"] for w in wos)


def test_uat09_order_to_cash_complete(c):
    sos = c.get_list("Sales Order", filters={"docstatus": 1}, fields=["name", "per_delivered", "per_billed"])
    assert len(sos) == 3 and all(s["per_delivered"] == 100 and s["per_billed"] == 100 for s in sos)
    paid = c.get_list("Sales Invoice", filters={"docstatus": 1, "outstanding_amount": 0})
    assert len(paid) == 1


def test_uat10_actual_cost_matches_bom(c):
    entries = c.get_list("Stock Entry", filters={"purpose": "Manufacture", "docstatus": 1}, fields=["name"])
    costs = {}
    for e in entries:
        fg = next(i for i in c.get("Stock Entry", e["name"])["items"] if i.get("is_finished_item"))
        costs.setdefault(fg["item_code"], set()).add(round(fg["valuation_rate"], 2))
    assert costs["SF-Q250"] == {41419.0} and costs["SF-X450"] == {99486.0}


def test_uat11_reorder_request_auto_raised(c):
    auto = c.get_list("Material Request", filters={"auto_created_via_reorder": 1, "docstatus": 1})
    assert len(auto) == 1
    lines = {i["item_code"] for i in c.get("Material Request", auto[0]["name"])["items"]}
    assert {"CAM-4K", "ESC-30A", "GPS-M10"} <= lines


# ------------------------------------------------------------------ integrations
def test_uat12_price_sync_applied_with_controls(c):
    def price(item):
        return c.get_list("Item Price", filters={"item_code": item, "price_list": "Standard Buying"},
                          fields=["price_list_rate"])[0]["price_list_rate"]
    assert price("ESC-30A") == 1020 and c.get("Item", "ESC-30A")["lead_time_days"] == 35
    assert price("FC-H7") == 11500                      # +47% quote held, not applied
    bom = c.get_list("BOM", filters={"item": "SF-Q250", "is_default": 1}, fields=["total_cost"])[0]
    assert bom["total_cost"] == 41699
    assert c.get_list("Comment", filters={"reference_doctype": "Supplier", "content": ["like", "Price sync%"]})


def test_uat13_web_order_lands_as_draft(c):
    so = c.get_list("Sales Order", filters={"po_no": "WEB:WEB-2026-0045"}, fields=["docstatus", "customer", "grand_total"])
    assert so == [{"docstatus": 0, "customer": "Coastal Wind Energy", "grand_total": 204000.0}]
