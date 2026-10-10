"""Run the data migration: cleanse -> (load -> verify) -> reconciliation report.

  python -m migration.run --dry-run          cleanse only, report what would load
  python -m migration.run                    full migration into ERPNext
  python -m migration.run --no-decisions     first-pass view: what needs client decisions
"""

import argparse
import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

from migration.cleanse import cleanse, load_decisions

ROOT = Path(__file__).resolve().parent.parent
WORKBOOK = ROOT / "data" / "legacy" / "SkyForge_Master_Data.xlsx"
DECISIONS = ROOT / "migration" / "decisions.json"
REPORT = ROOT / "docs" / "04_migration_reconciliation.md"
EXCEPTION_LOG = ROOT / "docs" / "04_migration_exception_log.csv"

ENTITY_SHEETS = [("Suppliers", "Suppliers", "suppliers"), ("Items", "Items", "items"),
                 ("Customers", "Customers", "customers"), ("BOM lines", "Parts Lists", None),
                 ("Stock lines", "Stock Count", "stock")]


def resolution_type(res: str) -> str:
    return "OPEN" if res == "OPEN" else res.split(":")[0]


def not_migrated(e) -> bool:
    """Row intentionally left out: excluded outright or rejected by client decision."""
    return e.resolution.startswith("excluded") or "rejected" in e.resolution


def write_exception_log(data, path):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "sheet", "row", "field", "value", "issue", "resolution"])
        for e in data.exceptions:
            w.writerow([e.id, e.sheet, e.row, e.field, e.value, e.issue, e.resolution])


def build_report(data, results=None, checks=None, dry_run=False) -> str:
    sheet_exc = Counter((e.sheet, resolution_type(e.resolution)) for e in data.exceptions)
    dropped = Counter(e.sheet for e in data.exceptions if not_migrated(e))
    loaded = {"suppliers": len(data.suppliers), "items": len(data.items), "customers": len(data.customers),
              "stock": len(data.stock)}
    bom_lines = sum(len(v) for v in data.boms.values())

    out = ["# Data Migration Reconciliation Report", "",
           f"**Client:** SkyForge Drones Pvt Ltd · **Source:** `{WORKBOOK.name}` · "
           f"**Run:** {datetime.now():%Y-%m-%d %H:%M} · **Mode:** {'dry run' if dry_run else 'load + verify'}", "",
           "## 1. Source to target", "",
           "| Entity | Source rows | Not migrated (duplicate / obsolete / write-off / rejected) | Blocked (OPEN) | Ready to load |",
           "|---|---|---|---|---|"]
    for label, sheet, key in ENTITY_SHEETS:
        ready = bom_lines if key is None else loaded[key]
        out.append(f"| {label} | {data.source_rows[sheet]} | {dropped[sheet]} | "
                   f"{sheet_exc[(sheet, 'OPEN')]} | {ready} |")
    out += ["", "Stock lines are aggregated per item and warehouse, so *Ready to load* counts distinct "
            "item/warehouse pairs.", ""]

    by_type = Counter(resolution_type(e.resolution) for e in data.exceptions)
    out += ["## 2. Data-quality exceptions", "",
            f"{len(data.exceptions)} exceptions raised. Full log: "
            f"[`{EXCEPTION_LOG.name}`]({EXCEPTION_LOG.name}).", "",
            "| Resolution | Count | Meaning |", "|---|---|---|",
            f"| auto-fixed | {by_type['auto-fixed']} | Formatting with exactly one correct answer (units, whitespace, ₹ symbols) |",
            f"| client decision | {by_type['client decision']} | Resolved per signed-off `decisions.json` |",
            f"| excluded | {by_type['excluded']} | Intentionally not migrated |",
            f"| accepted | {by_type['accepted']} | Loaded as-is, follow-up owned by client |",
            f"| **OPEN** | **{by_type['OPEN']}** | **Blocks go-live until decided** |", ""]

    auto = Counter(e.issue for e in data.exceptions if resolution_type(e.resolution) == "auto-fixed")
    out += ["### Auto-fixes by type", "", "| Issue | Rows |", "|---|---|"]
    out += [f"| {issue} | {n} |" for issue, n in auto.most_common()]

    notable = [e for e in data.exceptions if resolution_type(e.resolution) != "auto-fixed"]
    out += ["", "### Decisions, exclusions and open items", "",
            "| ID | Sheet:row | Value | Issue | Resolution |", "|---|---|---|---|---|"]
    out += [f"| {e.id} | {e.sheet}:{e.row} | `{e.value}` | {e.issue} | "
            f"{'**OPEN**' if e.is_open else e.resolution} |" for e in notable]

    if results:
        out += ["", "## 3. Load results", "", "| Object | Created | Updated | Skipped (already loaded) | Failed |",
                "|---|---|---|---|---|"]
        for entity, r in results.items():
            out.append(f"| {entity} | {r['created']} | {r['updated']} | {r['skipped']} | {len(r['failed'])} |")
        failures = [(ent, k, msg) for ent, r in results.items() for k, msg in r["failed"]]
        if failures:
            out += ["", "**Failures:**", ""] + [f"- {ent} `{k}`: {msg}" for ent, k, msg in failures]

    if checks:
        passed = sum(c["ok"] for c in checks)
        out += ["", "## 4. Post-load verification (read back from ERPNext)", "",
                f"**{passed} / {len(checks)} checks passed.**", "",
                "| Check | Expected | In ERPNext | Result |", "|---|---|---|---|"]
        for c in checks:
            exp, act = c["expected"], c["actual"]
            if isinstance(exp, list):
                exp, act = f"{len(exp)} lines", f"{len(act)} lines{' (identical)' if c['ok'] else ''}"
            out.append(f"| {c['check']} | {exp:,} | {act:,} | {'✅' if c['ok'] else '❌'} |"
                       if isinstance(exp, (int, float)) else
                       f"| {c['check']} | {exp} | {act} | {'✅' if c['ok'] else '❌'} |")

    out += ["", "## Sign-off", "", "| Role | Name | Date |", "|---|---|---|",
            "| Store Keeper (stock & items) | Ramesh | |", "| Purchase (suppliers) | Priya | |",
            "| Implementation Consultant | Rehbar Khan | |", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-decisions", action="store_true")
    ap.add_argument("--force-after-go-live", action="store_true")
    args = ap.parse_args()

    decisions = None if args.no_decisions else load_decisions(DECISIONS)
    data = cleanse(WORKBOOK, decisions)
    print(f"cleansed: {len(data.items)} items, {len(data.suppliers)} suppliers, {len(data.customers)} customers, "
          f"{len(data.boms)} BOMs, {len(data.stock)} stock lines; {len(data.exceptions)} exceptions, "
          f"{len(data.open_exceptions)} OPEN")

    results = checks = None
    if not args.dry_run:
        if data.open_exceptions:
            raise SystemExit("Refusing to load: OPEN exceptions need client decisions (run --dry-run to see them).")
        from erp.client import ERPClient
        from migration.load import Loader, verify
        c = ERPClient()
        live = [d for d in ("Sales Invoice", "Purchase Receipt", "Stock Entry")
                if c.get_list(d, filters={"docstatus": 1}, limit=1)]
        if live and not args.force_after_go_live:
            # ISS-09: a re-run after go-live overwrote prices the supplier sync had updated.
            raise SystemExit(f"Refusing to load: system is live ({', '.join(live)} posted). Re-running the "
                             "migration would overwrite live master data. Use --force-after-go-live only "
                             "with the client's written approval.")
        results = Loader(c, data).run()
        checks = verify(c, data)
        print(f"verification: {sum(x['ok'] for x in checks)}/{len(checks)} checks passed")
        for x in checks:
            if not x["ok"]:
                print(f"  FAIL {x['check']}: expected {x['expected']} got {x['actual']}")

    write_exception_log(data, EXCEPTION_LOG)
    REPORT.write_text(build_report(data, results, checks, dry_run=args.dry_run))
    print(f"report: {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
