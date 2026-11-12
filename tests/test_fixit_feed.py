import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import fixit_feed as f  # noqa: E402
from tools import nm3d_feed as nf  # noqa: E402

DATA = json.loads((Path(__file__).parent / "fixtures" / "3dfixit_sample.json").read_text(encoding="utf-8"))


def test_filter_tar_kategorien_men_ikke_tilbehor_eller_andre_kategorier():
    assert [p["id"] for p in DATA if f.is_filament(p)] == [1582, 1581, 100]  # tørkeboks og dyse er ikke filament


def test_rader_med_pris_forpris_lager_og_rensede_navn(tmp_path):
    out = tmp_path / "f.csv"
    assert nf.convert(DATA, out, fetch=None, keep=f.is_filament) == 3
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager"
    assert "PETG HS MATE – Nyhet !!! 1.75mm 1kg – Sea Soul Blue" in lines[1]  # &#8211; er gjort om til tankestrek
    assert ",209,229,23 på lager" in lines[1]  # pris i øre -> kroner, førpris fra regular_price
    assert lines[3].endswith(",269,,Utsolgt")  # ikke på tilbud: ingen førpris


def test_ingen_filamenter_gir_feil_uten_a_skrive_filen(tmp_path):
    import pytest
    with pytest.raises(SystemExit):
        nf.convert([p for p in DATA if p["id"] == 102], tmp_path / "x.csv", fetch=None, keep=f.is_filament)
    assert not (tmp_path / "x.csv").exists()
