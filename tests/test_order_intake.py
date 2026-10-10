"""Order intake REST API against an in-memory fake of ERPNext."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from integration import order_intake_api as api

GSTIN = "36AABDS1555L1Z5"
KEY = {"X-API-Key": api.API_KEY}


class FakeERP:
    def __init__(self):
        self.orders, self.comments = [], []
        self.customers = [{"name": "GreenAcre Agritech", "tax_id": GSTIN, "disabled": 0}]
        self.items = {"SF-Q250": 68000.0, "SF-X450": 145000.0}

    def get_list(self, doctype, filters=None, fields=("name",), limit=0):
        f = filters or {}
        if doctype == "Sales Order":
            return [o for o in self.orders if o["po_no"] == f["po_no"]]
        if doctype == "Customer":
            return [{"name": c["name"]} for c in self.customers if c["tax_id"] == f["tax_id"]]
        if doctype == "Item":
            return [{"name": f["name"]}] if f["name"] in self.items else []
        if doctype == "Item Price":
            return [{"price_list_rate": self.items[f["item_code"]]}]
        raise AssertionError(doctype)

    def insert(self, doctype, doc):
        if doctype == "Comment":
            self.comments.append(doc)
            return doc
        so = {**doc, "name": f"SAL-ORD-TEST-{len(self.orders) + 1:05d}", "docstatus": 0, "status": "Draft",
              "grand_total": sum(i["qty"] * i["rate"] for i in doc["items"])}
        self.orders.append(so)
        return so


@pytest.fixture
def erp():
    return FakeERP()


@pytest.fixture
def client(erp):
    api.app.dependency_overrides[api.get_erp] = lambda: erp
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


def order(**over):
    body = {"submission_id": "WEB-1", "gstin": GSTIN.lower(), "contact_email": "ops@greenacre.example",
            "required_by": str(date.today() + timedelta(days=30)), "lines": [{"model": "SF-Q250", "qty": 3}]}
    return {**body, **over}


def test_creates_draft_order_priced_from_erp(client, erp):
    r = client.post("/api/v1/orders", json=order(lines=[{"model": "SF-Q250", "qty": 3},
                                                        {"model": "SF-X450", "qty": 1}]), headers=KEY)
    assert r.status_code == 201
    assert r.json()["grand_total"] == 3 * 68000 + 145000
    so = erp.orders[0]
    assert so["docstatus"] == 0 and so["po_no"] == "WEB:WEB-1" and so["customer"] == "GreenAcre Agritech"
    assert "ops@greenacre.example" in erp.comments[0]["content"]


def test_retry_is_idempotent(client, erp):
    first = client.post("/api/v1/orders", json=order(), headers=KEY)
    again = client.post("/api/v1/orders", json=order(), headers=KEY)
    assert (first.status_code, again.status_code) == (201, 200)
    assert again.json()["duplicate"] is True
    assert len(erp.orders) == 1


def test_status_endpoint(client):
    client.post("/api/v1/orders", json=order(), headers=KEY)
    r = client.get("/api/v1/orders/WEB-1", headers=KEY)
    assert r.status_code == 200 and r.json()["status"].startswith("Received")
    assert client.get("/api/v1/orders/NOPE", headers=KEY).status_code == 404


def test_requires_api_key(client):
    assert client.post("/api/v1/orders", json=order()).status_code == 401
    assert client.post("/api/v1/orders", json=order(), headers={"X-API-Key": "wrong"}).status_code == 401


@pytest.mark.parametrize("override,fragment", [
    ({"gstin": "29AAAAA0000A1Z5"}, "GSTIN not registered"),
    ({"lines": [{"model": "SF-Z999", "qty": 1}]}, "Unknown model"),
])
def test_business_rejections(client, erp, override, fragment):
    r = client.post("/api/v1/orders", json=order(**override), headers=KEY)
    assert r.status_code == 422 and fragment in r.json()["detail"]
    assert erp.orders == []


@pytest.mark.parametrize("override", [
    {"required_by": str(date.today())},
    {"lines": []},
    {"lines": [{"model": "SF-Q250", "qty": 0}]},
    {"lines": [{"model": "SF-Q250", "qty": 500}]},
    {"contact_email": "not-an-email"},
    {"submission_id": "has spaces!"},
])
def test_schema_validation(client, override):
    assert client.post("/api/v1/orders", json=order(**override), headers=KEY).status_code == 422
