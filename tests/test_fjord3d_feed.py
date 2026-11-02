import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import fjord3d_feed as f  # noqa: E402

DATA = json.loads((Path(__file__).parent / "fixtures" / "fjord3d_products.json").read_text(encoding="utf-8"))


def test_bare_filament_en_rad_per_farge():
    rows = f.rows_from_products(DATA["products"])
    assert len(rows) == 7  # tilbehør er ikke med; hvit finnes med to spoletyper, men gir én rad
    by = {r[3]: r for r in rows}
    assert by["Svart"][0] == "https://fjord3d.no/filament-pla-svart"
    assert by["Mørkblå"][0].endswith("/filament-pla-morkbla") and by["Leppestiftrød"][0].endswith("/filament-pla-leppestiftrod")
    assert by["Blandet"][0].endswith("/filament-pla-fargeskift-blandet") and by["Blandet"][4] == "89"
    assert by["Svart"][2] == "Fjord3D PLA filament 1,75 mm 1 kg Svart" and by["Svart"][5] == "Utsolgt"
    assert by["Svart"][1] == "https://fjord3d.no/images/products/pla-svart.jpg"
    assert by["Hvit"][1].startswith("https://fjord3d.no/api/uploads/")


def test_lager_og_valg_av_spole():
    base = {"product_type": "filament", "material": "PLA", "color": "Hvit", "weight_grams": 1000, "price": 169, "image_url": None}
    rows = f.rows_from_products([
        dict(base, spool_type="cardboard", stock_qty=0),
        dict(base, spool_type="reusable", stock_qty=7, image_url="a.jpg"),
    ])
    assert len(rows) == 1 and rows[0][5] == "7" and rows[0][1].endswith("/a.jpg")


def test_slug_og_penger():
    assert f.slug("PLA FARGESKIFT", "Blandet") == "filament-pla-fargeskift-blandet"
    assert f.money("89") == "89" and f.money(0) == "" and f.money(None) == "" and f.money(79.5) == "79,50"
