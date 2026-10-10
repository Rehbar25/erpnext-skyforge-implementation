"""Phase 3: run SkyForge's first month of operations end-to-end through ERPNext.

  Order-to-Cash  : Sales Orders -> Delivery Notes -> Sales Invoices -> Payment
  Planning (MRP) : Production Plan nets demand against stock, explodes multi-level BOMs
  Procure-to-Pay : Material Request -> Purchase Order -> Purchase Receipt -> Purchase Invoice
  Manufacturing  : Work Orders for sub-assemblies, then drones (transfer -> manufacture)
  Costing        : actual manufactured cost vs selling price

Every document created is recorded in a trail that docs/03_business_cycle_results.md and
the UAT report are generated from. Uses ERPNext's own mappers and planners (not hand-built
documents) so the run exercises the same logic as the UI.

Run:  python -m scenarios.business_cycle
"""

import json
from collections import defaultdict
from pathlib import Path

from config.configure import COMPANY, WH_FG, WH_STORES, WH_WIP
from erp.client import ERPClient

ROOT = Path(__file__).resolve().parent.parent
TRAIL_FILE = ROOT / "data" / "output" / "business_cycle_trail.json"
TODAY = "2026-10-08"

# Customer, model, qty, customer PO reference, requested delivery
DEMAND = [
    ("SunGrid Solar Parks", "SF-Q250", 6, "SG/PO/2026/114", "2026-11-10"),
    ("TerraMap Surveys", "SF-X450", 2, "TMS-8812", "2026-11-20"),
    ("Deccan Infra Inspections", "SF-Q250", 4, "DII/26/077", "2026-11-15"),
]

M = {  # ERPNext's own whitelisted mappers / planners
    "mr_to_po": "erpnext.stock.doctype.material_request.material_request.make_purchase_order",
    "po_to_pr": "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
    "pr_to_pi": "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
    "so_to_dn": "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
    "dn_to_si": "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
    "payment": "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry",
    "wo_entry": "erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry",
    "mr_items": "erpnext.manufacturing.doctype.production_plan.production_plan.get_items_for_material_requests",
}


class Cycle:
    def __init__(self, c: ERPClient):
        self.c = c
        self.trail = defaultdict(list)   # step -> [records]

    def log(self, step, **rec):
        self.trail[step].append(rec)
        print(f"  [{step}] " + ", ".join(f"{k}={v}" for k, v in rec.items()))

    def price(self, item, price_list):
        rows = self.c.get_list("Item Price", filters={"item_code": item, "price_list": price_list},
                               fields=["price_list_rate"])
        return rows[0]["price_list_rate"]

    def stock(self, item, wh):
        rows = self.c.get_list("Bin", filters={"item_code": item, "warehouse": wh}, fields=["actual_qty"])
        return rows[0]["actual_qty"] if rows else 0

    # ------------------------------------------------------------------ 1. demand
    def sales_orders(self):
        if self.c.get_list("Sales Order", filters={"po_no": DEMAND[0][3]}):
            raise SystemExit("Business cycle already run (sales orders exist). Restore a clean site to re-run.")
        for customer, item, qty, po_no, delivery in DEMAND:
            rate = self.price(item, "Standard Selling")   # REST does not apply price lists; the UI does
            so = self.c.insert_submit("Sales Order", {
                "customer": customer, "company": COMPANY, "transaction_date": TODAY, "po_no": po_no,
                "delivery_date": delivery, "selling_price_list": "Standard Selling",
                "items": [{"item_code": item, "qty": qty, "rate": rate, "delivery_date": delivery,
                           "warehouse": WH_FG}]})
            self.log("sales_order", name=so["name"], customer=customer, item=item, qty=qty,
                     value=so["grand_total"], delivery=delivery)

    # ------------------------------------------------------------------ 2. MRP
    def production_plan(self):
        sos = [r["name"] for r in self.trail["sales_order"]]
        pp = {"doctype": "Production Plan", "company": COMPANY, "posting_date": TODAY,
              "get_items_from": "Sales Order", "for_warehouse": WH_STORES,
              # Field name is historical; its v16 label is "Consider Projected Qty in Calculation (RM)".
              # Must be 1 or MRP orders the gross requirement and ignores stock on hand.
              "ignore_existing_ordered_qty": 1,
              "sales_orders": [{"doctype": "Production Plan Sales Order", "sales_order": s} for s in sos]}
        pp, _ = self.c.run_doc_method(pp, "get_items")

        # Net demand against finished goods already on the shelf (planner's call, documented in UAT).
        on_hand = {i: self.stock(i, WH_FG) for i in {r["item_code"] for r in pp["po_items"]}}
        for row in pp["po_items"]:
            take = min(on_hand[row["item_code"]], row["planned_qty"])
            on_hand[row["item_code"]] -= take
            self.log("mrp_netting", item=row["item_code"], sales_order=row["sales_order"],
                     demand=row["planned_qty"], from_fg_stock=take, to_build=row["planned_qty"] - take)
            row["planned_qty"] -= take
        pp["po_items"] = [r for r in pp["po_items"] if r["planned_qty"] > 0]
        for r in pp["po_items"]:
            r["warehouse"] = WH_FG

        pp = self.c.insert("Production Plan", {k: v for k, v in pp.items() if k not in ("name", "__islocal")})
        pp, _ = self.c.run_doc_method(pp, "get_sub_assembly_items")
        for r in pp["sub_assembly_items"]:
            r["fg_warehouse"] = WH_STORES          # sub-assemblies are stocked in Stores
            r["type_of_manufacturing"] = "In House"
        pp = self.c.update("Production Plan", pp["name"], {"sub_assembly_items": pp["sub_assembly_items"]})

        mr_items = self.c.call_json(M["mr_items"], doc=pp)   # passing warehouses switches to transfer mode
        pp = self.c.update("Production Plan", pp["name"], {"mr_items": mr_items})
        self.c.submit("Production Plan", pp["name"])
        pp = self.c.get("Production Plan", pp["name"])
        self.log("production_plan", name=pp["name"],
                 builds=", ".join(f"{r['item_code']}×{r['planned_qty']:g}" for r in pp["po_items"]),
                 sub_assemblies=", ".join(f"{r['production_item']}×{r['qty']:g}" for r in pp["sub_assembly_items"]))
        # ERPNext plans per sales order; summarise per component for the planner's view.
        per_item = {}
        for r in pp["mr_items"]:
            agg = per_item.setdefault(r["item_code"], {"required": 0, "available": r.get("projected_qty"), "to_order": 0})
            agg["required"] += r.get("required_bom_qty") or 0
            agg["to_order"] += r["quantity"]
        for code, a in per_item.items():
            self.log("mrp_requirement", item=code, required=a["required"], available=a["available"],
                     to_order=a["to_order"])
        self.pp = pp

    # ------------------------------------------------------------------ 3. procure-to-pay
    def procure(self):
        self.c.run_doc_method(self.c.get("Production Plan", self.pp["name"]), "make_material_request")
        rows = self.c.get_list("Material Request",
                               filters=[["Material Request Item", "production_plan", "=", self.pp["name"]]])
        for mr in {r["name"]: r for r in rows}.values():   # one row per matching child line
            self.c.submit("Material Request", mr["name"])
            items = self.c.get("Material Request", mr["name"])["items"]
            self.log("material_request", name=mr["name"], lines=len(items),
                     items=", ".join(f"{i['item_code']}×{i['qty']:g}" for i in items))

            # One PO per default supplier, built by ERPNext's MR->PO mapper
            by_supplier = defaultdict(list)
            for i in items:
                sup = self.c.get("Item", i["item_code"])["item_defaults"][0]["default_supplier"]
                by_supplier[sup].append(i["item_code"])
            for sup, codes in by_supplier.items():
                po = self.c.map_doc(M["mr_to_po"], mr["name"])
                po["supplier"] = sup
                po["items"] = [i for i in po["items"] if i["item_code"] in codes]
                for i in po["items"]:
                    i["rate"] = self.price(i["item_code"], "Standard Buying")
                po = self.c.insert_submit("Purchase Order", po)
                self.log("purchase_order", name=po["name"], supplier=sup, value=po["grand_total"],
                         items=", ".join(f"{i['item_code']}×{i['qty']:g}" for i in po["items"]))

                pr = self.c.insert_submit("Purchase Receipt", self.c.map_doc(M["po_to_pr"], po["name"]))
                self.log("purchase_receipt", name=pr["name"], against=po["name"], warehouse=WH_STORES)
                pi = self.c.map_doc(M["pr_to_pi"], pr["name"])
                pi["bill_no"], pi["bill_date"] = f"INV-{sup[:4].upper()}-{po['name'][-3:]}", TODAY
                pi = self.c.insert_submit("Purchase Invoice", pi)
                self.log("purchase_invoice", name=pi["name"], against=pr["name"], value=pi["grand_total"])

    # ------------------------------------------------------------------ 4. manufacturing
    def manufacture(self):
        self.c.run_doc_method(self.c.get("Production Plan", self.pp["name"]), "make_work_order")
        wos = self.c.get_list("Work Order", filters={"production_plan": self.pp["name"]},
                              fields=["name", "production_item", "qty"])
        # Sub-assemblies first: drones consume them.
        wos.sort(key=lambda w: (not w["production_item"].startswith("SA-"), w["name"]))
        for wo in wos:
            is_sub = wo["production_item"].startswith("SA-")
            self.c.update("Work Order", wo["name"], {"wip_warehouse": WH_WIP, "source_warehouse": WH_STORES,
                                                     "fg_warehouse": WH_STORES if is_sub else WH_FG})
            self.c.submit("Work Order", wo["name"])
            for purpose in ("Material Transfer for Manufacture", "Manufacture"):
                se = self.c.call_json(M["wo_entry"], work_order_id=wo["name"], purpose=purpose, qty=wo["qty"])
                se = self.c.insert_submit("Stock Entry", se)
                if purpose == "Manufacture":
                    fg = next(i for i in self.c.get("Stock Entry", se["name"])["items"] if i.get("is_finished_item"))
                    self.log("work_order", name=wo["name"], item=wo["production_item"], qty=wo["qty"],
                             entry=se["name"], unit_cost=round(fg["valuation_rate"], 2))

    # ------------------------------------------------------------------ 5. order-to-cash
    def deliver_and_bill(self):
        for so in self.trail["sales_order"]:
            dn = self.c.map_doc(M["so_to_dn"], so["name"])
            for i in dn["items"]:
                i["warehouse"] = WH_FG
            dn = self.c.insert_submit("Delivery Note", dn)
            self.log("delivery_note", name=dn["name"], against=so["name"], customer=so["customer"])
            si = self.c.insert_submit("Sales Invoice", self.c.map_doc(M["dn_to_si"], dn["name"]))
            self.log("sales_invoice", name=si["name"], against=dn["name"], value=si["grand_total"])
            so["invoice"] = si["name"]

        first = self.trail["sales_order"][0]          # SunGrid pays on delivery
        pe = self.c.call_json(M["payment"], dt="Sales Invoice", dn=first["invoice"])
        pe.update({"reference_no": "NEFT-SG-20261008", "reference_date": TODAY})
        pe = self.c.insert_submit("Payment Entry", pe)
        self.log("payment_entry", name=pe["name"], against=first["invoice"], amount=pe["paid_amount"])

    # ------------------------------------------------------------------ 6. reorder automation (BR-03)
    def reorder_check(self):
        """After builds, some stock sits below reorder level; ERPNext's scheduler job should react."""
        below = []
        for it in self.c.get_list("Item", filters={"item_group": "Components"}, fields=["name"]):
            item = self.c.get("Item", it["name"])
            for rl in item.get("reorder_levels", []):
                qty = self.stock(it["name"], rl["warehouse"])
                if qty < rl["warehouse_reorder_level"]:
                    below.append((it["name"], qty, rl["warehouse_reorder_level"]))
        for code, qty, level in below:
            self.log("below_reorder_level", item=code, on_hand=qty, reorder_level=level)

    def run(self):
        for step in (self.sales_orders, self.production_plan, self.procure, self.manufacture,
                     self.deliver_and_bill, self.reorder_check):
            print(f"== {step.__name__}")
            step()
        TRAIL_FILE.parent.mkdir(parents=True, exist_ok=True)
        TRAIL_FILE.write_text(json.dumps(self.trail, indent=1, default=str))
        print(f"trail: {TRAIL_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    Cycle(ERPClient()).run()
