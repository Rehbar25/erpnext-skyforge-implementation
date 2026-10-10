# Requirements & Fit-Gap Analysis

**Client:** SkyForge Drones Pvt. Ltd. (fictional client, for portfolio purposes)
**Project:** ERPNext implementation: Inventory, Procurement, Order Management, Manufacturing, Costing
**Prepared by:** Rehbar Khan, Implementation Consultant
**Version:** 1.0 · Status: Draft for client sign-off

---

## 1. Client background

SkyForge Drones is a 25-person company in Hyderabad that assembles and sells two drone models to
industrial customers (solar farms, infrastructure inspection firms, survey agencies):

| Model | Description | Monthly volume | Selling price |
|---|---|---|---|
| **SF-Q250** Inspection Quad | 4-rotor, camera-equipped inspection drone | ~30 units | ₹68,000 |
| **SF-X450** Survey Hex | 6-rotor, longer-endurance mapping drone | ~10 units | ₹1,45,000 |

Each drone is built from ~20 purchased components (motors, ESCs, flight controllers, frames,
batteries, etc.) bought from 6 suppliers, two of which import with 3–5 week lead times.

## 2. Current process ("as-is")

| Area | How it works today | Tool |
|---|---|---|
| Stock tracking | Store keeper updates a shared Excel sheet at end of day | Excel |
| Purchasing | Production head messages suppliers on WhatsApp when stock "looks low" | WhatsApp, Excel |
| Sales orders | Sales team emails order details to production; tracked in a separate sheet | Email, Excel |
| Production | Built from a printed parts list; no formal work orders | Paper |
| Costing | Owner estimates product cost once a year in a spreadsheet | Excel |
| Accounting | Invoices entered separately by an external accountant | Tally |

## 3. Pain points (from stakeholder interviews)

1. **Stock-outs stop the line.** Last quarter, ESC and GPS module stock-outs delayed 11 orders.
   Nobody knew stock was low until assembly started.
2. **No single source of truth.** The stock sheet is regularly 2–3 days behind and has duplicate
   item entries (e.g. "Motor 2306" and "2306 motor 2450KV").
3. **Unknown product cost.** Component prices change with exchange rates, but product cost is
   updated once a year, so margins on the SF-X450 are believed to be thin and nobody can confirm it.
4. **No purchase planning.** Long-lead imported parts are ordered reactively, not from demand.
5. **Order status is invisible.** Sales can't tell a customer when their order will ship.

## 4. Business requirements

| ID | Requirement | Priority | Pain point |
|---|---|---|---|
| BR-01 | Maintain a single, de-duplicated item master with standard units of measure | Must | 2 |
| BR-02 | Track stock in real time across Stores, Work-in-Progress and Finished Goods warehouses | Must | 1, 2 |
| BR-03 | Alert purchasing when a component falls below its reorder level | Must | 1 |
| BR-04 | Raise and approve purchase orders inside the system; receive goods against POs | Must | 4 |
| BR-05 | Record customer sales orders and track them through to delivery | Must | 5 |
| BR-06 | Define multi-level Bills of Materials for both drone models | Must | 3 |
| BR-07 | Plan material requirements from open sales orders, accounting for supplier lead times | Must | 4 |
| BR-08 | Issue work orders and consume components from stock on completion | Must | 1, 3 |
| BR-09 | Calculate product cost automatically from current component purchase prices | Must | 3 |
| BR-10 | Migrate existing items, suppliers, customers, BOMs and opening stock from Excel | Must | 2 |
| BR-11 | Pull latest prices and lead times from the main import supplier's system automatically | Should | 3, 4 |
| BR-12 | Accept sales orders from the website enquiry form without re-keying | Should | 5 |
| BR-13 | Replace Tally with ERPNext accounting | Could | n/a (out of scope, phase 2) |

## 5. Fit-gap analysis (ERPNext v16)

**Fit** = standard functionality · **Config** = met by configuration only ·
**Gap** = needs integration/custom work

| ID | ERPNext solution | Result |
|---|---|---|
| BR-01 | Item master, Item Groups, UOM, item naming rules | Config |
| BR-02 | Warehouses + Stock Ledger; Stores / WIP / FG warehouse structure | Config |
| BR-03 | Item reorder levels + auto Material Request (Stock Settings) | Config |
| BR-04 | Material Request → Purchase Order → Purchase Receipt → Purchase Invoice | Fit |
| BR-05 | Quotation → Sales Order → Delivery Note → Sales Invoice | Fit |
| BR-06 | BOM with sub-assembly BOMs (Power Pack, Frame Kit) | Fit |
| BR-07 | Production Plan (MRP) with lead times from Item master | Config |
| BR-08 | Work Order + Stock Entry (Material Transfer for Manufacture / Manufacture) | Fit |
| BR-09 | BOM costing on "Last Purchase Rate"; BOM Update Tool for cost roll-up | Config |
| BR-10 | Python migration pipeline via ERPNext REST API (cleansing + validation + reconciliation) | **Gap** |
| BR-11 | Supplier's SOAP pricing service → sync job updating Item Price & lead time | **Gap** |
| BR-12 | REST order-intake endpoint creating draft Sales Orders | **Gap** |
| BR-13 | n/a | Out of scope |

**Summary:** 9 of 12 in-scope requirements are met by standard ERPNext or configuration alone.
The 3 gaps are all integration/data work. None needs changes to ERPNext's own code, so the
system stays on the vendor upgrade path.

## 6. Scope, assumptions & risks

**In scope:** Stock, Buying, Selling, Manufacturing modules; data migration; two integrations;
UAT; cutover; 2 weeks of post-go-live support.

**Out of scope:** Accounting migration from Tally, payroll, CRM, quality inspection.

| Risk | Impact | Mitigation |
|---|---|---|
| Legacy Excel data is inconsistent (duplicates, mixed units) | Bad master data at go-live | Cleansing rules + reconciliation report signed off by store keeper |
| Opening stock count is inaccurate | Wrong MRP output from day one | Physical stock count the weekend before cutover |
| Users revert to WhatsApp ordering | Process not adopted | Short role-based user guides; POs only paid if raised in ERPNext |
| Supplier pricing service unavailable | Stale prices | Sync job logs failures and keeps last known price |

## 7. Sign-off

| Role | Name | Status |
|---|---|---|
| Managing Director (sponsor) | — | Pending |
| Production Head | — | Pending |
| Implementation Consultant | Rehbar Khan | Prepared |
