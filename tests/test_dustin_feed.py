import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import dustin_feed as d  # noqa: E402

PAGE = (Path(__file__).parent / "fixtures" / "dustin_sample.html").read_text(encoding="utf-8")


def test_leser_varer_fra_json_i_siden():
    prods, hits = d.parse_page(PAGE)
    assert len(prods) == 18 and hits == 114
    rows = d.rows_from_products(prods)
    assert len(rows) == 18
    a = rows[0]
    assert a[0] == "https://www.dustin.no/product/5011244163/pla-pro-175-mm-svart-1-kg"
    assert a[2] == "Flashforge PLA Pro 1.75 mm svart 1 kg" and a[3] == "Svart"
    assert a[4] == "269"  # inkl. mva (215 + 25 %)
    assert a[5] == "" and a[6] == "47"
    assert a[1].endswith("/d200001001407515/d200001001407515.jpg")


def test_filtrerer_bort_tilbehor_og_utsolgt():
    fil = {"id": "1", "displayName": "PLA 1,75 mm", "manufacturerName": "X", "nameSlug": "a", "promotedSpecifications": [
        {"name": "Printmateriale", "value": "PLA"}, {"name": "Tykkhet", "value": "1.75 mm"}],
        "price": {"priceIncludingVat": 100, "price": 80}, "availability": {"isAvailableForSale": False}}
    dyse = dict(fil, id="2", displayName="Dyse 0,4 mm", promotedSpecifications=[])
    rows = d.rows_from_products([fil, dyse])
    assert len(rows) == 1 and rows[0][6] == "Utsolgt" and rows[0][2] == "X PLA 1,75 mm"


def test_forpris_regnes_inkl_mva():
    p = {"id": "1", "displayName": "PETG", "manufacturerName": "X", "nameSlug": "a", "promotedSpecifications": [
        {"name": "Printmateriale", "value": "PETG"}, {"name": "Tykkhet", "value": "1.75 mm"}],
        "price": {"price": 80, "priceIncludingVat": 100, "originalPrice": 120, "isCampaign": True},
        "availability": {"isAvailableForSale": True, "internalStock": {"quantity": 0}}}
    r = d.row(p)
    assert r[4] == "100" and r[5] == "150" and r[6] == "På lager"


PAGE2 = (Path(__file__).parent / "fixtures" / "dustin_sample_p2.html").read_text(encoding="utf-8")


def test_sider_slaas_sammen_selv_om_de_overlapper():
    calls = []

    def fake(url):
        calls.append(url)
        return PAGE if "page=" not in url else PAGE2 if url.endswith("page=2") else "<html></html>"

    got = d.all_pages(fake, max_pages=5, delay=0)
    ids = [p["id"] for p in got]
    assert len(ids) == len(set(ids)) == 29  # 18 på side 1 + 11 nye på side 2 (7 gjentas)
    assert len(calls) == 3  # side 3 er tom, og da stopper vi


def test_flere_farger_blir_flerfarget():
    prods, _ = d.parse_page(PAGE)
    rows = {r[0].rsplit("/", 1)[1]: r for r in d.rows_from_products(prods)}
    assert rows["pla-silk-dual-rosagul-175mm-1kg"][3] == "Flerfarget"
