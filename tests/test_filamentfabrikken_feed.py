import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import filamentfabrikken_feed as f  # noqa: E402

DATA = json.loads((Path(__file__).parent / "fixtures" / "filamentfabrikken_sample.json").read_text(encoding="utf-8"))


def test_rader():
    rows = f.rows_from_products(DATA["products"])
    assert len(rows) == 3  # tørkeren er ikke filament; produkt 2 har to varianter
    a, b, c = rows
    assert a[0] == "https://filamentfabrikken.no/products/bambu-lab-pla-basic-black" and a[2] == "Bambu Lab: PLA Basic, Black"
    assert a[4] == "199" and a[5] == "" and a[6] == "På lager"
    assert b[0].endswith("?variant=21") and b[2].endswith("1 kg") and b[4] == "249,50" and b[5] == "299" and b[6] == "Utsolgt"
    assert b[1].endswith("b.jpg")  # variantbildet
    assert c[5] == ""  # førpris lik pris regnes ikke som tilbud


def test_money():
    assert f.money("199.00") == "199" and f.money("0.00") == "" and f.money(None) == ""


def test_sider():
    calls = []

    def fake(url):
        calls.append(url)
        return {"products": DATA["products"]}

    assert len(f.all_products(fake)) == 3 and len(calls) == 1


def test_convert(tmp_path):
    out = tmp_path / "f.csv"
    assert f.convert(f.rows_from_products(DATA["products"]), out) == 3
    try:
        f.convert([], tmp_path / "x.csv")
    except SystemExit:
        pass
    else:
        raise AssertionError("skulle stoppet")
