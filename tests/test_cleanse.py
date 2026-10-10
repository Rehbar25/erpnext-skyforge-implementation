"""Migration cleansing: parsers, validation rules, and recovery of the true master data."""

from pathlib import Path

import pytest

from migration.cleanse import (cleanse, gstin_valid, load_decisions, normalise_phone, parse_lead_days,
                               parse_number)
from migration.load import bom_build_order, rolled_up_cost
from tools import generate_legacy_data as truth

ROOT = Path(__file__).resolve().parent.parent
WORKBOOK = ROOT / "data" / "legacy" / "SkyForge_Master_Data.xlsx"


@pytest.fixture(scope="module", autouse=True)
def workbook():
    truth.main()                     # regenerate so tests never depend on a stale file


@pytest.fixture(scope="module")
def clean():
    return cleanse(WORKBOOK, load_decisions(ROOT / "migration" / "decisions.json"))


@pytest.fixture(scope="module")
def first_pass():
    return cleanse(WORKBOOK, None)


@pytest.mark.parametrize("raw,expected", [
    ("₹1,450", 1450), ("Rs. 950", 950), ("950.00", 950), ("52 pcs", 52), ("1 m", 1),
    (12.0, 12), ("-2", -2), ("approx 38k", None), ("", None), (None, None)])
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


@pytest.mark.parametrize("raw,expected", [(28, 28), ("21 days", 21), ("4 weeks", 28), ("soon", None)])
def test_parse_lead_days(raw, expected):
    assert parse_lead_days(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("+91 98480 12345", "+91-9848012345"), ("09849012346", "+91-9849012346"),
    ("040-27654321", "+91-4027654321"), ("12345", None)])
def test_normalise_phone(raw, expected):
    assert normalise_phone(raw) == expected


def test_gstin_checksum():
    good = truth.gstin("Telangana", "AABCS1000K")
    assert gstin_valid(good)
    assert not gstin_valid(good[:-1] + ("0" if good[-1] != "0" else "1"))
    assert not gstin_valid("NOT-A-GSTIN")


def test_first_pass_blocks_on_real_root_causes(first_pass):
    issues = {(e.sheet, e.issue.split(";")[0]) for e in first_pass.open_exceptions}
    assert ("Suppliers", "GSTIN fails checksum") in issues
    assert ("Items", "Missing item code") in issues
    assert ("Items", "Unparseable price") in issues
    assert ("Stock Count", "Negative quantity on a count sheet") in issues
    dup_hint = [e for e in first_pass.open_exceptions if "probable duplicate of MTR-2306" in e.issue]
    assert dup_hint, "fuzzy matcher should point the nameless motor row at MTR-2306"


def test_decisions_resolve_everything(clean):
    assert clean.open_exceptions == []


def test_recovers_true_item_master(clean):
    expected = {code: (name, group, uom) for code, name, group, uom, *_ in truth.CLEAN_ITEMS}
    assert {c: (i["name"], i["group"], i["uom"]) for c, i in clean.items.items()} == expected
    for code, *_, rate, _sup, _rol, _roq in truth.CLEAN_ITEMS:
        if clean.items[code]["group"] == "Components":
            assert clean.items[code]["buy_rate"] == rate, code


def test_obsolete_and_duplicates_excluded(clean):
    assert "FC-F4" not in clean.items
    assert len(clean.suppliers) == len(truth.CLEAN_SUPPLIERS)
    assert len(clean.customers) == len(truth.CLEAN_CUSTOMERS)
    assert clean.customers["CUST-GREE"]["name"] == "GreenAcre Agritech"   # ISS-08


def test_invalid_gstin_loaded_blank(clean):
    assert clean.suppliers["SUP-FAST"]["gstin"] == ""
    assert all(gstin_valid(s["gstin"]) for c, s in clean.suppliers.items() if c != "SUP-FAST")


def test_recovers_boms_and_stock(clean):
    assert clean.boms == {p: [(c, float(q)) for c, q in comps] for p, comps in truth.CLEAN_BOMS.items()}
    stock = {code: qty for (code, _wh), qty in clean.stock.items()}
    assert stock == {k: float(v) for k, v in truth.CLEAN_STOCK.items()}
    assert clean.stock[("SF-Q250", "Finished Goods - SFD")] == 2


def test_cost_rollup_and_build_order(clean):
    assert rolled_up_cost("SA-PWR-Q250", clean) == 10295
    assert rolled_up_cost("SF-Q250", clean) == 41419
    assert rolled_up_cost("SF-X450", clean) == 99486
    order = bom_build_order(clean.boms)
    assert order.index("SA-PWR-Q250") < order.index("SF-Q250")
    assert order.index("SA-FRM-X450") < order.index("SF-X450")


def test_every_exception_has_a_resolution(clean):
    allowed = ("auto-fixed", "client decision", "excluded", "accepted")
    assert all(e.resolution.split(":")[0] in allowed for e in clean.exceptions)
