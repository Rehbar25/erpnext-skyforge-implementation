"""Generate docs/03_business_cycle_results.md from the business-cycle trail + live ERPNext data.

Run after `python -m scenarios.business_cycle` (and the reorder job, see README).
"""

import json
from collections import defaultdict

from erp.client import ERPClient
from scenarios.business_cycle import ROOT, TRAIL_FILE

OUT = ROOT / "docs" / "03_business_cycle_results.md"


def inr(v):
    return f"₹{v:,.0f}"


def main():
    t = json.loads(TRAIL_FILE.read_text())
    c = ERPClient()
    L = ["# Business Cycle Results: First Month of Operations", "",
         "Generated from an end-to-end run against ERPNext v16 "
         "([`scenarios/business_cycle.py`](../scenarios/business_cycle.py)). Every document below exists "
         "in the system; names are ERPNext document IDs.", ""]

    # 1. demand
    L += ["## 1. Customer demand (Sales Orders)", "", "| Sales Order | Customer | Model | Qty | Value | Delivery |",
          "|---|---|---|---|---|---|"]
    L += [f"| {s['name']} | {s['customer']} | {s['item']} | {s['qty']} | {inr(s['value'])} | {s['delivery']} |"
          for s in t["sales_order"]]
    L += [f"| | | | **{sum(s['qty'] for s in t['sales_order'])}** | "
          f"**{inr(sum(s['value'] for s in t['sales_order']))}** | |", ""]

    # 2. MRP
    pp = t["production_plan"][0]
    L += ["## 2. Planning (Production Plan / MRP)", "",
          f"Production Plan **{pp['name']}** pulled all open sales orders and exploded the multi-level BOMs.", "",
          "**Step 1: net finished goods on hand.** ERPNext plans gross sales-order quantity, so the planner nets "
          "existing finished stock first:", "",
          "| Sales Order | Model | Demand | From FG stock | To build |", "|---|---|---|---|---|"]
    L += [f"| {n['sales_order']} | {n['item']} | {n['demand']:g} | {n['from_fg_stock']:g} | {n['to_build']:g} |"
          for n in t["mrp_netting"]]
    L += ["", f"**Step 2: sub-assemblies scheduled:** {pp['sub_assemblies']}", "",
          "**Step 3: component requirements vs projected stock** (shortages in bold):", "",
          "| Component | Required | Projected available | To order |", "|---|---|---|---|"]
    for r in sorted(t["mrp_requirement"], key=lambda r: -r["to_order"]):
        b = "**" if r["to_order"] else ""
        L.append(f"| {b}{r['item']}{b} | {r['required']:g} | {r['available']:g} | {b}{r['to_order']:g}{b} |")
    short = [r for r in t["mrp_requirement"] if r["to_order"]]
    L += ["", f"Result: {len(t['mrp_requirement'])} components checked, **{len(short)} shortages**, both on "
          "the 28-day import supplier. Under the old process these were discovered at the assembly bench.", ""]

    # 3. P2P
    L += ["## 3. Procure-to-Pay", "", "| Step | Document | Detail |", "|---|---|---|"]
    for mr in t["material_request"]:
        L.append(f"| Material Request (from MRP) | {mr['name']} | {mr['items']} |")
    for po, pr, pi in zip(t["purchase_order"], t["purchase_receipt"], t["purchase_invoice"]):
        L += [f"| Purchase Order | {po['name']} | {po['supplier']}: {po['items']}, {inr(po['value'])} |",
              f"| Purchase Receipt | {pr['name']} | Received into {pr['warehouse']} against {pr['against']} |",
              f"| Purchase Invoice | {pi['name']} | {inr(pi['value'])}, 3-way matched to PO and receipt |"]
    L.append("")

    # 4. manufacturing + costing
    L += ["## 4. Manufacturing", "",
          "Sub-assemblies are built first (Stores → WIP → Stores), then drones (Stores → WIP → Finished Goods). "
          "Components are back-flushed per BOM.", "",
          "| Work Order | Item | Qty | Manufacture entry | Actual unit cost |", "|---|---|---|---|---|"]
    L += [f"| {w['name']} | {w['item']} | {w['qty']:g} | {w['entry']} | {inr(w['unit_cost'])} |" for w in t["work_order"]]
    L.append("")

    unit_cost = {w["item"]: w["unit_cost"] for w in t["work_order"]}
    price = {s["item"]: s["value"] / s["qty"] for s in t["sales_order"]}
    L += ["## 5. Product costing & margin (pain point 3)", "",
          "| Model | Selling price | Actual material cost | Gross margin | Margin % |", "|---|---|---|---|---|"]
    for m in sorted(price):
        L.append(f"| {m} | {inr(price[m])} | {inr(unit_cost[m])} | {inr(price[m] - unit_cost[m])} | "
                 f"**{(price[m] - unit_cost[m]) / price[m]:.1%}** |")
    q, x = ((price[m] - unit_cost[m]) / price[m] for m in ("SF-Q250", "SF-X450"))
    cam_share = 38000 / unit_cost["SF-X450"]
    L += ["", f"The SF-X450's margin is {(q - x) * 100:.1f} points below the SF-Q250's, confirming "
          f"management's suspicion with data. {cam_share:.0%} of its cost is the mapping camera, so supplier "
          "negotiation there has the most leverage.", ""]

    # 5. O2C
    L += ["## 6. Order-to-Cash", "", "| Sales Order | Delivery Note | Sales Invoice | Value | Payment |",
          "|---|---|---|---|---|"]
    pays = {p["against"]: p for p in t["payment_entry"]}
    for so, dn, si in zip(t["sales_order"], t["delivery_note"], t["sales_invoice"]):
        pay = pays.get(si["name"])
        L.append(f"| {so['name']} | {dn['name']} | {si['name']} | {inr(si['value'])} | "
                 f"{pay['name'] + ' (received)' if pay else 'outstanding'} |")
    L.append("")

    # 6. reorder automation
    auto = c.get_list("Material Request", filters={"auto_created_via_reorder": 1}, fields=["name"])
    mr = c.get("Material Request", auto[0]["name"]) if auto else None
    L += ["## 7. Reorder automation (BR-03)", "",
          f"After production, ERPNext's scheduled reorder job found "
          f"{len(mr['items']) if mr else 'the'} components at or below reorder level and raised "
          f"{'**' + mr['name'] + '**' if mr else '*(job not yet run)*'} automatically. Required-by dates follow "
          "each item's supplier lead time:", ""]
    if mr:
        by_date = defaultdict(list)
        for i in mr["items"]:
            by_date[i["schedule_date"]].append(f"{i['item_code']}×{i['qty']:g}")
        L += ["| Required by | Items |", "|---|---|"]
        L += [f"| {d} | {', '.join(v)} |" for d, v in sorted(by_date.items())]
        L += ["", f"Value of auto-raised request: {inr(sum(i['amount'] for i in mr['items']))}. Purchase reviews "
              "it and converts it to POs, so no one has to spot low stock by eye or chase suppliers on WhatsApp.", ""]

    OUT.write_text("\n".join(L))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
