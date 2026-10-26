import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import nm3d_feed  # noqa: E402

SAMPLE = json.loads((ROOT / "tests" / "fixtures" / "nm3d_sample.json").read_text(encoding="utf-8"))


def rows(tmp_path, fetch=None):
    out = tmp_path / "n.csv"
    nm3d_feed.convert(SAMPLE, out, fetch=fetch)
    return list(csv.DictReader(out.open(encoding="utf-8")))


def test_resin_is_dropped_and_variants_become_rows(tmp_path):
    r = rows(tmp_path)
    names = " ".join(x["Navn"] for x in r)
    assert "Resin" not in names and "Dental" not in names
    assert sum("Creality Ender" in x["Navn"] for x in r) == 7  # 7 farger
    assert all(x["Pris"] for x in r)


def test_sale_gets_original_price_and_weight_from_tag(tmp_path):
    r = rows(tmp_path)
    lite = [x for x in r if "ePLA" in x["Navn"]]
    assert lite and all(x["Pris"] == "139" and x["Førpris"] == "179" for x in lite)
    colorfabb = next(x for x in r if "XT-CF20" in x["Navn"])
    assert "750g" in colorfabb["Navn"] and colorfabb["Pris"] == "577" and colorfabb["Lager"] == "Utsolgt"


def test_variant_prices_come_from_variant_products(tmp_path):
    def fetch(url):
        if "type=variation" in url:
            raise SystemExit("ikke støttet")
        vid = int(url.rsplit("/", 1)[1])
        pr = {"price": "19900", "regular_price": "19900", "currency_minor_unit": 2}
        return {"id": vid, "prices": pr, "on_sale": False, "is_in_stock": True, "stock_availability": {"text": "3 på lager"}, "images": []}
    r = rows(tmp_path, fetch)
    ender = [x for x in r if "Creality Ender" in x["Navn"]]
    assert all(x["Pris"] == "199" and x["Lager"] == "3 på lager" for x in ender)


def _p(*slugs):
    return {"categories": [{"slug": s} for s in slugs]}


def test_filter_kategorier():
    from tools import nm3d_feed as n
    assert n.is_filament(_p("filament-og-resin", "raise3d-filament-og-resin"))
    assert n.is_filament(_p("filament"))
    assert not n.is_filament(_p("filament-lagring", "tilbehor-og-ekstradeler"))
    assert not n.is_filament(_p("resin"))
    assert not n.is_filament(_p("rengjoring"))
