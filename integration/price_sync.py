"""BR-11: sync AeroParts' quarterly price list (SOAP) into ERPNext.

  1. Fetch the price list from the supplier's SOAP service (zeep, WSDL-driven).
  2. Map supplier part numbers to SkyForge items (Item -> Supplier Items table, set during migration).
  3. Apply business controls:
       - change above +/-25% is held for purchase-manager approval, not applied
       - unknown part numbers and non-INR currency are logged and skipped
       - items missing from the feed keep their last price
  4. Update Standard Buying prices and item lead times, then roll costs up through the BOMs.
  5. Leave an audit comment on the Supplier record and write a sync report.

If the supplier service is down, nothing changes in ERPNext (last known prices stay) and the
job exits non-zero so the scheduler or monitoring flags it.

Run:  python -m integration.price_sync [--wsdl URL] [--dry-run]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from zeep import Client
from zeep.exceptions import Fault, TransportError

from erp.client import ERPClient

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "docs" / "05_price_sync_report.md"
SUPPLIER = "AeroParts Imports Ltd"
ACCOUNT_ID = "SKYF-0042"
DEFAULT_WSDL = "http://127.0.0.1:8765/PartnerPriceService?wsdl"
PRICE_LIST = "Standard Buying"
MAX_AUTO_CHANGE = 0.25


def fetch_price_list(wsdl, account_id=ACCOUNT_ID):
    resp = Client(wsdl).service.GetPriceList(accountId=account_id)
    return resp.priceListId, [{"part_no": ln.partNo, "description": ln.description,
                               "price": float(ln.unitPrice), "currency": ln.currency,
                               "lead_days": ln.leadTimeDays, "valid_from": str(ln.validFrom)}
                              for ln in (resp.line or [])]


def plan_updates(lines, part_map, current):
    """Pure decision logic (unit-tested).

    part_map: supplier part no -> item code; current: item code -> {"price", "lead_days"}.
    Returns a list of actions: apply | hold | unchanged | unmapped | rejected | missing_from_feed.
    """
    actions, seen = [], set()
    for ln in lines:
        item = part_map.get(ln["part_no"])
        if not item:
            actions.append({"action": "unmapped", "part_no": ln["part_no"], "new_price": ln["price"],
                            "reason": "Part number not linked to any SkyForge item"})
            continue
        seen.add(item)
        cur = current[item]
        a = {"item": item, "part_no": ln["part_no"], "old_price": cur["price"], "new_price": ln["price"],
             "old_lead": cur["lead_days"], "new_lead": ln["lead_days"], "valid_from": ln["valid_from"]}
        if ln["currency"] != "INR":
            a.update(action="rejected", reason=f"Currency {ln['currency']} not supported")
        elif ln["price"] <= 0:
            a.update(action="rejected", reason="Non-positive price")
        else:
            change = (ln["price"] - cur["price"]) / cur["price"] if cur["price"] else 1.0
            a["change"] = change
            if abs(change) > MAX_AUTO_CHANGE:
                a.update(action="hold", reason=f"{change:+.1%} exceeds ±{MAX_AUTO_CHANGE:.0%} auto-approve limit")
            elif change == 0 and ln["lead_days"] == cur["lead_days"]:
                a.update(action="unchanged")
            else:
                a.update(action="apply")
        actions.append(a)
    for item in sorted(set(part_map.values()) - seen):
        actions.append({"action": "missing_from_feed", "item": item, "old_price": current[item]["price"],
                        "reason": "Not on supplier's current list; last price kept"})
    return actions


class PriceSync:
    def __init__(self, c: ERPClient):
        self.c = c

    def read_erp_state(self):
        rows = self.c.get_list("Item", filters=[["Item Supplier", "supplier", "=", SUPPLIER]])
        part_map, current = {}, {}
        for code in sorted({r["name"] for r in rows}):
            item = self.c.get("Item", code)
            for s in item["supplier_items"]:
                if s["supplier"] == SUPPLIER and s.get("supplier_part_no"):
                    part_map[s["supplier_part_no"]] = code
            price = self.c.get_list("Item Price", filters={"item_code": code, "price_list": PRICE_LIST},
                                    fields=["name", "price_list_rate"])
            current[code] = {"price": price[0]["price_list_rate"], "price_doc": price[0]["name"],
                             "lead_days": item["lead_time_days"]}
        return part_map, current

    def bom_costs(self):
        return {b["item"]: b["total_cost"] for b in self.c.get_list(
            "BOM", filters={"is_default": 1, "docstatus": 1}, fields=["item", "total_cost"])}

    def apply(self, actions, current):
        for a in actions:
            if a["action"] != "apply":
                continue
            self.c.update("Item Price", current[a["item"]]["price_doc"],
                          {"price_list_rate": a["new_price"], "valid_from": a["valid_from"]})
            if a["new_lead"] != a["old_lead"]:
                self.c.update("Item", a["item"], {"lead_time_days": a["new_lead"]})
        # Roll new prices up: sub-assembly BOMs first, update_parent propagates to the drones.
        boms = self.c.get_list("BOM", filters={"is_default": 1, "docstatus": 1}, fields=["name", "item"])
        for b in sorted(boms, key=lambda b: not b["item"].startswith("SA-")):
            self.c.run_doc_method(self.c.get("BOM", b["name"]), "update_cost",
                                  update_parent=True, from_child_bom=False, update_hour_rate=False, save=True)

    def audit_comment(self, price_list_id, actions):
        counts = {k: sum(a["action"] == k for a in actions) for k in ("apply", "hold", "unmapped")}
        self.c.insert("Comment", {
            "comment_type": "Comment", "reference_doctype": "Supplier", "reference_name": SUPPLIER,
            "content": f"Price sync {price_list_id}: {counts['apply']} prices updated, {counts['hold']} held "
                       f"for approval, {counts['unmapped']} unmapped part numbers. See price sync report."})


def write_report(price_list_id, actions, before, after, error=None, dry_run=False):
    L = ["# Supplier Price Sync Report (AeroParts SOAP → ERPNext)", "",
         f"**Run:** {datetime.now():%Y-%m-%d %H:%M} · **Supplier:** {SUPPLIER} · "
         f"**Price list:** {price_list_id or 'n/a'} · **Mode:** {'dry run' if dry_run else 'live'}", ""]
    if error:
        L += [f"**Sync failed:** {error}", "", "No changes were made in ERPNext; last known prices remain in effect."]
        REPORT.write_text("\n".join(L) + "\n")
        return
    label = {"apply": "✅ Applied", "hold": "⏸ Held for approval", "unchanged": "No change",
             "unmapped": "⚠ Unmapped", "rejected": "❌ Rejected", "missing_from_feed": "Kept last price"}
    L += ["## Line-by-line decisions", "", "| Item | Supplier part | Old ₹ | New ₹ | Change | Lead time | Result |",
          "|---|---|---|---|---|---|---|"]
    for a in actions:
        old = f"{a['old_price']:,.0f}" if a.get("old_price") is not None else "n/a"
        new = f"{a['new_price']:,.0f}" if a.get("new_price") is not None else "n/a"
        lead = f"{a['old_lead']} → {a['new_lead']} d" if a.get("new_lead") not in (None, a.get("old_lead")) \
            else (f"{a['old_lead']} d" if a.get("old_lead") else "")
        res = label[a["action"]] + (f": {a['reason']}" if a.get("reason") else "")
        chg = f"{a['change']:+.1%}" if "change" in a else ""
        L.append(f"| {a.get('item', '')} | {a.get('part_no', '')} | {old} | {new} | {chg} | {lead} | {res} |")
    if after:
        L += ["", "## Impact on product cost (BOM roll-up)", "",
              "| BOM item | Cost before | Cost after | Δ |", "|---|---|---|---|"]
        for item in sorted(before):
            d = after[item] - before[item]
            L.append(f"| {item} | ₹{before[item]:,.0f} | ₹{after[item]:,.0f} | {'+' if d >= 0 else ''}₹{d:,.0f} |")
        sell = {"SF-Q250": 68000, "SF-X450": 145000}
        L += ["", "| Model | Margin before | Margin after |", "|---|---|---|"]
        for m, p in sell.items():
            L.append(f"| {m} | {(p - before[m]) / p:.1%} | {(p - after[m]) / p:.1%} |")
    held = [a for a in actions if a["action"] == "hold"]
    if held:
        L += ["", "## Action required", ""] + [
            f"- **{a['item']}**: supplier quotes ₹{a['new_price']:,.0f} vs ₹{a['old_price']:,.0f} "
            f"({a['change']:+.0%}). Purchase manager to confirm with AeroParts before approving." for a in held]
    REPORT.write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wsdl", default=DEFAULT_WSDL)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    try:
        price_list_id, lines = fetch_price_list(args.wsdl)
    except (Fault, TransportError, OSError) as e:
        write_report(None, [], {}, {}, error=f"{type(e).__name__}: {e}")
        print(f"price sync FAILED, no changes made: {e}")
        sys.exit(1)

    c = ERPClient()
    sync = PriceSync(c)
    part_map, current = sync.read_erp_state()
    actions = plan_updates(lines, part_map, current)
    before = sync.bom_costs()
    after = {}
    if not args.dry_run:
        sync.apply(actions, current)
        sync.audit_comment(price_list_id, actions)
        after = sync.bom_costs()
    write_report(price_list_id, actions, before, after, dry_run=args.dry_run)
    summary = {k: sum(a["action"] == k for a in actions) for k in
               ("apply", "hold", "unchanged", "unmapped", "missing_from_feed")}
    print(f"price sync {price_list_id}: {summary}; report: {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
