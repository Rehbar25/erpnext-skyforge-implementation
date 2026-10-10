# Business Cycle Results: First Month of Operations

Generated from an end-to-end run against ERPNext v16 ([`scenarios/business_cycle.py`](../scenarios/business_cycle.py)). Every document below exists in the system; names are ERPNext document IDs.

## 1. Customer demand (Sales Orders)

| Sales Order | Customer | Model | Qty | Value | Delivery |
|---|---|---|---|---|---|
| SAL-ORD-2026-00001 | SunGrid Solar Parks | SF-Q250 | 6 | ₹408,000 | 2026-11-10 |
| SAL-ORD-2026-00002 | TerraMap Surveys | SF-X450 | 2 | ₹290,000 | 2026-11-20 |
| SAL-ORD-2026-00003 | Deccan Infra Inspections | SF-Q250 | 4 | ₹272,000 | 2026-11-15 |
| | | | **12** | **₹970,000** | |

## 2. Planning (Production Plan / MRP)

Production Plan **MFG-PP-2026-00001** pulled all open sales orders and exploded the multi-level BOMs.

**Step 1: net finished goods on hand.** ERPNext plans gross sales-order quantity, so the planner nets existing finished stock first:

| Sales Order | Model | Demand | From FG stock | To build |
|---|---|---|---|---|
| SAL-ORD-2026-00001 | SF-Q250 | 6 | 2 | 4 |
| SAL-ORD-2026-00002 | SF-X450 | 2 | 0 | 2 |
| SAL-ORD-2026-00003 | SF-Q250 | 4 | 0 | 4 |

**Step 2: sub-assemblies scheduled:** SA-FRM-Q250×4, SA-PWR-Q250×4, SA-FRM-X450×2, SA-PWR-X450×2, SA-FRM-Q250×4, SA-PWR-Q250×4

**Step 3: component requirements vs projected stock** (shortages in bold):

| Component | Required | Projected available | To order |
|---|---|---|---|
| **ESC-30A** | 32 | 18 | **14** |
| **GPS-M10** | 10 | 6 | **4** |
| FRM-Q250-ARM | 32 | 64 | 0 |
| FRM-Q250-PLT | 16 | 30 | 0 |
| HW-STANDOFF | 88 | 420 | 0 |
| HW-SCREW-M3 | 264 | 1150 | 0 |
| MTR-2306 | 32 | 52 | 0 |
| PDB-120 | 8 | 15 | 0 |
| WIRE-14AWG | 12 | 85 | 0 |
| FC-F7 | 8 | 12 | 0 |
| PRP-5045 | 16 | 44 | 0 |
| BAT-4S1500 | 8 | 9 | 0 |
| RX-ELRS | 10 | 20 | 0 |
| CAM-4K | 8 | 8 | 0 |
| FRM-X450-ARM | 12 | 36 | 0 |
| FRM-X450-PLT | 4 | 10 | 0 |
| MTR-3508 | 12 | 30 | 0 |
| ESC-40A | 12 | 26 | 0 |
| PDB-200 | 2 | 6 | 0 |
| FC-H7 | 2 | 5 | 0 |
| PRP-1045 | 6 | 21 | 0 |
| BAT-6S5000 | 2 | 4 | 0 |
| CAM-MAP | 2 | 3 | 0 |

Result: 23 components checked, **2 shortages**, both on the 28-day import supplier. Under the old process these were discovered at the assembly bench.

## 3. Procure-to-Pay

| Step | Document | Detail |
|---|---|---|
| Material Request (from MRP) | MAT-MR-2026-00001 | ESC-30A×14, GPS-M10×4 |
| Purchase Order | PUR-ORD-2026-00001 | AeroParts Imports Ltd: ESC-30A×14, GPS-M10×4, ₹21,700 |
| Purchase Receipt | MAT-PRE-2026-00001 | Received into Stores - SFD against PUR-ORD-2026-00001 |
| Purchase Invoice | ACC-PINV-2026-00001 | ₹21,700, 3-way matched to PO and receipt |

## 4. Manufacturing

Sub-assemblies are built first (Stores → WIP → Stores), then drones (Stores → WIP → Finished Goods). Components are back-flushed per BOM.

| Work Order | Item | Qty | Manufacture entry | Actual unit cost |
|---|---|---|---|---|
| MFG-WO-2026-00004 | SA-FRM-Q250 | 4 | MAT-STE-2026-00002 | ₹3,384 |
| MFG-WO-2026-00005 | SA-PWR-Q250 | 4 | MAT-STE-2026-00004 | ₹10,295 |
| MFG-WO-2026-00006 | SA-FRM-X450 | 2 | MAT-STE-2026-00006 | ₹7,256 |
| MFG-WO-2026-00007 | SA-PWR-X450 | 2 | MAT-STE-2026-00008 | ₹28,490 |
| MFG-WO-2026-00008 | SA-FRM-Q250 | 4 | MAT-STE-2026-00010 | ₹3,384 |
| MFG-WO-2026-00009 | SA-PWR-Q250 | 4 | MAT-STE-2026-00012 | ₹10,295 |
| MFG-WO-2026-00001 | SF-Q250 | 4 | MAT-STE-2026-00014 | ₹41,419 |
| MFG-WO-2026-00002 | SF-X450 | 2 | MAT-STE-2026-00016 | ₹99,486 |
| MFG-WO-2026-00003 | SF-Q250 | 4 | MAT-STE-2026-00018 | ₹41,419 |

## 5. Product costing & margin (pain point 3)

| Model | Selling price | Actual material cost | Gross margin | Margin % |
|---|---|---|---|---|
| SF-Q250 | ₹68,000 | ₹41,419 | ₹26,581 | **39.1%** |
| SF-X450 | ₹145,000 | ₹99,486 | ₹45,514 | **31.4%** |

The SF-X450's margin is 7.7 points below the SF-Q250's, confirming management's suspicion with data. 38% of its cost is the mapping camera, so supplier negotiation there has the most leverage.

## 6. Order-to-Cash

| Sales Order | Delivery Note | Sales Invoice | Value | Payment |
|---|---|---|---|---|
| SAL-ORD-2026-00001 | MAT-DN-2026-00001 | ACC-SINV-2026-00001 | ₹408,000 | ACC-PAY-2026-00001 (received) |
| SAL-ORD-2026-00002 | MAT-DN-2026-00002 | ACC-SINV-2026-00002 | ₹290,000 | outstanding |
| SAL-ORD-2026-00003 | MAT-DN-2026-00003 | ACC-SINV-2026-00003 | ₹272,000 | outstanding |

## 7. Reorder automation (BR-03)

After production, ERPNext's scheduled reorder job found 18 components at or below reorder level and raised **MAT-MR-2026-00002** automatically. Required-by dates follow each item's supplier lead time:

| Required by | Items |
|---|---|
| 2026-10-13 | PDB-120×30, PDB-200×10 |
| 2026-10-18 | FRM-Q250-ARM×120, FRM-Q250-PLT×60, FRM-X450-ARM×60, FRM-X450-PLT×20 |
| 2026-10-22 | CAM-MAP×6, CAM-4K×15 |
| 2026-10-29 | BAT-4S1500×30, BAT-6S5000×10 |
| 2026-11-05 | MTR-2306×120, MTR-3508×60, ESC-30A×120, ESC-40A×60, FC-F7×30, GPS-M10×40, FC-H7×10, RX-ELRS×40 |

Value of auto-raised request: ₹1,840,600. Purchase reviews it and converts it to POs, so no one has to spot low stock by eye or chase suppliers on WhatsApp.
