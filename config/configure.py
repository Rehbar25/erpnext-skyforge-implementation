"""Phase 2: configure ERPNext for SkyForge Drones.

Idempotent: safe to re-run. Every setting maps back to a business requirement (BR-xx)
in docs/01_requirements.md.

Run:  python -m config.configure
"""

import json

from erp.client import ERPClient

COMPANY = "SkyForge Drones Pvt Ltd"
ABBR = "SFD"
WH_STORES, WH_WIP, WH_FG = f"Stores - {ABBR}", f"Work In Progress - {ABBR}", f"Finished Goods - {ABBR}"

SETUP_ARGS = {
    "language": "English", "country": "India", "timezone": "Asia/Kolkata", "currency": "INR",
    "full_name": "Rehbar Khan", "email": "consultant@skyforge.example", "password": "admin",
    "company_name": COMPANY, "company_abbr": ABBR, "chart_of_accounts": "Standard",
    "fy_start_date": "2026-04-01", "fy_end_date": "2027-03-31", "setup_demo": 0,
}

ITEM_GROUPS = ["Components", "Sub Assemblies", "Products"]
SUPPLIER_GROUPS = ["Import Distributor", "Domestic Manufacturer"]
MARKET_SEGMENTS = ["Solar", "Infrastructure", "Survey", "Agriculture"]

# Role-based users: each department gets only the roles its process needs.
USERS = [
    ("stores@skyforge.example", "Ramesh", "Store Keeper", ["Stock User", "Item Manager"]),
    ("purchase@skyforge.example", "Priya", "Purchase", ["Purchase User", "Purchase Manager", "Stock User"]),
    ("production@skyforge.example", "Arjun", "Production Head", ["Manufacturing User", "Manufacturing Manager", "Stock User"]),
    ("sales@skyforge.example", "Fatima", "Sales", ["Sales User", "Sales Manager"]),
]
DEMO_PASSWORD = "SkyForge@2026"


def log(msg):
    print(f"  {msg}")


def run_setup_wizard(c):
    if c.call("frappe.client.get_single_value", doctype="System Settings", field="setup_complete"):
        log("setup wizard: already complete")
        return
    c.call_post("frappe.desk.page.setup_wizard.setup_wizard.setup_complete", args=json.dumps(SETUP_ARGS))
    log(f"setup wizard: created company {COMPANY}")


def ensure(c, doctype, name, doc):
    _, created = c.upsert(doctype, name, doc)
    log(f"{doctype}: {name} {'created' if created else 'updated'}")


def configure_masters(c):
    for g in ITEM_GROUPS:                                     # BR-01
        ensure(c, "Item Group", g, {"item_group_name": g, "parent_item_group": "All Item Groups"})
    for g in SUPPLIER_GROUPS:
        ensure(c, "Supplier Group", g, {"supplier_group_name": g, "parent_supplier_group": "All Supplier Groups"})
    for s in MARKET_SEGMENTS:
        ensure(c, "Market Segment", s, {"market_segment": s})


def configure_settings(c):
    c.set_single("System Settings", {"enable_scheduler": 1})  # needed for reorder automation
    c.set_single("Stock Settings", {                          # BR-01, BR-02, BR-03
        "item_naming_by": "Item Code",
        "default_warehouse": WH_STORES,
        "stock_uom": "Nos",
        "valuation_method": "FIFO",
        "allow_negative_stock": 0,
        "auto_indent": 1,                # raise Material Requests when stock < reorder level
    })
    c.set_single("Buying Settings", {                         # BR-04
        "supp_master_name": "Supplier Name",
        "po_required": "Yes",            # no receipt/invoice without an approved PO
        "pr_required": "No",
        "maintain_same_rate": 1,
    })
    c.set_single("Selling Settings", {                        # BR-05
        "cust_master_name": "Customer Name",
        "so_required": "Yes",            # every delivery traces back to a sales order
    })
    c.set_single("Manufacturing Settings", {                  # BR-08, BR-09
        "backflush_raw_materials_based_on": "BOM",
        "update_bom_costs_automatically": 1,
        "overproduction_percentage_for_work_order": 0,
    })
    log("stock / buying / selling / manufacturing settings applied")


def configure_users(c):
    for email, first, dept, roles in USERS:
        doc = {"email": email, "first_name": first, "last_name": f"({dept})", "user_type": "System User",
               "send_welcome_email": 0, "new_password": DEMO_PASSWORD,
               "roles": [{"role": r} for r in roles]}
        if c.exists("User", email):
            doc.pop("new_password")
        ensure(c, "User", email, doc)


def main():
    c = ERPClient()
    print("== Setup wizard");  run_setup_wizard(c)
    print("== Master groups");  configure_masters(c)
    print("== Module settings");  configure_settings(c)
    print("== Users & roles");  configure_users(c)
    print("Done.")


if __name__ == "__main__":
    main()
