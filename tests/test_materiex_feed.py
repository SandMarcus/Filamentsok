import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import materiex_feed as m  # noqa: E402

XML = """<?xml version="1.0"?><rss version="2.0" xmlns:g="http://base.google.com/ns/1.0"><channel>
<item><g:id>1</g:id><title>Bambu Lab PETG Matte</title><link>https://materiex.no/produkt/a</link><g:image_link>https://x/a.jpg</g:image_link>
<g:price>239.00 NOK</g:price><g:availability>in_stock</g:availability><g:product_type>Filament</g:product_type><g:color>Lime</g:color></item>
<item><g:id>2</g:id><title>Bambu Lab PETG Matte</title><link>https://materiex.no/produkt/a</link><g:image_link>https://x/b.jpg</g:image_link>
<g:price>239.00 NOK</g:price><g:sale_price>199.90 NOK</g:sale_price><g:availability>out_of_stock</g:availability><g:product_type>Filament</g:product_type><g:color>Pink</g:color></item>
<item><g:id>3</g:id><title>Bambu Lab Hotend</title><link>https://materiex.no/produkt/h</link><g:price>299.00 NOK</g:price><g:product_type>Utstyr &amp; Tilbehør</g:product_type></item>
</channel></rss>""".encode()


def test_feed_rader(tmp_path):
    rows = m.rows_from_feed(XML)
    assert len(rows) == 2
    assert rows[0][3:] == ["Lime", "239", "", "På lager"]
    assert rows[1][3:] == ["Pink", "199,90", "239", "Utsolgt"]


def test_convert_skriver_csv(tmp_path):
    out = tmp_path / "m.csv"
    assert m.convert(XML, out) == 2
    assert out.read_text(encoding="utf-8").splitlines()[0] == "Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager"
