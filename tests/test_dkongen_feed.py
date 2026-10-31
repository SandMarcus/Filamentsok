import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import dkongen_feed as k  # noqa: E402
from tools import nm3d_feed as nf  # noqa: E402

DATA = json.loads((Path(__file__).parent / "fixtures" / "3dkongen_sample.json").read_text(encoding="utf-8"))


def test_filter():
    keep = [p["id"] for p in DATA if k.is_filament(p)]
    assert keep == [1, 2]  # hotend, printer og tørkeboks er ikke filament


def test_rader(tmp_path):
    out = tmp_path / "k.csv"
    assert nf.convert(DATA, out, fetch=None, keep=k.is_filament) == 2
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager"
    assert "Polyterra PLA – 1.75mm – 1Kg – Peach" in lines[1]
    assert ",229,279," in lines[1]  # pris i øre -> kroner, førpris fra regular_price
    assert lines[2].endswith("Utsolgt")
