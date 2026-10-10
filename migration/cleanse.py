"""Cleanse and validate SkyForge's legacy workbook into load-ready records.

Nothing is silently fixed. Every change or rejection is recorded as an Exception with a
resolution:
  auto-fixed      formatting issue with exactly one correct answer (whitespace, "₹1,450")
  client decision resolved by an entry in decisions.json (signed off by the client)
  excluded        intentionally not migrated (obsolete, duplicate, write-off)
  OPEN            blocks the record; needs a client decision before go-live
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

UOM_MAP = {"nos": "Nos", "pcs": "Nos", "unit": "Nos", "pair": "Pair", "pairs": "Pair",
           "mtr": "Meter", "m": "Meter", "meter": "Meter"}
GST_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


@dataclass
class Exception_:
    id: str
    sheet: str
    row: int            # spreadsheet row number as the client sees it (header = row 1)
    field: str
    value: str
    issue: str
    resolution: str

    @property
    def is_open(self):
        return self.resolution == "OPEN"


@dataclass
class CleanData:
    items: dict = field(default_factory=dict)        # code -> item record
    suppliers: dict = field(default_factory=dict)    # code -> supplier record
    customers: dict = field(default_factory=dict)    # code -> customer record
    stock: dict = field(default_factory=dict)        # (code, warehouse) -> qty
    boms: dict = field(default_factory=dict)         # parent -> [(component, qty)]
    exceptions: list = field(default_factory=list)
    source_rows: dict = field(default_factory=dict)  # sheet -> row count

    @property
    def open_exceptions(self):
        return [e for e in self.exceptions if e.is_open]


# --------------------------------------------------------------------------- parsers
def clean_text(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return re.sub(r"\s+", " ", str(v)).strip()


def parse_number(v):
    """'₹1,450' / 'Rs. 950' / '52 pcs' / '1 m' / 12.0 -> float. None if unparseable."""
    s = clean_text(v)
    if not s:
        return None
    s = re.sub(r"^(₹|rs\.?|inr)\s*", "", s, flags=re.I).replace(",", "")
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*(pcs|nos|m|mtr|days?)?", s, flags=re.I)
    return float(m.group(1)) if m else None


def parse_lead_days(v):
    s = clean_text(v).lower()
    m = re.fullmatch(r"(\d+)\s*(days?|weeks?)?", s)
    if not m:
        return None
    return int(m.group(1)) * (7 if (m.group(2) or "").startswith("week") else 1)


def gstin_valid(g: str) -> bool:
    if not GSTIN_RE.match(g):
        return False
    total = 0
    for i, ch in enumerate(g[:14]):
        p = GST_CHARS.index(ch) * (2 if i % 2 else 1)
        total += p // 36 + p % 36
    return GST_CHARS[(36 - total % 36) % 36] == g[14]


def normalise_phone(v):
    digits = re.sub(r"\D", "", clean_text(v))
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    digits = digits.lstrip("0")
    return f"+91-{digits}" if len(digits) == 10 else None


def tokens(name: str) -> set:
    return set(re.findall(r"[a-z0-9]+", name.lower()))


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) / len(ta | tb) if ta | tb else 0.0


# --------------------------------------------------------------------------- engine
class Cleanser:
    def __init__(self, workbook: Path, decisions: dict | None = None):
        self.sheets = pd.read_excel(workbook, sheet_name=None, dtype=object)
        self.d = decisions or {}
        self.out = CleanData(source_rows={k: len(v) for k, v in self.sheets.items()})
        self._seq = {}
        self.excluded_items = {}   # code -> reason (obsolete etc.)

    def _raise(self, prefix, sheet, idx, fld, value, issue, resolution):
        self._seq[prefix] = self._seq.get(prefix, 0) + 1
        self.out.exceptions.append(Exception_(f"{prefix}-{self._seq[prefix]:03d}", sheet, idx + 2,
                                              fld, clean_text(value), issue, resolution))

    def _decision(self, key, lookup):
        return self.d.get(key, {}).get(lookup)

    def run(self) -> CleanData:
        self.suppliers()
        self.items()
        self.customers()
        self.boms()
        self.stock()
        return self.out

    # ------------------------------------------------------------------ suppliers
    def suppliers(self):
        S = "Suppliers"
        for idx, r in self.sheets[S].iterrows():
            code, name = clean_text(r["Supplier ID"]).upper(), clean_text(r["Supplier Name"])
            if not code:
                target = self._decision("supplier_aliases", name.lower())
                if target:
                    self._raise("SUP", S, idx, "Supplier ID", name, f"Duplicate of {target}",
                                f"excluded: merged into {target} (client decision)")
                else:
                    self._raise("SUP", S, idx, "Supplier ID", name, self._dup_hint(
                        name, {c: s["name"] for c, s in self.out.suppliers.items()}, "Missing supplier ID"), "OPEN")
                continue

            gstin = clean_text(r["GSTIN"]).upper()
            if gstin and not gstin_valid(gstin):
                if self.d.get("invalid_gstin_action") == "load_without_tax_id":
                    self._raise("SUP", S, idx, "GSTIN", gstin, "GSTIN fails checksum",
                                "client decision: loaded without GSTIN, purchase team to obtain correct one")
                    gstin = ""
                else:
                    self._raise("SUP", S, idx, "GSTIN", gstin, "GSTIN fails checksum", "OPEN")
                    continue

            phone = normalise_phone(r["Phone"])
            if phone is None:
                self._raise("SUP", S, idx, "Phone", r["Phone"], "Unrecognised phone format", "auto-fixed: left blank")
            elif phone != clean_text(r["Phone"]):
                self._raise("SUP", S, idx, "Phone", r["Phone"], "Non-standard phone format", f"auto-fixed: {phone}")

            email = clean_text(r["Email"]).lower()
            if not email:
                self._raise("SUP", S, idx, "Email", "", "Missing email",
                            "accepted: loads without email; contact to be completed by purchase")

            lead = parse_lead_days(r["Lead Time"])
            if lead is None:
                self._raise("SUP", S, idx, "Lead Time", r["Lead Time"], "Unparseable lead time", "OPEN")
                continue
            if str(r["Lead Time"]).strip() != str(lead):
                self._raise("SUP", S, idx, "Lead Time", r["Lead Time"], "Lead time stored as text",
                            f"auto-fixed: {lead} days")

            group = self._decision("supplier_groups", code)
            if not group:   # classification only; never worth blocking a supplier over
                group = "All Supplier Groups"
                self._raise("SUP", S, idx, "Supplier Group", "", "No supplier group assigned",
                            "auto-fixed: default group, purchase to classify")

            self.out.suppliers[code] = {"code": code, "name": name, "city": clean_text(r["City"]),
                                        "gstin": gstin, "phone": phone, "email": email,
                                        "lead_days": lead, "group": group}

    # ------------------------------------------------------------------ items
    def items(self):
        S = "Items"
        df = self.sheets[S]
        dup_mask = df.duplicated(keep="first")
        for idx, r in df.iterrows():
            raw_code, raw_name = r["Item Code"], r["Item Name"]
            code, name = clean_text(raw_code).upper(), clean_text(raw_name)
            if dup_mask[idx]:
                self._raise("ITM", S, idx, "(row)", code, "Exact duplicate row", "excluded: duplicate row removed")
                continue
            if clean_text(r["Status"]).lower() == "obsolete":
                self.excluded_items[code] = "obsolete"
                self._raise("ITM", S, idx, "Status", code, "Obsolete item", "excluded: not migrated")
                continue
            if code and code != clean_text(raw_code):
                self._raise("ITM", S, idx, "Item Code", raw_code, "Code not in standard upper case", f"auto-fixed: {code}")
            if name != str(raw_name):
                self._raise("ITM", S, idx, "Item Name", repr(raw_name), "Leading/trailing/double spaces", "auto-fixed: trimmed")

            if not code:
                alias = self._decision("item_aliases", name.lower())
                assigned = self._decision("item_code_assignments", name.lower())
                if alias:
                    self._raise("ITM", S, idx, "Item Code", name, f"Missing code; duplicate of {alias}",
                                f"excluded: merged into {alias} (client decision)")
                    continue
                if assigned:
                    code = assigned
                    self._raise("ITM", S, idx, "Item Code", name, "Missing item code",
                                f"client decision: code {code} assigned")
                else:
                    known = {clean_text(c).upper(): clean_text(n) for c, n in zip(df["Item Code"], df["Item Name"])
                             if clean_text(c)}
                    self._raise("ITM", S, idx, "Item Code", name, self._dup_hint(name, known, "Missing item code"), "OPEN")
                    continue

            group = clean_text(r["Category"]) or self._decision("item_group_overrides", code)
            if not clean_text(r["Category"]):
                self._raise("ITM", S, idx, "Category", "", "Missing item group",
                            f"client decision: {group}" if group else "OPEN")
                if not group:
                    continue

            uom = UOM_MAP.get(clean_text(r["Unit"]).lower())
            if not uom:
                self._raise("ITM", S, idx, "Unit", r["Unit"], "Unknown unit of measure", "OPEN")
                continue
            if uom != clean_text(r["Unit"]):
                self._raise("ITM", S, idx, "Unit", r["Unit"], "Non-standard UOM", f"auto-fixed: {uom}")

            buy_rate = None
            if group == "Components":
                buy_rate = parse_number(r["Last Purchase Price"])
                if buy_rate is None:
                    buy_rate = self._decision("item_price_overrides", code)
                    self._raise("ITM", S, idx, "Last Purchase Price", r["Last Purchase Price"], "Unparseable price",
                                f"client decision: ₹{buy_rate:,.0f}" if buy_rate else "OPEN")
                    if buy_rate is None:
                        continue
                elif clean_text(r["Last Purchase Price"]) != f"{buy_rate:g}":
                    self._raise("ITM", S, idx, "Last Purchase Price", r["Last Purchase Price"],
                                "Price not stored as a plain number", f"auto-fixed: {buy_rate:g}")

            supplier = clean_text(r["Supplier"]).upper() or None
            if supplier and supplier not in self.out.suppliers:
                self._raise("ITM", S, idx, "Supplier", supplier, "Supplier not in supplier master", "OPEN")
                continue

            self.out.items[code] = {
                "code": code, "name": name, "group": group, "uom": uom, "buy_rate": buy_rate,
                "sell_rate": parse_number(r["Selling Price"]), "supplier": supplier,
                "supplier_part_no": self._decision("supplier_part_numbers", code),
                "lead_days": self.out.suppliers[supplier]["lead_days"] if supplier else 0,
                "reorder_level": parse_number(r["Min Stock"]) or 0,
                "reorder_qty": parse_number(r["Order Qty"]) or 0,
            }

    # ------------------------------------------------------------------ customers
    def customers(self):
        S = "Customers"
        seen_gstin = {}
        for idx, r in self.sheets[S].iterrows():
            code, name = clean_text(r["Cust Code"]).upper(), clean_text(r["Customer"])
            gstin = clean_text(r["GSTIN"]).upper()
            if not code:
                target = self._decision("customer_aliases", name.lower())
                hint = f"Missing customer code; same GSTIN as {seen_gstin[gstin]}" if gstin in seen_gstin \
                    else "Missing customer code"
                if target:
                    self._raise("CUS", S, idx, "Cust Code", name, hint, f"excluded: merged into {target} (client decision)")
                else:
                    self._raise("CUS", S, idx, "Cust Code", name, hint, "OPEN")
                continue
            if name.isupper():   # title-casing would mangle brands like "GreenAcre", so ask the client
                fixed = self._decision("customer_name_fixes", code)
                self._raise("CUS", S, idx, "Customer", r["Customer"], "Name in all caps",
                            f"client decision: {fixed}" if fixed else "OPEN")
                if not fixed:
                    continue
                name = fixed
            if gstin and not gstin_valid(gstin):
                self._raise("CUS", S, idx, "GSTIN", gstin, "GSTIN fails checksum", "OPEN")
                continue
            state = clean_text(r["State"]) or self._decision("customer_state_fixes", code)
            if not clean_text(r["State"]):
                self._raise("CUS", S, idx, "State", "", "Missing state (needed for GST place of supply)",
                            f"client decision: {state}" if state else "OPEN")
                if not state:
                    continue
            seen_gstin[gstin] = code
            self.out.customers[code] = {"code": code, "name": name, "city": clean_text(r["City"]),
                                        "state": state, "gstin": gstin, "segment": clean_text(r["Segment"])}

    # ------------------------------------------------------------------ BOMs
    def _resolve_item(self, raw):
        """Map a free-text item reference to an item code. Returns (code, how) or (None, None)."""
        code = clean_text(raw).upper()
        if code in self.out.items:
            return code, None if code == clean_text(raw) else "auto-fixed"
        alias = self._decision("item_aliases", clean_text(raw).lower())
        if alias in self.out.items:
            return alias, "client decision"
        return None, None

    def boms(self):
        S = "Parts Lists"
        for idx, r in self.sheets[S].iterrows():
            parent, _ = self._resolve_item(r["Assembly"])
            comp, how = self._resolve_item(r["Part"])
            if not parent or not comp:
                bad = "Assembly" if not parent else "Part"
                self._raise("BOM", S, idx, bad, r[bad], "Item not in item master", "OPEN")
                continue
            if how:
                self._raise("BOM", S, idx, "Part", r["Part"], "Part referenced by name, not code", f"{how}: {comp}")
            qty = parse_number(r["Qty Per"])
            if not qty or qty <= 0:
                self._raise("BOM", S, idx, "Qty Per", r["Qty Per"], "Invalid quantity", "OPEN")
                continue
            if clean_text(r["Qty Per"]) != f"{qty:g}":
                self._raise("BOM", S, idx, "Qty Per", r["Qty Per"], "Unit typed into quantity", f"auto-fixed: {qty:g}")
            self.out.boms.setdefault(parent, []).append((comp, qty))

    # ------------------------------------------------------------------ opening stock
    def stock(self):
        S = "Stock Count"
        for idx, r in self.sheets[S].iterrows():
            raw = clean_text(r["Item"])
            if raw.upper() in self.excluded_items:
                self._raise("STK", S, idx, "Item", raw, f"Stock of {self.excluded_items[raw.upper()]} item",
                            "excluded: not migrated")
                continue
            if raw.upper() in self.d.get("excluded_stock_codes", {}):
                self._raise("STK", S, idx, "Item", raw, "Item not in item master",
                            f"excluded: {self.d['excluded_stock_codes'][raw.upper()]}")
                continue
            code, how = self._resolve_item(raw)
            if not code:
                self._raise("STK", S, idx, "Item", raw, "Item not in item master", "OPEN")
                continue
            if how:
                self._raise("STK", S, idx, "Item", raw, "Non-standard item code", f"{how}: {code}")

            qty = parse_number(r["Qty"])
            if qty is None:
                self._raise("STK", S, idx, "Qty", r["Qty"], "Unparseable quantity", "OPEN")
                continue
            if qty < 0:
                rejected = self.d.get("negative_stock_lines") == "reject"
                self._raise("STK", S, idx, "Qty", r["Qty"], "Negative quantity on a count sheet",
                            "client decision: line rejected, physical count stands" if rejected else "OPEN")
                continue
            if clean_text(r["Qty"]) != f"{qty:g}":
                self._raise("STK", S, idx, "Qty", r["Qty"], "Unit typed into quantity", f"auto-fixed: {qty:g}")

            loc = clean_text(r["Location"]).lower()
            wh = self.d.get("warehouse_map", {}).get(loc)
            if not wh:
                self._raise("STK", S, idx, "Location", r["Location"], "Unknown location", "OPEN")
                continue
            key = (code, wh)
            self.out.stock[key] = self.out.stock.get(key, 0) + qty

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _dup_hint(name, known: dict, base: str) -> str:
        best = max(known.items(), key=lambda kv: similarity(name, kv[1]), default=None)
        if best and similarity(name, best[1]) >= 0.5:
            return f"{base}; probable duplicate of {best[0]} ({best[1]})"
        return base


def load_decisions(path: Path) -> dict:
    return json.loads(path.read_text()) if path and path.exists() else {}


def cleanse(workbook: Path, decisions: dict | None = None) -> CleanData:
    return Cleanser(workbook, decisions).run()
