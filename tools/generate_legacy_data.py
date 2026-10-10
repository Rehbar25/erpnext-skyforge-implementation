"""Generate SkyForge Drones' legacy master data as the client would hand it over.

Produces data/legacy/SkyForge_Master_Data.xlsx: the store keeper's and sales team's
working spreadsheets, complete with the data-quality problems found in real handovers
(duplicates, mixed units, prices stored as text, unknown codes, ...).

The clean reference data lives here too (CLEAN_*), so tests can verify that the
migration pipeline recovers it. The migration code itself never imports this module.

Run:  python tools/generate_legacy_data.py
"""

from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "data" / "legacy" / "SkyForge_Master_Data.xlsx"

# --------------------------------------------------------------------------- suppliers
# code, name, city, lead_days, contact email
CLEAN_SUPPLIERS = [
    ("SUP-AERO", "AeroParts Imports Ltd", "Mumbai", 28, "orders@aeroparts.example"),
    ("SUP-VOLT", "VoltCell Energy", "Bengaluru", 21, "sales@voltcell.example"),
    ("SUP-CARB", "CarbonWorks India", "Pune", 10, "info@carbonworks.example"),
    ("SUP-FAST", "Hyderabad Fasteners Co", "Hyderabad", 3, "hfc@fasteners.example"),
    ("SUP-OPTI", "OptiSight Cameras", "Chennai", 14, "b2b@optisight.example"),
    ("SUP-WIRE", "WireTech Electricals", "Hyderabad", 5, "wiretech@wiretech.example"),
]

# --------------------------------------------------------------------------- items
# code, name, group, uom, rate, supplier, reorder_level, reorder_qty
CLEAN_ITEMS = [
    ("MTR-2306", "Brushless Motor 2306 2450KV", "Components", "Nos", 1450, "SUP-AERO", 40, 120),
    ("MTR-3508", "Brushless Motor 3508 700KV", "Components", "Nos", 3200, "SUP-AERO", 24, 60),
    ("ESC-30A", "ESC 30A BLHeli_32", "Components", "Nos", 950, "SUP-AERO", 40, 120),
    ("ESC-40A", "ESC 40A BLHeli_32", "Components", "Nos", 1350, "SUP-AERO", 24, 60),
    ("FC-F7", "Flight Controller F7", "Components", "Nos", 6800, "SUP-AERO", 10, 30),
    ("FC-H7", "Flight Controller H7", "Components", "Nos", 11500, "SUP-AERO", 4, 10),
    ("GPS-M10", "GPS Module M10", "Components", "Nos", 2100, "SUP-AERO", 14, 40),
    ("RX-ELRS", "ELRS 2.4GHz Receiver", "Components", "Nos", 1200, "SUP-AERO", 14, 40),
    ("PDB-120", "Power Distribution Board 120A", "Components", "Nos", 650, "SUP-WIRE", 10, 30),
    ("PDB-200", "Power Distribution Board 200A", "Components", "Nos", 1100, "SUP-WIRE", 4, 10),
    ("WIRE-14AWG", "Silicone Wire 14AWG", "Components", "Meter", 45, "SUP-WIRE", 20, 100),
    ("PRP-5045", "Propeller 5045 (pair)", "Components", "Pair", 120, "SUP-WIRE", 20, 60),
    ("PRP-1045", "Propeller 10x4.5 (pair)", "Components", "Pair", 380, "SUP-WIRE", 10, 30),
    ("FRM-Q250-ARM", "Carbon Arm 250-class", "Components", "Nos", 420, "SUP-CARB", 40, 120),
    ("FRM-Q250-PLT", "Carbon Centre Plate 250-class", "Components", "Nos", 780, "SUP-CARB", 20, 60),
    ("FRM-X450-ARM", "Carbon Arm 450-class", "Components", "Nos", 690, "SUP-CARB", 24, 60),
    ("FRM-X450-PLT", "Carbon Centre Plate 450-class", "Components", "Nos", 1450, "SUP-CARB", 8, 20),
    ("HW-STANDOFF", "M3 Aluminium Standoff 30mm", "Components", "Nos", 12, "SUP-FAST", 100, 500),
    ("HW-SCREW-M3", "M3 Hex Screw 8mm", "Components", "Nos", 2, "SUP-FAST", 300, 1000),
    ("BAT-4S1500", "LiPo Battery 4S 1500mAh", "Components", "Nos", 2900, "SUP-VOLT", 10, 30),
    ("BAT-6S5000", "LiPo Battery 6S 5000mAh", "Components", "Nos", 9800, "SUP-VOLT", 4, 10),
    ("CAM-4K", "Inspection Camera 4K", "Components", "Nos", 14500, "SUP-OPTI", 6, 15),
    ("CAM-MAP", "Mapping Camera 20MP", "Components", "Nos", 38000, "SUP-OPTI", 2, 6),
    ("SA-PWR-Q250", "Power Pack - Q250", "Sub Assemblies", "Nos", 0, None, 0, 0),
    ("SA-PWR-X450", "Power Pack - X450", "Sub Assemblies", "Nos", 0, None, 0, 0),
    ("SA-FRM-Q250", "Frame Kit - Q250", "Sub Assemblies", "Nos", 0, None, 0, 0),
    ("SA-FRM-X450", "Frame Kit - X450", "Sub Assemblies", "Nos", 0, None, 0, 0),
    ("SF-Q250", "SF-Q250 Inspection Quad", "Products", "Nos", 68000, None, 0, 0),
    ("SF-X450", "SF-X450 Survey Hex", "Products", "Nos", 145000, None, 0, 0),
]

# --------------------------------------------------------------------------- BOMs
# parent -> [(component, qty)]
CLEAN_BOMS = {
    "SA-PWR-Q250": [("MTR-2306", 4), ("ESC-30A", 4), ("PDB-120", 1), ("WIRE-14AWG", 1)],
    "SA-PWR-X450": [("MTR-3508", 6), ("ESC-40A", 6), ("PDB-200", 1), ("WIRE-14AWG", 2)],
    "SA-FRM-Q250": [("FRM-Q250-ARM", 4), ("FRM-Q250-PLT", 2), ("HW-STANDOFF", 8), ("HW-SCREW-M3", 24)],
    "SA-FRM-X450": [("FRM-X450-ARM", 6), ("FRM-X450-PLT", 2), ("HW-STANDOFF", 12), ("HW-SCREW-M3", 36)],
    "SF-Q250": [("SA-FRM-Q250", 1), ("SA-PWR-Q250", 1), ("FC-F7", 1), ("GPS-M10", 1),
                ("PRP-5045", 2), ("BAT-4S1500", 1), ("RX-ELRS", 1), ("CAM-4K", 1)],
    "SF-X450": [("SA-FRM-X450", 1), ("SA-PWR-X450", 1), ("FC-H7", 1), ("GPS-M10", 1),
                ("PRP-1045", 3), ("BAT-6S5000", 1), ("RX-ELRS", 1), ("CAM-MAP", 1)],
}

# --------------------------------------------------------------------------- opening stock
# Several components sit below reorder level on purpose, so MRP and reorder alerts have work to do.
CLEAN_STOCK = {
    "MTR-2306": 52, "MTR-3508": 30, "ESC-30A": 18, "ESC-40A": 26, "FC-F7": 12, "FC-H7": 5,
    "GPS-M10": 6, "RX-ELRS": 20, "PDB-120": 15, "PDB-200": 6, "WIRE-14AWG": 85,
    "PRP-5045": 44, "PRP-1045": 21, "FRM-Q250-ARM": 64, "FRM-Q250-PLT": 30,
    "FRM-X450-ARM": 36, "FRM-X450-PLT": 10, "HW-STANDOFF": 420, "HW-SCREW-M3": 1150,
    "BAT-4S1500": 9, "BAT-6S5000": 4, "CAM-4K": 8, "CAM-MAP": 3, "SF-Q250": 2,
}

# --------------------------------------------------------------------------- customers
# code, name, city, state, segment
CLEAN_CUSTOMERS = [
    ("CUST-SUNG", "SunGrid Solar Parks", "Anantapur", "Andhra Pradesh", "Solar"),
    ("CUST-DECC", "Deccan Infra Inspections", "Hyderabad", "Telangana", "Infrastructure"),
    ("CUST-TERR", "TerraMap Surveys", "Nagpur", "Maharashtra", "Survey"),
    ("CUST-HYDL", "HydroLine Pipelines", "Vadodara", "Gujarat", "Infrastructure"),
    ("CUST-COAS", "Coastal Wind Energy", "Tuticorin", "Tamil Nadu", "Solar"),
    ("CUST-GREE", "GreenAcre Agritech", "Warangal", "Telangana", "Agriculture"),
    ("CUST-NIRM", "Nirmaan Constructions", "Bengaluru", "Karnataka", "Infrastructure"),
]

STATE_CODES = {"Andhra Pradesh": "37", "Telangana": "36", "Maharashtra": "27", "Gujarat": "24",
               "Tamil Nadu": "33", "Karnataka": "29"}
GST_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin(state: str, pan: str) -> str:
    """Build a structurally valid GSTIN (state code + PAN + entity no. + 'Z' + checksum)."""
    body = f"{STATE_CODES[state]}{pan}1Z"
    total = 0
    for i, ch in enumerate(body):
        product = GST_CHARS.index(ch) * (2 if i % 2 else 1)
        total += product // 36 + product % 36
    return body + GST_CHARS[(36 - total % 36) % 36]


def pan_for(i: int) -> str:
    return f"AAB{'CDEFGHJ'[i % 7]}S{1000 + 37 * i:04d}{'KLMNPQR'[i % 7]}"


# --------------------------------------------------------------------------- messy sheets
def items_sheet() -> pd.DataFrame:
    uom_variants = {"Nos": ["Nos", "nos", "pcs", "PCS", "unit", "Pcs"], "Pair": ["pair", "Pairs"],
                    "Meter": ["mtr", "m"]}
    rows = []
    for i, (code, name, group, uom, rate, sup, rol, roq) in enumerate(CLEAN_ITEMS):
        variants = uom_variants[uom]
        bought = group == "Components"
        price = "" if not bought else (f"₹{rate:,}" if i % 3 == 0 else
                                       f"Rs. {rate}" if i % 3 == 1 else f"{rate}.00")
        rows.append({"Item Code": code, "Item Name": name, "Category": group,
                     "Unit": variants[i % len(variants)], "Last Purchase Price": price,
                     "Selling Price": rate if group == "Products" else "",
                     "Supplier": sup or "", "Min Stock": rol or "", "Order Qty": roq or "",
                     "Status": "Active", "Remarks": ""})

    # Defects a store keeper's sheet accumulates over the years
    rows[2]["Item Code"] = "esc-30a"                          # lower-case code
    rows[4]["Item Name"] = "  Flight Controller F7 "          # stray whitespace
    rows[10]["Item Code"] = ""                                # wire: code never assigned
    rows[17]["Category"] = ""                                 # standoff: no category
    rows[22]["Last Purchase Price"] = "approx 38k"            # unparseable price
    rows.insert(1, {"Item Code": "", "Item Name": "2306 motor 2450KV", "Category": "Components",
                    "Unit": "pcs", "Last Purchase Price": "1500", "Supplier": "SUP-AERO",
                    "Min Stock": 40, "Order Qty": 100, "Status": "Active",
                    "Remarks": "same as MTR-2306?"})          # duplicate of MTR-2306
    rows.append({"Item Code": "FC-F4", "Item Name": "Flight Controller F4 (old)",
                 "Category": "Components", "Unit": "Nos", "Last Purchase Price": "3900",
                 "Supplier": "SUP-AERO", "Min Stock": "", "Order Qty": "", "Status": "Obsolete",
                 "Remarks": "discontinued 2025"})              # obsolete, must not migrate
    rows.append(dict(next(r for r in rows if r["Item Code"] == "RX-ELRS")))  # exact duplicate row
    return pd.DataFrame(rows)


def suppliers_sheet() -> pd.DataFrame:
    phones = ["+91 98480 12345", "09849012346", "9849012347", "+91-9849012348", "98490 12349",
              "040-27654321"]
    rows = []
    for i, (code, name, city, lead, email) in enumerate(CLEAN_SUPPLIERS):
        state = {"Mumbai": "Maharashtra", "Bengaluru": "Karnataka", "Pune": "Maharashtra",
                 "Hyderabad": "Telangana", "Chennai": "Tamil Nadu"}[city]
        rows.append({"Supplier ID": code, "Supplier Name": name, "City": city,
                     "GSTIN": gstin(state, pan_for(i)), "Phone": phones[i], "Email": email,
                     "Lead Time": f"{lead} days" if i % 2 else lead})
    rows[3]["GSTIN"] = rows[3]["GSTIN"][:-1] + ("0" if rows[3]["GSTIN"][-1] != "0" else "1")  # bad checksum
    rows[4]["Email"] = ""
    rows.append({"Supplier ID": "", "Supplier Name": "Aeroparts Imports", "City": "Mumbai",
                 "GSTIN": rows[0]["GSTIN"], "Phone": "9848012345", "Email": "",
                 "Lead Time": "4 weeks"})                     # duplicate of SUP-AERO
    return pd.DataFrame(rows)


def customers_sheet() -> pd.DataFrame:
    rows = []
    for i, (code, name, city, state, segment) in enumerate(CLEAN_CUSTOMERS):
        rows.append({"Cust Code": code, "Customer": name, "City": city, "State": state,
                     "GSTIN": gstin(state, pan_for(i + 10)), "Segment": segment})
    rows[2]["State"] = ""                                      # missing state
    rows[5]["Customer"] = "GREENACRE AGRITECH "                # inconsistent casing
    rows.append({"Cust Code": "", "Customer": "Sungrid Solar Parks Pvt Ltd", "City": "Anantapur",
                 "State": "Andhra Pradesh", "GSTIN": rows[0]["GSTIN"], "Segment": "Solar"})
    return pd.DataFrame(rows)


def stock_sheet() -> pd.DataFrame:
    warehouses = ["Store", "stores", "Main Store", "Store "]
    rows = [{"Item": code, "Qty": qty if i % 4 else f"{qty} pcs",
             "Location": "FG Shelf" if code.startswith("SF-") else warehouses[i % 4],
             "Counted By": "Ramesh"}
            for i, (code, qty) in enumerate(CLEAN_STOCK.items())]
    rows[9]["Item"] = "pdb 200"                                 # sloppy code
    rows.append({"Item": "FC-F4", "Qty": 3, "Location": "Store", "Counted By": "Ramesh"})
    rows.append({"Item": "MTR-2207", "Qty": 7, "Location": "Store",
                 "Counted By": "Ramesh"})                       # not in item master
    rows.append({"Item": "BAT-4S1500", "Qty": -2, "Location": "Store",
                 "Counted By": "Ramesh"})                       # negative adjustment line
    return pd.DataFrame(rows)


def bom_sheet() -> pd.DataFrame:
    rows = [{"Assembly": parent, "Part": comp, "Qty Per": qty}
            for parent, comps in CLEAN_BOMS.items() for comp, qty in comps]
    rows[0]["Part"] = "Motor 2306"                              # referenced by old name
    rows[3]["Qty Per"] = "1 m"                                  # unit typed into qty
    return pd.DataFrame(rows)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT, engine="openpyxl") as xl:
        items_sheet().to_excel(xl, sheet_name="Items", index=False)
        suppliers_sheet().to_excel(xl, sheet_name="Suppliers", index=False)
        customers_sheet().to_excel(xl, sheet_name="Customers", index=False)
        stock_sheet().to_excel(xl, sheet_name="Stock Count", index=False)
        bom_sheet().to_excel(xl, sheet_name="Parts Lists", index=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
