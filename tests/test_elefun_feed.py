import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import elefun_feed  # noqa: E402

HEAD = "id,title,link,availability,price,condition,google_product_category,image_link,gtin,mpn,shipping,product_type\n"


def test_keeps_only_175_filament_and_maps_columns(tmp_path):
    src = tmp_path / "feed.csv"
    src.write_text("\ufeff" + HEAD +
        '1,Propell,https://x/1,in_stock,35 NOK,new,1,https://x/1.jpg,,,,Fly > Propeller\n'
        '2,eSUN PLA+ 1kg - Black,https://x/2,in_stock,299 NOK,new,1,https://x/2.jpg,,,,3dprint > Filament > Filament 1.75mm > PLA+\n'
        '3,eSUN PETG 1kg - Blue,https://x/3,out_of_stock,"349,50 NOK",new,1,https://x/3.jpg,,,,3dprint > Filament > Filament 1.75mm > PLA+\n'
        '4,Ultimaker PLA 2.85mm,https://x/4,in_stock,500 NOK,new,1,https://x/4.jpg,,,,3dprint > Filament > Filament 2.85mm > PLA\n',
        encoding="utf-8")
    out = tmp_path / "elefun.csv"
    assert elefun_feed.convert(src, out) == 2
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert [r["Lenke"] for r in rows] == ["https://x/2", "https://x/3"]
    assert rows[0]["Pris"] == "kr 299,-" and rows[0]["Lager"] == "På lager"
    assert rows[1]["Pris"] == "kr 349,50,-" or rows[1]["Pris"].startswith("kr 349")
    assert rows[1]["Lager"] == "Utsolgt"


def test_empty_result_does_not_overwrite(tmp_path):
    src = tmp_path / "feed.csv"
    src.write_text(HEAD + "1,Propell,https://x/1,in_stock,35 NOK,new,1,i,,,,Fly\n", encoding="utf-8")
    out = tmp_path / "elefun.csv"
    out.write_text("gammel", encoding="utf-8")
    try:
        elefun_feed.convert(src, out)
        assert False
    except SystemExit:
        pass
    assert out.read_text(encoding="utf-8") == "gammel"
