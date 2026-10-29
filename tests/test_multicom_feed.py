import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import multicom_feed as m  # noqa: E402

PAGE = (Path(__file__).parent / "fixtures" / "multicom_sample.html").read_text(encoding="utf-8")


def test_parse_list():
    rows = m.parse_list(PAGE)
    assert len(rows) == 4
    r = rows[0]
    assert r[0].startswith("https://www.multicom.no/") and "/cat-p/" in r[0]
    assert r[2].startswith("Prima Filaments") and "750 g" in r[2]  # merke + navn + vekt
    assert r[4] == "319" and r[5] == ""


def test_lager():
    lager = [r[6] for r in m.parse_list(PAGE)]
    assert lager[0] in ("1", "5+") or lager[0].rstrip("+").isdigit()
    assert "Utsolgt" in lager
    assert "Utsolgt, men kan bestilles" in lager  # leverandørlager


def test_money_og_total():
    assert m.money("299,-") == "299" and m.money("1 290,-") == "1290" and m.money("299,90") == "299,90"
    assert m.total("<p>Viser 1-25 av 48 produkter</p>") == (25, 48)


def test_convert_skriver_csv_og_nekter_tom(tmp_path):
    out = tmp_path / "m.csv"
    assert m.convert(m.parse_list(PAGE), out) == 4
    assert out.read_text(encoding="utf-8").splitlines()[0] == "Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager"
    try:
        m.convert([], tmp_path / "x.csv")
    except SystemExit:
        assert not (tmp_path / "x.csv").exists()
    else:
        raise AssertionError("skulle stoppet")


def test_hopper_over_handlebars_mal():
    assert m.parse_list('<div class="b-product-list__item"><a data-product-link="{{id}}" href="{{url}}">x</a>') == []
