# Issue Log

**Client:** SkyForge Drones Pvt Ltd · **Updated:** 2026-10-08

Issues found during build, mock cutover and UAT. Severity: **High** = blocks a business process or
corrupts data · **Medium** = workaround exists · **Low** = cosmetic or environment-only.

| ID | Area | Severity | Status | Owner |
|---|---|---|---|---|
| ISS-01 | Sales | High | Closed | Consultant |
| ISS-02 | Planning | High | Closed | Consultant |
| ISS-03 | Planning | Medium | Closed | Consultant |
| ISS-04 | Planning | Medium | Closed (SOP) | Arjun |
| ISS-05 | Manufacturing | Medium | Closed | Consultant |
| ISS-06 | Integration | Low | Closed | Consultant |
| ISS-07 | Stock | Low | Closed (expected) | Priya |
| ISS-08 | Migration | Medium | Closed | Consultant |
| ISS-09 | Migration | **High** | Closed | Consultant |
| ISS-10 | Master data | Medium | **Open** | Priya |
| ISS-11 | Purchasing | Medium | **Open** | Priya |
| ISS-12 | Purchasing | Medium | **Open** | Priya |
| ISS-13 | Accounting | Medium | Deferred (Phase 2) | MD |
| ISS-14 | Environment | Low | Closed | Consultant |

---

### ISS-01 · Sales Orders created through the API came in at ₹0
- **Found:** Build, first API-created Sales Order (₹0 grand total).
- **Root cause:** Price-list lookup runs in the browser form; documents created via REST skip it.
- **Fix:** The order-intake API and test scripts read the rate from the *Standard Selling* price list
  server-side; the website can never set prices. Covered by UAT-13 (₹2,04,000 for 3 units).

### ISS-02 · MRP proposed buying every component, ignoring stock on hand
- **Found:** Build, first Production Plan run (proposed 42 purchase lines, the gross requirement of every component on all 3 orders, instead of 2).
- **Root cause:** In v16 the field `ignore_existing_ordered_qty` is labelled *"Consider Projected Qty in
  Calculation (RM)"*: the name says the opposite of what it does. When a plan is created through the API it
  defaults to off, so MRP plans gross requirements.
- **Fix:** Set explicitly in the planning script; step added to the planner's SOP and UAT-06. Validated
  against a hand calculation (ESC-30A 32 needed − 18 on hand = 14).

### ISS-03 · Raw-material planner switched to "transfer" mode
- **Root cause:** Passing a warehouse list to the material planner makes ERPNext plan *transfers between
  warehouses* instead of purchases.
- **Fix:** Planner called with the target warehouse only.

### ISS-04 · Production Plan ignores finished drones already on the shelf
- **Impact:** Would build 6 SF-Q250 for SunGrid although 2 were in stock.
- **Resolution:** Standard ERPNext behaviour. The planner subtracts finished-goods stock before planning
  (scripted, and in the SOP). Agreed with Arjun.

### ISS-05 · v16 removed default WIP / Finished Goods warehouses from Manufacturing Settings
- **Fix:** Warehouses set on each Work Order (Stores → WIP → Stores for sub-assemblies; → Finished Goods
  for drones). Documented in the production user guide.

### ISS-06 · Material Request cannot be filtered by Production Plan at header level
- **Fix:** Filter on the item table (`Material Request Item.production_plan`). Integration code only.

### ISS-07 · Reorder job also raised items sitting *exactly* at reorder level
- **Detail:** PDB-200 (4 on hand, level 4) and FRM-X450-ARM (24, level 24) were included.
- **Resolution:** ERPNext reorders at *≤* level. Explained to Priya; levels kept as they are.

### ISS-08 · Migration auto-fix changed a customer's brand name
- **Found:** Client review of the reconciliation report.
- **Detail:** The all-caps name "GREENACRE AGRITECH" was auto-title-cased to "Greenacre Agritech"; the
  registered name is "GreenAcre Agritech".
- **Fix:** All-caps names are now raised as exceptions for a client decision, never auto-fixed. Customer
  renamed in ERPNext (address link preserved). Regression test added.
- **Lesson:** Auto-fix only when there is exactly one correct answer. Names never qualify.

### ISS-09 · Re-running the migration after go-live overwrote live prices
- **Found:** Mock cutover 1. Migration re-run after the supplier price sync reset 4 prices to legacy
  values and made BOM costs inconsistent.
- **Fix:** Migration now detects a live system (posted invoices / receipts / stock entries) and refuses
  to load without `--force-after-go-live`. Environment rebuilt from scratch and all checks re-run.

### ISS-10 · Hyderabad Fasteners' GSTIN fails checksum
- **Status:** Supplier loaded without GSTIN so POs aren't blocked. **Action:** Priya to obtain the correct
  GSTIN before their first invoice is booked. **Due:** T-7.

### ISS-11 · AeroParts quotes FC-H7 at ₹16,900 (+47%)
- **Status:** Held by the price-sync control (±25% auto-approve limit); ERPNext still uses ₹11,500.
  **Action:** Priya to confirm with AeroParts (possible typo vs. real increase). If real, SF-X450 margin
  falls from 30.7% to 26.9%.

### ISS-12 · AeroParts dropped RX-ELRS from its price list
- **Status:** Last price (₹1,200) kept. **Action:** Priya to confirm availability or qualify a second
  source before current stock (10 units after the first cycle) runs out.

### ISS-13 · GST not configured
- **Status:** Deferred. Out of scope for Phase 1 (accounting stays in Tally). Phase 2: install India
  Compliance app, configure GST templates, then retire Tally.

### ISS-14 · Test runner picked up ROS 2 plugins on the consultant's laptop
- **Root cause:** Host `PYTHONPATH` leaked ROS's pytest plugins into the project venv.
- **Fix:** `run_all.sh` unsets `PYTHONPATH`. Environment-only, no client impact.
