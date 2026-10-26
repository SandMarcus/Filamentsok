import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.build import apply_sale, smart_case  # noqa: E402

CFG = {"id": "t", "columns": {"onsale": "onsale", "sale_price": "ny pris"}}


def rep():
    return {"merknader": [], "skipped": Counter()}


def test_sale_uses_lowest_price_and_keeps_old():
    o = {"price": 239.0, "was": 0}
    apply_sale(o, "KR199,00", "Tilbud!", CFG, rep(), "x")
    assert (o["price"], o["was"]) == (199.0, 239.0)


def test_second_price_ignored_when_not_marked_as_sale():
    o, r = {"price": 209.0, "was": 0}, rep()
    apply_sale(o, "KR619,00", "", CFG, r, "x")
    assert (o["price"], o["was"]) == (209.0, 0) and r["merknader"]


def test_absurd_sale_is_ignored_and_reported():
    o, r = {"price": 150.0, "was": 0}, rep()
    apply_sale(o, "KR2 879,00", "Tilbud!", CFG, r, "x")
    assert (o["price"], o["was"]) == (150.0, 0) and r["merknader"]


def test_smart_case():
    assert smart_case("CREALITY HYPER PLA – 1,75MM – 1KG") == "Creality Hyper PLA – 1,75 mm – 1 kg"
    assert smart_case("Bambu Lab PLA – 1 kg") == "Bambu Lab PLA – 1 kg"
