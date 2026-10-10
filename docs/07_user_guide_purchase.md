# User Guide: Purchasing in ERPNext

**For:** Priya (Purchase) · **Login:** `purchase@skyforge.example` · **Time to learn:** ~30 minutes

This guide covers your daily work. Tip: the search bar at the top of every screen opens any screen by
name. Type *Material Request List* and press Enter.

---

## Your daily routine (10 minutes, every morning)

### 1. Check what the system wants you to buy
1. Open **Material Request List**.
2. Filter **Status = Pending**. You'll see two kinds:
   - **From the production plan:** parts needed for confirmed customer orders. *Highest priority.*
   - **"Auto created via reorder"** (tick shown): stock fell to its minimum level overnight.
3. Open each one and check the quantities. The **Required By** date is already set from each supplier's
   lead time (AeroParts 28–35 days, Hyderabad Fasteners 3 days).

> You no longer need to check shelves or wait for production to tell you something is short.

### 2. Turn a request into purchase orders
1. In the Material Request, click **Create → Purchase Order**.
2. Set **Supplier**. Each part has a default supplier, so only order that supplier's parts on this PO.
   Remove other suppliers' lines and create a separate PO for them from the same request.
3. Prices fill in from the **Standard Buying** price list. *Don't type prices manually*; if a price looks
   wrong, tell the consultant (see §5).
4. **Save → Submit.** Then **Email** the PO to the supplier from the PO's menu (⋯ → Email).

### 3. When goods arrive (with Ramesh in Stores)
1. Open the **Purchase Order** → **Create → Purchase Receipt**.
2. Ramesh enters the **quantity actually received**. If short, enter what arrived; the PO stays open
   for the rest.
3. **Submit.** Stock is now available to production.

> The system will not accept a receipt without a PO. This is deliberate: every rupee we spend is
> approved first.

### 4. When the supplier's bill arrives
1. Open the **Purchase Receipt** → **Create → Purchase Invoice**.
2. Enter the supplier's **bill number and date**. Check the total against the paper bill.
3. **Submit.** The PO now shows 100% received and 100% billed.

---

## Weekly: supplier prices (AeroParts)

AeroParts' price list is pulled into ERPNext automatically every quarter. After each sync:

1. Open **Supplier → AeroParts Imports Ltd** and read the latest comment, e.g. *"4 prices updated, 1 held
   for approval, 1 unmapped part number"*.
2. **Held for approval** means a price changed by more than 25%. The system has **not** used it. Call
   AeroParts to confirm, then ask the consultant to approve it.
3. **Unmapped** means AeroParts sells a part we have never bought. Usually nothing to do.

---

## Quick answers

| Question | Where to look |
|---|---|
| How many ESCs do we have? | Search **Stock Balance** → filter item |
| Is the GPS order from AeroParts late? | **Purchase Order List** → filter supplier, status *To Receive* |
| What did we pay for motors last time? | Open the **Item** → *Purchase* section → Last Purchase Rate |
| Which parts are below minimum? | **Material Request List** → "Auto created via reorder" |

## What you can and can't do

| You can | You can't (by design) |
|---|---|
| Create and submit POs, receipts, purchase invoices | Edit price lists or create customer orders |
| Edit supplier details | Delete submitted documents (use *Cancel*, which keeps a record) |
| See stock levels in all warehouses | Change BOMs (Production Head only) |

**Help:** hypercare stand-up daily at 09:30 during the first two weeks · consultant: Rehbar Khan
