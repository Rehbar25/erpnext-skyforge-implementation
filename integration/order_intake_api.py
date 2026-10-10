"""BR-12: REST order intake from SkyForge's website, creating draft Sales Orders in ERPNext.

  POST /api/v1/orders                   submit an order (idempotent on submission_id)
  GET  /api/v1/orders/{submission_id}   order status, so customers stop emailing sales (pain point 5)
  GET  /health

Design decisions (agreed with SkyForge sales):
  - Orders arrive as DRAFT Sales Orders; a salesperson reviews and submits. The website never
    commits stock or delivery dates on its own.
  - Customers are matched on GSTIN. Unknown GSTINs are rejected (422), never auto-created, so
    the customer master stays governed.
  - Prices come from ERPNext's Standard Selling price list, never from the request body.
  - submission_id is stored on the order (po_no = "WEB:<id>"), so retries from the website
    return the existing order instead of creating duplicates.

Run:  uvicorn integration.order_intake_api:app --port 8090
"""

import os
from datetime import date

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

from config.configure import COMPANY, WH_FG

API_KEY = os.getenv("INTAKE_API_KEY", "dev-intake-key")
STATUS_FOR_CUSTOMER = {
    0: "Received: under review by SkyForge sales",
    "To Deliver and Bill": "Confirmed: in production",
    "To Bill": "Shipped",
    "To Deliver": "Confirmed: in production",
    "Completed": "Delivered and invoiced",
    "Cancelled": "Cancelled",
}


class OrderLine(BaseModel):
    model: str = Field(examples=["SF-Q250"])
    qty: int = Field(gt=0, le=50)


class OrderRequest(BaseModel):
    submission_id: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9\-_]+$")
    gstin: str = Field(min_length=15, max_length=15)
    contact_email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    required_by: date
    lines: list[OrderLine] = Field(min_length=1, max_length=10)
    notes: str = Field(default="", max_length=500)

    @field_validator("gstin")
    @classmethod
    def upper(cls, v):
        return v.upper()

    @field_validator("required_by")
    @classmethod
    def in_future(cls, v):
        if v <= date.today():
            raise ValueError("required_by must be a future date")
        return v


def get_erp():                                 # overridden in tests
    from erp.client import ERPClient
    return ERPClient()


def require_key(x_api_key: str = Header(default="")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


app = FastAPI(title="SkyForge Order Intake API", version="1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


def _find_order(erp, submission_id):
    rows = erp.get_list("Sales Order", filters={"po_no": f"WEB:{submission_id}", "docstatus": ["!=", 2]},
                        fields=["name", "docstatus", "status", "grand_total", "customer", "delivery_date"])
    return rows[0] if rows else None


def _status(row):
    return STATUS_FOR_CUSTOMER.get(0 if row["docstatus"] == 0 else row["status"], row["status"])


@app.post("/api/v1/orders", status_code=201, dependencies=[Depends(require_key)])
def create_order(req: OrderRequest, response: Response, erp=Depends(get_erp)):
    existing = _find_order(erp, req.submission_id)
    if existing:                                # idempotent retry: 200, not a new resource
        response.status_code = 200
        return {"sales_order": existing["name"], "status": _status(existing),
                "grand_total": existing["grand_total"], "duplicate": True}

    customers = erp.get_list("Customer", filters={"tax_id": req.gstin, "disabled": 0}, fields=["name"])
    if not customers:
        raise HTTPException(422, detail="GSTIN not registered with SkyForge. Our sales team will contact you "
                                        "to open an account.")

    items = []
    for ln in req.lines:
        found = erp.get_list("Item", filters={"name": ln.model, "is_sales_item": 1, "disabled": 0}, fields=["name"])
        if not found:
            raise HTTPException(422, detail=f"Unknown model '{ln.model}'")
        price = erp.get_list("Item Price", filters={"item_code": ln.model, "price_list": "Standard Selling"},
                             fields=["price_list_rate"])
        items.append({"item_code": ln.model, "qty": ln.qty, "rate": price[0]["price_list_rate"],
                      "delivery_date": str(req.required_by), "warehouse": WH_FG})

    so = erp.insert("Sales Order", {
        "customer": customers[0]["name"], "company": COMPANY, "transaction_date": str(date.today()),
        "delivery_date": str(req.required_by), "po_no": f"WEB:{req.submission_id}",
        "order_type": "Sales", "selling_price_list": "Standard Selling", "items": items,
    })
    erp.insert("Comment", {"comment_type": "Comment", "reference_doctype": "Sales Order", "reference_name": so["name"],
                           "content": f"Website order {req.submission_id} from {req.contact_email}"
                                      + (f". Note: {req.notes}" if req.notes else "")})
    return {"sales_order": so["name"], "status": STATUS_FOR_CUSTOMER[0], "grand_total": so["grand_total"],
            "duplicate": False}


@app.get("/api/v1/orders/{submission_id}", dependencies=[Depends(require_key)])
def order_status(submission_id: str, erp=Depends(get_erp)):
    row = _find_order(erp, submission_id)
    if not row:
        raise HTTPException(404, detail="No order with that submission_id")
    return {"sales_order": row["name"], "status": _status(row), "expected_delivery": row["delivery_date"],
            "grand_total": row["grand_total"]}
