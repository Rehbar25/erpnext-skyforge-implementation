# Cutover Plan: Go-Live Weekend

**Client:** SkyForge Drones Pvt Ltd · **Go-live:** Monday 2026-11-02, 09:00 · **Version:** 1.1
**Cutover lead:** Rehbar Khan · **Business owner:** Managing Director

The cutover moves SkyForge from Excel/WhatsApp to ERPNext over one weekend, with a tested way back.
Every technical step is scripted ([`run_all.sh`](../run_all.sh)) and has been rehearsed end to end
from an empty system (mock cutovers below).

## 1. Timeline

| When | Step | Owner | Done when |
|---|---|---|---|
| T-25 (8 Oct) | **Mock cutover 1:** full rebuild from empty system, all 14 UAT checks | Consultant | ✅ Done: 19/19 migration checks, 60/60 tests |
| T-14 (19 Oct) | UAT sign-off by department heads ([UAT scripts](06_uat_test_scripts.md)) | Dept heads | Signed |
| T-10 (23 Oct) | End-user training: Stores, Purchase, Production, Sales (role-based guides) | Consultant | Attendance sheet |
| T-7 (26 Oct) | **Mock cutover 2** with the latest legacy workbook; client signs reconciliation report | Consultant + Ramesh | Signed report, 0 OPEN exceptions |
| T-3 (30 Oct) | Last PO/SO in legacy process; open POs and open SOs listed for re-entry | Priya, Fatima | Lists received |
| **T-2 (Sat 31 Oct)** | **Freeze**: no stock movements; physical stock count of all 23 components + finished goods | Ramesh | Count sheet signed |
| T-2 | Count sheet entered into legacy workbook *Stock Count* tab | Ramesh | |
| T-1 (Sun 1 Nov) 09:00 | Backup of empty-but-configured system (restore point R0) | Consultant | Backup file listed |
| T-1 10:00 | Cleansing dry run; any new OPEN exceptions resolved with client by phone | Consultant + Ramesh | 0 OPEN |
| T-1 11:00 | Live migration + automatic verification (read back from ERPNext) | Consultant | All checks ✅ |
| T-1 12:00 | Re-enter open POs and open SOs from T-3 lists | Priya, Fatima | Counts match lists |
| T-1 14:00 | Spot checks by business: 10 items' stock, 2 BOM costs, 3 supplier contacts | Dept heads | Checklist ticked |
| T-1 16:00 | **Go / No-go call** (criteria §3) | MD | Decision recorded |
| T-1 16:30 | Backup (restore point R1 = "go-live baseline"); migration lock confirmed active | Consultant | |
| **T-0 (Mon 2 Nov) 09:00** | **Go-live.** Legacy sheets set read-only; price sync and order intake switched on | All | |
| T+1 to T+10 | Hypercare: daily 15-min stand-up, issues logged in [issue log](07_issue_log.md) | Consultant | |

## 2. Technical runbook (T-1)

```bash
docker compose -f infra/docker-compose.yml -p skyforge exec -T backend bench --site frontend backup   # R0
.venv/bin/python -m migration.run --dry-run       # expect: 0 OPEN
.venv/bin/python -m migration.run                 # expect: all verification checks passed
docker compose -f infra/docker-compose.yml -p skyforge exec -T backend bench --site frontend backup   # R1
```

After go-live the migration **refuses to run** (it detects posted invoices, receipts and stock entries),
so a mistaken re-run cannot overwrite live master data. Added after mock cutover 1, see ISS-09.

## 3. Go / No-go criteria

All must be true:

1. Migration verification: every check passed; stock value equals signed count sheet × agreed rates.
2. 0 OPEN data exceptions; all client decisions recorded in `decisions.json`.
3. UAT-01 to UAT-14 signed off; no open *High* issues in the issue log.
4. Each department has at least one trained user who has logged in successfully.
5. Restore point R0 exists and a restore has been rehearsed (done during mock cutover 1).

## 4. Rollback plan

| Trigger (decided by MD + consultant) | Action | Time to recover |
|---|---|---|
| Migration verification fails and cannot be fixed by 15:00 Sunday | Restore R0, stay on legacy process one more week, re-plan | < 30 min |
| Critical defect in first 2 days of live use (e.g., cannot receive goods) | Fix forward if < 4 h; else restore R1 and re-enter the day's transactions | < 1 day |

Legacy spreadsheets stay read-only (not deleted) for 90 days as a reference.

## 5. Communication

| When | Audience | Message | Channel |
|---|---|---|---|
| T-7 | All staff | Go-live date, freeze rules, who to call | Email + notice board |
| T-2 | Suppliers (6) | POs from 2 Nov will come from ERPNext; contact unchanged | Email from Priya |
| T-1 16:00 | Leadership | Go/No-go result | Call |
| T-0 | All staff | "We're live": login links, user guides, hypercare contact | Email |
