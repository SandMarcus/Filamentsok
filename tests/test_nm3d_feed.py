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


def test_stratum_filter_og_konvertering(tmp_path):
    import json
    from tools import stratum_feed as sf
    from tools import nm3d_feed as nf
    prods = json.load(open(Path(__file__).parent / "fixtures" / "nm3d_sample.json", encoding="utf-8"))
    for p in prods:
        p["categories"] = [{"slug": "3d-print-filament"}]
    assert sf.is_filament(prods[0]) and sf.is_filament({"categories": [{"slug": "3d-print-filament-peek"}]})
    assert not sf.is_filament({"categories": [{"slug": "3d-printer-filament"}]})  # printere ligger her
    out = tmp_path / "s.csv"
    assert nf.convert(prods, out, fetch=None, keep=sf.is_filament) > 0


def test_vekt_og_farge_fra_attributter():
    p = {"id": 1, "name": "Kexcelled K11 PEEK", "type": "simple", "permalink": "https://x/p/", "images": [], "tags": [],
         "prices": {"price": "549000", "regular_price": "549000", "currency_minor_unit": 2}, "is_in_stock": True,
         "stock_availability": {"text": "10+ på lager (3-5 dager levering)"},
         "attributes": [{"name": "Vekt", "terms": [{"name": "500g"}]}, {"name": "Farge", "terms": [{"name": "Natural"}]}]}
    row = nm3d_feed.rows_for(p)[0]
    assert row[2] == "Kexcelled K11 PEEK 500g" and row[3] == "Natural" and row[4] == "5490" and row[6] == "10+ på lager"
