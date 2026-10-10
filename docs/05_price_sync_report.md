# Supplier Price Sync Report (AeroParts SOAP → ERPNext)

**Run:** 2026-10-08 22:06 · **Supplier:** AeroParts Imports Ltd · **Price list:** AP-PL-2026Q4 · **Mode:** live

## Line-by-line decisions

| Item | Supplier part | Old ₹ | New ₹ | Change | Lead time | Result |
|---|---|---|---|---|---|---|
| MTR-2306 | AP-BLM-2306-2450 | 1,450 | 1,450 | +0.0% | 28 d | No change |
| MTR-3508 | AP-BLM-3508-0700 | 3,200 | 3,350 | +4.7% | 28 d | ✅ Applied |
| ESC-30A | AP-ESC-B32-30 | 950 | 1,020 | +7.4% | 28 → 35 d | ✅ Applied |
| ESC-40A | AP-ESC-B32-40 | 1,350 | 1,350 | +0.0% | 28 d | No change |
| FC-F7 | AP-FC-F722 | 6,800 | 6,650 | -2.2% | 28 d | ✅ Applied |
| FC-H7 | AP-FC-H743 | 11,500 | 16,900 | +47.0% | 28 d | ⏸ Held for approval: +47.0% exceeds ±25% auto-approve limit |
| GPS-M10 | AP-GNSS-M10 | 2,100 | 2,250 | +7.1% | 28 d | ✅ Applied |
|  | AP-BLM-2207-1950 | n/a | 1,290 |  |  | ⚠ Unmapped: Part number not linked to any SkyForge item |
| RX-ELRS |  | 1,200 | n/a |  |  | Kept last price: Not on supplier's current list; last price kept |

## Impact on product cost (BOM roll-up)

| BOM item | Cost before | Cost after | Δ |
|---|---|---|---|
| SA-FRM-Q250 | ₹3,384 | ₹3,384 | +₹0 |
| SA-FRM-X450 | ₹7,256 | ₹7,256 | +₹0 |
| SA-PWR-Q250 | ₹10,295 | ₹10,575 | +₹280 |
| SA-PWR-X450 | ₹28,490 | ₹29,390 | +₹900 |
| SF-Q250 | ₹41,419 | ₹41,699 | +₹280 |
| SF-X450 | ₹99,486 | ₹100,536 | +₹1,050 |

| Model | Margin before | Margin after |
|---|---|---|
| SF-Q250 | 39.1% | 38.7% |
| SF-X450 | 31.4% | 30.7% |

## Action required

- **FC-H7**: supplier quotes ₹16,900 vs ₹11,500 (+47%). Purchase manager to confirm with AeroParts before approving.
