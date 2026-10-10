"""Submit one website order through the running order-intake API (as the website would)."""

import os
import sys
from datetime import date, timedelta

import requests

from erp.client import ERPClient

API = os.getenv("INTAKE_URL", "http://127.0.0.1:8090")
KEY = os.getenv("INTAKE_API_KEY", "dev-intake-key")

gstin = ERPClient().get("Customer", "Coastal Wind Energy")["tax_id"]
body = {"submission_id": "WEB-2026-0045", "gstin": gstin, "contact_email": "ops@coastalwind.example",
        "required_by": str(date.today() + timedelta(days=60)),
        "lines": [{"model": "SF-Q250", "qty": 3}], "notes": "Need spare batteries quoted separately"}
for attempt in ("submit", "retry"):
    r = requests.post(f"{API}/api/v1/orders", json=body, headers={"X-API-Key": KEY}, timeout=30)
    print(f"{attempt}: HTTP {r.status_code} {r.json()}")
r = requests.get(f"{API}/api/v1/orders/WEB-2026-0045", headers={"X-API-Key": KEY}, timeout=30)
print(f"status: HTTP {r.status_code} {r.json()}")
sys.exit(0 if r.ok else 1)
