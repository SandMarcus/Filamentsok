import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import tonerweb_feed as t  # noqa: E402

PAGE = (Path(__file__).parent / "fixtures" / "tonerweb_sample.html").read_text(encoding="utf-8")


def test_parse_list():
    rows = t.parse_list(PAGE)
    assert len(rows) == 4
    r = rows[0]
    assert r[0] == "https://www.tonerweb.no/pv.php?pid=320736"
    assert r[1].startswith("https://www.tonerweb.no/images/")
    assert "FLASHFORGE" in r[2] and r[4] == "199" and r[5] == "247"  # pris inkl. mva og førpris


def test_lager_og_navn():
    rows = t.parse_list(PAGE)
    assert rows[0][6] == "1"
    assert rows[1][6] == "Utsolgt"
    assert rows[2][6] == "2" and rows[2][2].endswith("Blå")  # fjernlager teller, «Bl» blir «Blå»
    assert rows[3][1] == ""  # «no_image» tas ikke med
    assert rows[3][2].startswith("Verbatim")


def test_money_og_info():
    assert t.money("315,-") == "315" and t.money("1 290,-") == "1290"
    assert t.page_info(PAGE) == (4, 20)


def test_convert(tmp_path):
    out = tmp_path / "t.csv"
    assert t.convert(t.parse_list(PAGE), out) == 4
    assert out.read_text(encoding="utf-8").splitlines()[0] == "Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager"
    try:
        t.convert([], tmp_path / "x.csv")
    except SystemExit:
        pass
    else:
        raise AssertionError("skulle stoppet")
