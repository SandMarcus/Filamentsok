import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import restore_feeds as r  # noqa: E402


def setup(tmp_path, local="Lenke,Navn,Pris\nhttps://a/x,Gammel,100\n"):
    (tmp_path / "config").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "config" / "site.json").write_text(json.dumps({"url": "https://example.no/"}), encoding="utf-8")
    (tmp_path / "config" / "stores.json").write_text(json.dumps({"stores": [{"id": "elefun", "file": "data/elefun.csv"}]}), encoding="utf-8")
    (tmp_path / "data" / "elefun.csv").write_text(local, encoding="utf-8")
    return tmp_path


def test_henter_forrige_publiserte_fil(tmp_path):
    root = setup(tmp_path)
    calls = []

    def fake(url):
        calls.append(url)
        return "Lenke,Navn,Pris\nhttps://a/x,Fra natten,90\nhttps://a/y,Ny,50\n".encode()

    res = r.restore(["elefun"], root, fake)
    assert calls == ["https://example.no/feeds/elefun.csv"] and res["elefun"].startswith("hentet (2 rader)")
    assert "Fra natten" in (root / "data" / "elefun.csv").read_text(encoding="utf-8")


def test_beholder_repoets_fil_ved_feil_tom_eller_annen_overskrift(tmp_path):
    root = setup(tmp_path)
    keep = (root / "data" / "elefun.csv").read_text(encoding="utf-8")

    def boom(url):
        raise OSError("404")

    assert r.restore(["elefun"], root, boom)["elefun"].startswith("beholdt")
    assert r.restore(["elefun"], root, lambda u: b"Lenke,Navn,Pris\n")["elefun"] == "beholdt: tom fil"
    assert r.restore(["elefun"], root, lambda u: b"A,B\n1,2\n")["elefun"] == "beholdt: annen overskrift"
    assert r.restore(["finnes_ikke"], root, boom)["finnes_ikke"] == "beholdt: ukjent butikk"
    assert (root / "data" / "elefun.csv").read_text(encoding="utf-8") == keep


def test_bygget_publiserer_butikkfilene():
    import tempfile
    from src import build
    out = Path(tempfile.mkdtemp()) / "o"
    assert build.main(["--out", str(out)]) == 0
    assert (out / "feeds" / "elefun.csv").exists() and (out / "feeds" / "polyalkemi.csv").exists()
    assert "Disallow: /feeds/" in (out / "robots.txt").read_text(encoding="utf-8")
