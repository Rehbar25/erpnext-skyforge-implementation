# Data Migration Reconciliation Report

**Client:** SkyForge Drones Pvt Ltd · **Source:** `SkyForge_Master_Data.xlsx` · **Run:** 2026-10-08 22:05 · **Mode:** load + verify

## 1. Source to target

| Entity | Source rows | Not migrated (duplicate / obsolete / write-off / rejected) | Blocked (OPEN) | Ready to load |
|---|---|---|---|---|
| Suppliers | 7 | 1 | 0 | 6 |
| Items | 32 | 3 | 0 | 29 |
| Customers | 8 | 1 | 0 | 7 |
| BOM lines | 32 | 0 | 0 | 32 |
| Stock lines | 27 | 3 | 0 | 24 |

Stock lines are aggregated per item and warehouse, so *Ready to load* counts distinct item/warehouse pairs.

## 2. Data-quality exceptions

81 exceptions raised. Full log: [`04_migration_exception_log.csv`](04_migration_exception_log.csv).

| Resolution | Count | Meaning |
|---|---|---|
| auto-fixed | 64 | Formatting with exactly one correct answer (units, whitespace, ₹ symbols) |
| client decision | 9 | Resolved per signed-off `decisions.json` |
| excluded | 7 | Intentionally not migrated |
| accepted | 1 | Loaded as-is, follow-up owned by client |
| **OPEN** | **0** | **Blocks go-live until decided** |

### Auto-fixes by type

| Issue | Rows |
|---|---|
| Non-standard UOM | 25 |
| Price not stored as a plain number | 22 |
| Unit typed into quantity | 7 |
| Non-standard phone format | 5 |
| Lead time stored as text | 3 |
| Code not in standard upper case | 1 |
| Leading/trailing/double spaces | 1 |

### Decisions, exclusions and open items

| ID | Sheet:row | Value | Issue | Resolution |
|---|---|---|---|---|
| SUP-005 | Suppliers:5 | `36AABFS1111N1Z0` | GSTIN fails checksum | client decision: loaded without GSTIN, purchase team to obtain correct one |
| SUP-008 | Suppliers:6 | `` | Missing email | accepted: loads without email; contact to be completed by purchase |
| SUP-011 | Suppliers:8 | `Aeroparts Imports` | Duplicate of SUP-AERO | excluded: merged into SUP-AERO (client decision) |
| ITM-002 | Items:3 | `2306 motor 2450KV` | Missing code; duplicate of MTR-2306 | excluded: merged into MTR-2306 (client decision) |
| ITM-022 | Items:13 | `Silicone Wire 14AWG` | Missing item code | client decision: code WIRE-14AWG assigned |
| ITM-037 | Items:20 | `` | Missing item group | client decision: Components |
| ITM-048 | Items:25 | `approx 38k` | Unparseable price | client decision: ₹38,000 |
| ITM-054 | Items:32 | `FC-F4` | Obsolete item | excluded: not migrated |
| ITM-055 | Items:33 | `RX-ELRS` | Exact duplicate row | excluded: duplicate row removed |
| CUS-001 | Customers:4 | `` | Missing state (needed for GST place of supply) | client decision: Maharashtra |
| CUS-002 | Customers:7 | `GREENACRE AGRITECH` | Name in all caps | client decision: GreenAcre Agritech |
| CUS-003 | Customers:9 | `Sungrid Solar Parks Pvt Ltd` | Missing customer code; same GSTIN as CUST-SUNG | excluded: merged into CUST-SUNG (client decision) |
| BOM-001 | Parts Lists:2 | `Motor 2306` | Part referenced by name, not code | client decision: MTR-2306 |
| STK-004 | Stock Count:11 | `pdb 200` | Non-standard item code | client decision: PDB-200 |
| STK-008 | Stock Count:26 | `FC-F4` | Stock of obsolete item | excluded: not migrated |
| STK-009 | Stock Count:27 | `MTR-2207` | Item not in item master | excluded: Motor from a discontinued prototype; client confirmed write-off, not migrated. |
| STK-010 | Stock Count:28 | `-2` | Negative quantity on a count sheet | client decision: line rejected, physical count stands |

## 3. Load results

| Object | Created | Updated | Skipped (already loaded) | Failed |
|---|---|---|---|---|
| Supplier | 6 | 0 | 0 | 0 |
| Item | 29 | 0 | 0 | 0 |
| Item Price | 25 | 0 | 0 | 0 |
| Customer | 7 | 0 | 0 | 0 |
| BOM | 6 | 0 | 0 | 0 |
| Opening Stock | 1 | 0 | 0 | 0 |

## 4. Post-load verification (read back from ERPNext)

**19 / 19 checks passed.**

| Check | Expected | In ERPNext | Result |
|---|---|---|---|
| Items present | 29 | 29 | ✅ |
| Suppliers present | 6 | 6 | ✅ |
| Customers present | 7 | 7 | ✅ |
| Customers with address | 7 | 7 | ✅ |
| Default BOMs submitted | 6 | 6 | ✅ |
| BOM SA-PWR-Q250 lines | 4 lines | 4 lines (identical) | ✅ |
| BOM SA-PWR-Q250 cost (₹) | 10,295.0 | 10,295.0 | ✅ |
| BOM SA-PWR-X450 lines | 4 lines | 4 lines (identical) | ✅ |
| BOM SA-PWR-X450 cost (₹) | 28,490.0 | 28,490.0 | ✅ |
| BOM SA-FRM-Q250 lines | 4 lines | 4 lines (identical) | ✅ |
| BOM SA-FRM-Q250 cost (₹) | 3,384.0 | 3,384.0 | ✅ |
| BOM SA-FRM-X450 lines | 4 lines | 4 lines (identical) | ✅ |
| BOM SA-FRM-X450 cost (₹) | 7,256.0 | 7,256.0 | ✅ |
| BOM SF-Q250 lines | 8 lines | 8 lines (identical) | ✅ |
| BOM SF-Q250 cost (₹) | 41,419.0 | 41,419.0 | ✅ |
| BOM SF-X450 lines | 8 lines | 8 lines (identical) | ✅ |
| BOM SF-X450 cost (₹) | 99,486.0 | 99,486.0 | ✅ |
| Stock lines matching count sheet | 24 | 24 | ✅ |
| Opening stock value (₹) | 907,833.0 | 907,833.0 | ✅ |

## Sign-off

| Role | Name | Date |
|---|---|---|
| Store Keeper (stock & items) | Ramesh | |
| Purchase (suppliers) | Priya | |
| Implementation Consultant | Rehbar Khan | |
