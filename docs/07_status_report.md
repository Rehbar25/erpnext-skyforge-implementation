# Weekly Status Report: Week 4

**To:** Managing Director, SkyForge Drones · **Cc:** Arjun (Production), Priya (Purchase), Ramesh (Stores), Fatima (Sales)
**From:** Rehbar Khan, Implementation Consultant · **Date:** Thursday 8 October 2026

## Overall status: 🟢 On track for go-live on Monday 2 November

| Area | Status | Comment |
|---|---|---|
| Scope | 🟢 | All 12 in-scope requirements built and tested |
| Schedule | 🟢 | Mock go-live completed 3 weeks ahead of the real one |
| Data | 🟢 | Your spreadsheets are fully moved over and checked; 3 small follow-ups with Priya |
| Decisions needed | 🟡 | 3 decisions needed from you this week (below) |

## What we achieved this week

1. **Dress rehearsal of go-live, done successfully.** We rebuilt the whole system from empty, moved all your
   spreadsheet data in, and ran a full month of business through it: 3 customer orders, purchasing,
   production of 10 drones, delivery and invoicing. Everything balanced.
2. **Your data is clean.** Your spreadsheets contained 81 problems (duplicate parts, the same supplier
   entered twice, prices typed as text, a motor that no longer exists). 64 were simple formatting fixes
   made automatically; 16 were decided with Ramesh and Priya, including 7 rows deliberately left behind
   (duplicates, an obsolete part, a written-off motor); 1 was accepted as-is. Nothing was changed without
   a record of why.
3. **The system now tells you what to buy.** For the three current orders it calculated that only
   **14 ESCs and 4 GPS modules** need to be bought. Both come from AeroParts, which takes 4 weeks, so
   they are now ordered on day one instead of being discovered missing at the assembly bench.
4. **You now know your real margins.** The SF-Q250 makes **39.1%**; the SF-X450 makes **31.4%**. The
   X450's mapping camera alone is 38% of its cost, so that's the best place to negotiate.
5. **AeroParts' new prices load automatically.** This quarter's list changed four prices (three small rises, one drop); the
   system applied them and recalculated product costs. It **refused** one suspicious price (below).
6. **Website orders go straight into the system** as drafts for Fatima's team to confirm, and customers
   can check their order status online instead of emailing.

## Decisions needed from you

| # | Decision | Our recommendation | Needed by |
|---|---|---|---|
| 1 | AeroParts quoted the H7 flight controller at **₹16,900, up 47%** from ₹11,500. If accepted, the X450 margin drops from 30.7% to 26.9%. | Priya confirms with AeroParts whether this is a typo before we accept it. | 15 Oct |
| 2 | AeroParts no longer lists the **ELRS receiver**. 10 are left after this month's builds. | Ask Priya to find a second supplier now. | 22 Oct |
| 3 | **GST invoicing** stays in Tally for now (as agreed). | Confirm Tally continues until Phase 2 in Q1 2027. | 15 Oct |

## Issues and risks

- **One problem found and fixed during rehearsal:** re-loading the old spreadsheets after go-live could
  have overwritten new supplier prices. The system now blocks this automatically.
- **Hyderabad Fasteners' GST number is invalid** in your records. Purchase is not blocked, but Priya needs
  the correct number before their first invoice.
- **Risk: the stock count on 31 October.** The whole system starts from that count, so it must be
  accurate. Ramesh has agreed to a two-person count.

## Next week

- Sign-off of test results by each department (Arjun, Priya, Ramesh, Fatima): 1 hour each
- Training sessions: Purchase (Tue), Stores (Wed), Production and Sales (Thu)
- Second rehearsal with your latest spreadsheets on 26 October

Full details: [test results](06_uat_test_scripts.md) · [go-live plan](06_cutover_plan.md) ·
[issue log](07_issue_log.md) · [data reconciliation](04_migration_reconciliation.md)
