"""Load cleansed data into ERPNext via REST, in dependency order, then verify by reading back.

Order: Suppliers -> Items (+prices) -> Customers -> BOMs (bottom-up) -> Opening stock.
Every step is idempotent so the load can be re-run during mock cutovers.
"""

from config.configure import ABBR, COMPANY, WH_FG, WH_STORES
from erp.client import ERPClient, ERPError

OPENING_DATE = "2026-10-01"
OPENING_TAG = "MIGRATION: opening stock from legacy count sheet"
BUYING, SELLING = "Standard Buying", "Standard Selling"


def rolled_up_cost(code, data, _memo=None):
    """Material cost of an item: purchase price for components, BOM roll-up for assemblies."""
    memo = {} if _memo is None else _memo
    if code not in memo:
        item = data.items[code]
        memo[code] = item["buy_rate"] if item["buy_rate"] is not None else sum(
            qty * rolled_up_cost(comp, data, memo) for comp, qty in data.boms.get(code, []))
    return memo[code]


def bom_build_order(boms):
    """Parents ordered so every sub-assembly BOM exists before the BOM that uses it."""
    order, seen = [], set()

    def visit(p):
        if p in seen:
            return
        seen.add(p)
        for comp, _ in boms[p]:
            if comp in boms:
                visit(comp)
        order.append(p)

    for p in boms:
        visit(p)
    return order


class Loader:
    def __init__(self, client: ERPClient, data):
        self.c, self.d = client, data
        self.results = {k: {"created": 0, "updated": 0, "skipped": 0, "failed": []}
                        for k in ("Supplier", "Item", "Item Price", "Customer", "BOM", "Opening Stock")}
        self.supplier_names = {code: s["name"] for code, s in data.suppliers.items()}

    def _record(self, entity, key, fn):
        try:
            outcome = fn()
            self.results[entity][outcome] += 1
        except ERPError as e:
            self.results[entity]["failed"].append((key, str(e)[:300]))

    def _upsert(self, doctype, name, doc):
        _, created = self.c.upsert(doctype, name, doc)
        return "created" if created else "updated"

    def _linked(self, doctype, link_doctype, link_name):
        return self.c.get_list(doctype, filters=[["Dynamic Link", "link_doctype", "=", link_doctype],
                                                 ["Dynamic Link", "link_name", "=", link_name]])

    # ------------------------------------------------------------------ suppliers
    def suppliers(self):
        for code, s in self.d.suppliers.items():
            def go(s=s):
                outcome = self._upsert("Supplier", s["name"], {
                    "supplier_name": s["name"], "supplier_group": s["group"], "supplier_type": "Company",
                    "country": "India", "tax_id": s["gstin"] or None,
                    "supplier_details": f"Legacy ID {s['code']} · lead time {s['lead_days']} days"})
                contact = {"first_name": s["name"], "is_primary_contact": 1,
                           "email_ids": [{"email_id": s["email"], "is_primary": 1}] if s["email"] else [],
                           "phone_nos": [{"phone": s["phone"], "is_primary_phone": 1}] if s["phone"] else [],
                           "links": [{"link_doctype": "Supplier", "link_name": s["name"]}]}
                existing = self._linked("Contact", "Supplier", s["name"])
                if existing:
                    self.c.update("Contact", existing[0]["name"], contact)
                else:
                    self.c.insert("Contact", contact)
                return outcome
            self._record("Supplier", code, go)

    # ------------------------------------------------------------------ items
    def items(self):
        for code, it in self.d.items.items():
            is_component, is_product = it["group"] == "Components", it["group"] == "Products"
            doc = {
                "item_code": code, "item_name": it["name"], "item_group": it["group"],
                "stock_uom": it["uom"], "is_stock_item": 1, "include_item_in_manufacturing": 1,
                "is_purchase_item": int(is_component), "is_sales_item": int(is_product),
                "lead_time_days": it["lead_days"], "valuation_rate": rolled_up_cost(code, self.d),
                "item_defaults": [{"company": COMPANY,
                                   "default_warehouse": WH_FG if is_product else WH_STORES,
                                   "default_supplier": self.supplier_names.get(it["supplier"])}],
                "reorder_levels": [{"warehouse": WH_STORES, "warehouse_group": f"All Warehouses - {ABBR}",
                                    "warehouse_reorder_level": it["reorder_level"],
                                    "warehouse_reorder_qty": it["reorder_qty"],
                                    "material_request_type": "Purchase"}] if it["reorder_level"] else [],
                "supplier_items": [{"supplier": self.supplier_names[it["supplier"]],
                                    "supplier_part_no": it["supplier_part_no"]}] if it["supplier_part_no"] else [],
            }
            if it["uom"] != "Nos":
                doc["uoms"] = [{"uom": it["uom"], "conversion_factor": 1}]
            self._record("Item", code, lambda doc=doc: self._upsert("Item", doc["item_code"], doc))

            for price_list, rate in ((BUYING, it["buy_rate"]), (SELLING, it["sell_rate"])):
                if rate:
                    self._record("Item Price", f"{code}@{price_list}",
                                 lambda code=code, pl=price_list, rate=rate: self._price(code, pl, rate))

    def _price(self, code, price_list, rate):
        existing = self.c.get_list("Item Price", filters={"item_code": code, "price_list": price_list})
        if existing:
            self.c.update("Item Price", existing[0]["name"], {"price_list_rate": rate})
            return "updated"
        self.c.insert("Item Price", {"item_code": code, "price_list": price_list, "price_list_rate": rate})
        return "created"

    # ------------------------------------------------------------------ customers
    def customers(self):
        for code, cu in self.d.customers.items():
            def go(cu=cu):
                outcome = self._upsert("Customer", cu["name"], {
                    "customer_name": cu["name"], "customer_type": "Company", "customer_group": "Commercial",
                    "territory": "India", "market_segment": cu["segment"] or None, "tax_id": cu["gstin"] or None,
                    "customer_details": f"Legacy ID {cu['code']}"})
                address = {"address_title": cu["name"], "address_type": "Billing", "address_line1": cu["city"],
                           "city": cu["city"], "state": cu["state"], "country": "India", "is_primary_address": 1,
                           "links": [{"link_doctype": "Customer", "link_name": cu["name"]}]}
                existing = self._linked("Address", "Customer", cu["name"])
                if existing:
                    self.c.update("Address", existing[0]["name"], address)
                else:
                    self.c.insert("Address", address)
                return outcome
            self._record("Customer", code, go)

    # ------------------------------------------------------------------ BOMs
    def boms(self):
        for parent in bom_build_order(self.d.boms):
            def go(parent=parent):
                if self.c.get_list("BOM", filters={"item": parent, "docstatus": 1, "is_default": 1}):
                    return "skipped"
                bom = self.c.insert("BOM", {
                    "item": parent, "company": COMPANY, "quantity": 1, "is_active": 1, "is_default": 1,
                    "rm_cost_as_per": "Price List", "buying_price_list": BUYING,
                    "items": [{"item_code": comp, "qty": qty} for comp, qty in self.d.boms[parent]]})
                self.c.submit("BOM", bom["name"])
                return "created"
            self._record("BOM", parent, go)

    # ------------------------------------------------------------------ opening stock
    def opening_stock(self):
        def go():
            if self.c.get_list("Stock Reconciliation", filters={"purpose": "Opening Stock", "docstatus": 1}):
                return "skipped"
            doc = self.c.insert("Stock Reconciliation", {
                "company": COMPANY, "purpose": "Opening Stock", "set_posting_time": 1,
                "posting_date": OPENING_DATE, "posting_time": "00:00:00",
                "expense_account": f"Temporary Opening - {ABBR}", "remarks": OPENING_TAG,
                "items": [{"item_code": code, "warehouse": wh, "qty": qty,
                           "valuation_rate": rolled_up_cost(code, self.d)}
                          for (code, wh), qty in sorted(self.d.stock.items())]})
            self.c.submit("Stock Reconciliation", doc["name"])
            return "created"
        self._record("Opening Stock", "Stock Reconciliation", go)

    def run(self):
        for step in (self.suppliers, self.items, self.customers, self.boms, self.opening_stock):
            print(f"  loading {step.__name__} ...")
            step()
        return self.results


# --------------------------------------------------------------------------- verification
def verify(c: ERPClient, data):
    """Read everything back from ERPNext and compare with what should be there."""
    checks = []

    def check(name, expected, actual):
        checks.append({"check": name, "expected": expected, "actual": actual, "ok": expected == actual})

    erp_items = {i["name"] for i in c.get_list("Item", filters=[["name", "in", list(data.items)]])}
    check("Items present", len(data.items), len(erp_items))
    erp_sup = {s["name"] for s in c.get_list("Supplier")}
    check("Suppliers present", len(data.suppliers),
          sum(s["name"] in erp_sup for s in data.suppliers.values()))
    erp_cust = {s["name"] for s in c.get_list("Customer")}
    check("Customers present", len(data.customers),
          sum(cu["name"] in erp_cust for cu in data.customers.values()))
    check("Customers with address", len(data.customers),
          sum(bool(c.get_list("Address", filters=[["Dynamic Link", "link_name", "=", cu["name"]]]))
              for cu in data.customers.values()))

    boms = c.get_list("BOM", filters={"docstatus": 1, "is_default": 1}, fields=["name", "item", "raw_material_cost"])
    by_item = {b["item"]: b for b in boms}
    check("Default BOMs submitted", len(data.boms), sum(p in by_item for p in data.boms))
    for p in data.boms:
        lines = c.get("BOM", by_item[p]["name"])["items"] if p in by_item else []
        check(f"BOM {p} lines", sorted((x, float(q)) for x, q in data.boms[p]),
              sorted((ln["item_code"], float(ln["qty"])) for ln in lines))
        check(f"BOM {p} cost (₹)", round(rolled_up_cost(p, data), 2),
              round(by_item[p]["raw_material_cost"], 2) if p in by_item else None)

    # Check the opening-stock voucher's ledger entries, so this stays valid after later transactions.
    recon = c.get_list("Stock Reconciliation", filters={"purpose": "Opening Stock", "docstatus": 1})
    sle = c.get_list("Stock Ledger Entry", filters={"voucher_no": recon[0]["name"], "is_cancelled": 0},
                     fields=["item_code", "warehouse", "qty_after_transaction", "stock_value_difference"]) \
        if recon else []
    posted = {(e["item_code"], e["warehouse"]): e for e in sle}
    qty_ok = sum(abs(posted.get(k, {}).get("qty_after_transaction", 0) - q) < 1e-6 for k, q in data.stock.items())
    check("Stock lines matching count sheet", len(data.stock), qty_ok)
    expected_value = round(sum(q * rolled_up_cost(code, data) for (code, _), q in data.stock.items()), 2)
    check("Opening stock value (₹)", expected_value, round(sum(e["stock_value_difference"] for e in sle), 2))
    return checks
