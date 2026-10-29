import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import printers_common as pc  # noqa: E402
from tools import materiex_feed as m  # noqa: E402
from src import printers as sp  # noqa: E402


def test_clean_name():
    assert pc.clean_name("Anycubic LAGERSALG: Anycubic Photon S") == "Anycubic Photon S"
    assert pc.clean_name("LAGERSALG: Creality K1") == "Creality K1"


def test_tilbehor_filtreres():
    assert pc.is_accessory("Bambu Lab AMS 2 Pro Hotend")
    assert not pc.is_accessory("Bambu Lab P1S")


def test_write_dropper_pris_null(tmp_path):
    dst = tmp_path / "p.csv"
    rows = [["u1", "", "A", "FDM", "0", "", "Utsolgt"], ["u2", "", "B", "FDM", "1999", "", "På lager"]]
    assert pc.write(rows, dst) == 1
    assert pc.write([], tmp_path / "tom.csv") == 0
    assert not (tmp_path / "tom.csv").exists()


def test_materiex_printere():
    xml = """<?xml version="1.0"?><rss xmlns:g="http://base.google.com/ns/1.0"><channel>
<item><g:id>1</g:id><title>Bambu Lab P1S</title><link>https://materiex.no/p1s</link><g:price>7990.00 NOK</g:price><g:sale_price>6990.00 NOK</g:sale_price><g:availability>in_stock</g:availability><g:product_type>3D Printere</g:product_type></item>
<item><g:id>2</g:id><title>PETG</title><link>https://materiex.no/f</link><g:price>199.00 NOK</g:price><g:product_type>Filament</g:product_type></item>
</channel></rss>""".encode()
    rows = m.printer_rows(xml)
    assert len(rows) == 1 and rows[0][4] == "6990" and rows[0][5] == "7990"
