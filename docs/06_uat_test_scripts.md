# User Acceptance Test (UAT) Scripts & Results

**Client:** SkyForge Drones Pvt Ltd · **System:** ERPNext v16 · **Cycle:** UAT-1
**Prepared by:** Rehbar Khan · **Testers:** Ramesh (Stores), Priya (Purchase), Arjun (Production), Fatima (Sales)

Each case is written as steps a business user follows in the ERPNext screens. Every case also has an
automated equivalent in [`tests/test_live_uat.py`](../tests/test_live_uat.py) that runs against the
same system, so results can be re-checked after any configuration change.

**Result: 14 / 14 passed.** Negative tests (UAT-03, 04, 05, 14) confirm that the system *blocks*
the wrong action, with the error message shown below.

---

## Summary

| ID | Requirement | Process | Tester | Result |
|---|---|---|---|---|
| UAT-01 | BR-01, BR-10 | Migrated master data matches signed-off source | Ramesh | ✅ Pass |
| UAT-02 | BR-06 | Multi-level BOM structure | Arjun | ✅ Pass |
| UAT-03 | BR-04 | Goods cannot be received without a PO | Ramesh | ✅ Pass |
| UAT-04 | BR-05 | Goods cannot be shipped without a Sales Order | Fatima | ✅ Pass |
| UAT-05 | BR-02 | Stock cannot go negative | Ramesh | ✅ Pass |
| UAT-06 | BR-07 | MRP orders only the shortfall | Priya | ✅ Pass |
| UAT-07 | BR-04 | Procure-to-Pay completes (PO → receipt → invoice) | Priya | ✅ Pass |
| UAT-08 | BR-08 | Work orders consume components and produce drones | Arjun | ✅ Pass |
| UAT-09 | BR-05 | Order-to-Cash completes (SO → delivery → invoice → payment) | Fatima | ✅ Pass |
| UAT-10 | BR-09 | Actual product cost equals BOM cost | Arjun | ✅ Pass |
| UAT-11 | BR-03 | Reorder request raised automatically | Priya | ✅ Pass |
| UAT-12 | BR-11 | Supplier price sync applies changes within controls | Priya | ✅ Pass |
| UAT-13 | BR-12 | Website order arrives as a draft Sales Order | Fatima | ✅ Pass |
| UAT-14 | Security | Store keeper cannot raise purchase orders | Ramesh | ✅ Pass |

---

## Test cases

### UAT-01 · Migrated master data reconciles to source
- **Steps:** Open the [migration reconciliation report](04_migration_reconciliation.md). In ERPNext, open
  *Item List*, *Supplier List*, *Customer List*, *BOM List* and the *Stock Balance* report.
- **Expected:** 29 items, 6 suppliers, 7 customers (each with a billing address), 6 submitted default BOMs,
  24 opening stock lines; opening stock value ₹9,07,833. Every source row is either loaded or appears in
  the exception log with a resolution.
- **Actual:** As expected; all verification checks passed. · `test_uat01_migration_reconciles`

### UAT-02 · Multi-level BOM
- **Steps:** Open *BOM* for SF-Q250 → check the Items table.
- **Expected:** Contains sub-assemblies SA-FRM-Q250 and SA-PWR-Q250, each linked to its own BOM.
- **Actual:** As expected. · `test_uat02_multilevel_bom`

### UAT-03 · Receipt without PO is blocked (negative)
- **Steps:** *Purchase Receipt → New*. Supplier VoltCell Energy, item BAT-4S1500 × 5, no PO. Submit.
- **Expected:** Rejected with *"Purchase Order number required for Item BAT-4S1500"*.
- **Actual:** Rejected with that message; no document created. · `test_uat03_receipt_without_po_rejected`

### UAT-04 · Delivery without Sales Order is blocked (negative)
- **Steps:** *Delivery Note → New*. Customer TerraMap Surveys, SF-Q250 × 1, no SO. Submit.
- **Expected:** Rejected with *"Sales Order required for Item SF-Q250"*.
- **Actual:** As expected. · `test_uat04_delivery_without_sales_order_rejected`

### UAT-05 · Negative stock is blocked (negative)
- **Steps:** *Stock Entry → New*, type Material Issue, CAM-MAP × 500 from Stores. Submit.
- **Expected:** Rejected: quantity needed in *Stores - SFD* exceeds stock on hand.
- **Actual:** As expected. · `test_uat05_negative_stock_blocked`

### UAT-06 · MRP orders only the shortfall
- **Pre-condition:** Sales orders for 10 × SF-Q250 and 2 × SF-X450; 2 × SF-Q250 already in Finished Goods.
- **Steps:** *Production Plan → New* → Get Sales Orders → Get Finished Goods → reduce SF-Q250 by stock on
  hand → Get Sub Assembly Items → **tick "Consider Projected Qty in Calculation (RM)"** → Get Raw Materials
  for Purchase → Submit → Create Material Request.
- **Expected:** One Material Request for **ESC-30A × 14** and **GPS-M10 × 4** only (hand-calculated:
  ESC need 32, have 18; GPS need 10, have 6). The other 21 components are covered by stock.
- **Actual:** As expected. See [business cycle results §2](03_business_cycle_results.md). ·
  `test_uat06_mrp_orders_only_the_shortfall`

### UAT-07 · Procure-to-Pay
- **Steps:** Material Request → *Create → Purchase Order* (AeroParts) → Submit → *Create → Purchase Receipt*
  → Submit → *Create → Purchase Invoice* (enter supplier bill no.) → Submit.
- **Expected:** PO shows 100% received and 100% billed; stock of ESC-30A/GPS-M10 increases in Stores.
- **Actual:** As expected. · `test_uat07_procure_to_pay_complete`

### UAT-08 · Manufacturing
- **Steps:** From the Production Plan → *Create → Work Order*. For each work order, sub-assemblies first:
  Submit → *Start* (transfer to WIP) → *Finish* (manufacture).
- **Expected:** 9 work orders completed; sub-assemblies land in Stores, drones in Finished Goods; components
  consumed per BOM.
- **Actual:** As expected. · `test_uat08_work_orders_completed`

### UAT-09 · Order-to-Cash
- **Steps:** For each Sales Order: *Create → Delivery Note* → Submit → *Create → Sales Invoice* → Submit.
  For SunGrid's invoice: *Create → Payment* (NEFT reference) → Submit.
- **Expected:** 3 sales orders 100% delivered and billed; SunGrid invoice outstanding = ₹0.
- **Actual:** As expected. · `test_uat09_order_to_cash_complete`

### UAT-10 · Product cost
- **Steps:** Open the *Manufacture* stock entries for SF-Q250 and SF-X450 → check the finished item's
  valuation rate. Compare with BOM total cost.
- **Expected:** SF-Q250 ₹41,419, SF-X450 ₹99,486, equal to BOM cost at the time of production.
- **Actual:** As expected. Margins: SF-Q250 39.1%, SF-X450 31.4%. · `test_uat10_actual_cost_matches_bom`

### UAT-11 · Reorder automation
- **Steps:** After production, wait for the daily scheduler (or run *reorder_item* in UAT). Open
  *Material Request List*, filter "Auto created via reorder".
- **Expected:** One auto-created Material Request including CAM-4K, ESC-30A and GPS-M10, with required-by
  dates based on each item's lead time.
- **Actual:** As expected (18 lines). · `test_uat11_reorder_request_auto_raised`

### UAT-12 · Supplier price sync
- **Steps:** Run the price sync job. Open *Item Price* for ESC-30A and FC-H7, *Item* ESC-30A
  (Lead Time), *BOM* SF-Q250, and the comments on Supplier *AeroParts Imports Ltd*.
- **Expected:** ESC-30A ₹950 → ₹1,020, lead time 28 → 35 days; FC-H7 **unchanged** at ₹11,500 (the +47%
  quote is held for approval); SF-Q250 BOM cost ₹41,699; audit comment on the supplier.
- **Actual:** As expected. See [price sync report](05_price_sync_report.md). ·
  `test_uat12_price_sync_applied_with_controls`

### UAT-13 · Website order intake
- **Steps:** Submit an order for 3 × SF-Q250 on the website (Coastal Wind Energy's GSTIN); submit again
  (simulated retry). Open *Sales Order List*.
- **Expected:** Exactly one **Draft** Sales Order (₹2,04,000) for Coastal Wind Energy with reference
  `WEB:WEB-2026-0045`; the retry returns the same order.
- **Actual:** As expected. · `test_uat13_web_order_lands_as_draft`

### UAT-14 · Role-based access (negative)
- **Steps:** Log in as `stores@skyforge.example` → *Purchase Order → New* → Save.
- **Expected:** Not permitted: store keepers receive goods but do not commit company money.
- **Actual:** Rejected (*"does not have doctype access via role permission"*). ·
  `test_uat14_store_keeper_cannot_raise_purchase_orders`

---

## Sign-off

| Role | Name | Decision | Date |
|---|---|---|---|
| Production Head | Arjun | | |
| Purchase | Priya | | |
| Managing Director (sponsor) | | Go / No-go | |
