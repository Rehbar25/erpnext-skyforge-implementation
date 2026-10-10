# Demo Script: 7-Minute Walkthrough

Recorded walkthrough for the portfolio, framed as a **go-live readiness review with the client**.
Screen: ERPNext at `localhost:8080` (logged in as Administrator) + terminal + this repo.

| Time | Show | Say (talking points) |
|---|---|---|
| 0:00 | README (top) | "SkyForge assembles two drone models. Stock lives in Excel, buying happens on WhatsApp, and stock-outs delayed 11 orders last quarter. I ran a full ERPNext implementation for them: requirements to go-live." |
| 0:30 | `docs/01_requirements.md` §5 fit-gap | "12 requirements. 9 are standard ERPNext or configuration. The 3 gaps are all data and integration, so no changes to ERPNext's own code, and they stay upgradeable." |
| 1:00 | ERPNext → **BOM** SF-Q250 (tree view) | "Multi-level BOM: the drone uses a frame kit and a power pack, which are built first. Cost rolls up automatically: ₹41,419." |
| 1:30 | Excel workbook *Items* tab, then `docs/04_migration_reconciliation.md` | "The client's real data: duplicates, 'approx 38k' as a price, six spellings of 'pieces'. My pipeline raised 81 exceptions; formatting fixes ran automatically, anything needing judgement went to the client. Then it reads everything back from ERPNext: 19 of 19 checks." |
| 2:30 | ERPNext → **Production Plan** → *Material Requests* tab | "Three customer orders. MRP explodes the BOMs, nets against stock, and orders only what's short: 14 ESCs and 4 GPS modules, both 4-week imports, ordered on day one. I verified it by hand." *(Mention ISS-02: the v16 flag that made MRP buy everything, and how I caught it.)* |
| 3:15 | **Purchase Order** → Connections (Receipt, Invoice) | "Procure-to-pay with a control: you can't receive goods without a PO." |
| 3:40 | **Work Order List** (all Completed) → a Manufacture **Stock Entry** | "Nine work orders, sub-assemblies first. Actual cost equals BOM cost to the rupee." |
| 4:10 | `docs/03_business_cycle_results.md` §5 | "This answered the MD's question: the X450 makes 31% vs 39% for the Q250, and 38% of its cost is one camera." |
| 4:40 | Terminal: run `integration/price_sync.py`, then `docs/05_price_sync_report.md` | "The import supplier exposes a SOAP service. Quarterly prices sync in, costs recalculate, but a +47% quote is held for a human. The supplier being down changes nothing." |
| 5:30 | Terminal: `tools/sample_web_order.py` → ERPNext **Sales Order** (Draft) | "Website orders come in over REST as drafts, priced by ERPNext, never by the website, and a retry doesn't create a duplicate." |
| 6:00 | `docs/07_status_report.md` | "This is how I'd report it to the MD: plain language, three decisions needed, no jargon." |
| 6:30 | Terminal: `pytest -q` → 60 passed; `run_all.sh` | "Everything is reproducible: one script rebuilds it from an empty system, and 14 UAT cases run as automated tests. That's my mock cutover." |
| 7:00 | | End. |

**Recording tips:** 1080p, zoom browser to 125%, hide bookmarks bar. Rehearse once; keep each segment
under its slot. Upload unlisted to YouTube/Loom and link it at the top of the README.
