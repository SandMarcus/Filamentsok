import json
from pathlib import Path

from src import build
from src.csvparse import parse_price, parse_stock, weight_kg
from src.grouping import group


def test_price():
    assert parse_price("1 590,00 kr") == 1590.0
    assert parse_price("kr 9.999,-") == 9999.0
    assert parse_price("299,90") == 299.9
    assert parse_price("749,-") == 749.0
    assert parse_price("") is None


def test_stock():
    assert parse_stock("Utsolgt") == "out"
    assert parse_stock("Utsolgt, men kan bestilles") == "order"
    assert parse_stock("25+ på lager") == "25+"
    assert parse_stock("10-25 på lager") == "10-25"
    assert parse_stock("27") == "27"
    assert parse_stock("På lager (3-5 dager levering)") == "yes"
    assert parse_stock("Ubekreftet 22.10.2026") == "soon:22.10.2026"
    assert parse_stock("Usikker") is None
    assert parse_stock("") is None


def test_weight_rules():
    assert weight_kg("eSun PLA+ (5kg) Black", default_kg=1) == 5.0
    assert weight_kg("PolySmart PLA Super Pack (10 ruller) Black", rolls_as_kg=True, default_kg=1) == 10.0
    assert weight_kg("Filamentpm PLA+ Pastel pack (4x0,5kg)", default_kg=1) == 2.0
    assert weight_kg("Azurefilm PLA Original Red", default_kg=1) == 1.0
    assert weight_kg("Bambu Lab PLA Basic Color Trial Set 12 farger", default_kg=1) is None
    assert weight_kg("Azurefilm PLA Original Red") is None
    assert weight_kg("Bambu Lab PLA Basic - Black", default_kg_brands={"Bambu Lab": 1}, brand="Bambu Lab", material="PLA") == 1.0
    assert weight_kg("Bambu Lab PAHT-CF Black", default_kg_brands={"Bambu Lab": 1}, brand="Bambu Lab", material="PAHT") is None


def offer(store, name, price, kg=1.0, brand="Bambu Lab", mat="PLA", add=None):
    return {"store": store, "name": name, "price": price, "kg": kg, "brand": brand, "mat": mat, "add": add}


def test_group_same_product_across_stores():
    g = group([offer("elefun", "Bambu Lab PLA Basic 1kg - Black", 198), offer("poly", "Bambu Lab PLA Basic Black", 219)])
    assert len(g) == 1 and [o["store"] for o in g[0]] == ["elefun", "poly"]


def test_group_keeps_shades_and_weights_apart():
    g = group([offer("elefun", "Bambu Lab PLA Basic - Cocoa Brown", 1), offer("poly", "Bambu Lab PLA Basic - Brown", 1),
               offer("elefun", "Bambu Lab PLA Basic - Black", 1, kg=0.5), offer("poly", "Bambu Lab PLA Basic - Black", 1)])
    assert all(len(x) == 1 for x in g)


def test_group_never_merges_unknown_weight():
    g = group([offer("elefun", "X PLA Black", 1, kg=None), offer("poly", "X PLA Black", 1, kg=None)])
    assert len(g) == 2


def test_group_same_store_duplicates_stay_separate():
    g = group([offer("kjell", "Addnorth E-PLA Hvit", 280, brand="Addnorth"), offer("kjell", "Addnorth E-PLA 1000 g Hvit", 300, brand="Addnorth"),
               offer("poly", "add:north E-PLA (1kg) White", 209, brand="Addnorth")])
    sizes = sorted(len(x) for x in g)
    assert sizes == [1, 2]


def test_full_build(tmp_path):
    out = tmp_path / "dist"
    assert build.main(["--out", str(out)]) == 0
    data = json.loads((out / "products.json").read_text(encoding="utf-8"))
    assert data["v"] == 1 and len(data["products"]) > 1000
    assert set(data["stores"]) >= {"kjell", "poly", "elefun", "stratum", "clas"}
    for p in data["products"]:
        assert p["offers"] and all("s" in o for o in p["offers"])
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "__BUILD__" not in html
    assert (out / ".nojekyll").exists()


def test_bad_column_gives_helpful_error(tmp_path):
    cfg = json.loads(Path(build.ROOT, "config", "stores.json").read_text(encoding="utf-8"))
    cfg["stores"] = [cfg["stores"][0]]
    cfg["stores"][0]["columns"]["price"] = "FinnesIkke"
    p = tmp_path / "s.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    try:
        build.main(["--config", str(p), "--out", str(tmp_path / "o")])
    except build.ConfigError as e:
        assert "FinnesIkke" in str(e) and "Kolonner i filen" in str(e)
    else:
        raise AssertionError("forventet ConfigError")
