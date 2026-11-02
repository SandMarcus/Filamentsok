import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import history as h  # noqa: E402

NOW = 30_000_000


def prod(price, url="https://a/x", store="poly", extra=None):
    offers = [{"s": store, "p": price, "u": url, "a": "yes", "i": "img.jpg"}] + (extra or [])
    return {"id": "p1", "name": "PLA Svart", "brand": "Elegoo", "col": "Svart", "mat": "PLA", "kg": 1.0, "offers": offers}


def test_forste_gang_gir_ingen_endringer():
    hist = h.update(None, [prod(199)], NOW)
    assert hist["since"] == NOW and h.changes(hist, [prod(199)], NOW) == []


def test_prisendring_registreres_og_vises():
    hist = h.update(None, [prod(199)], NOW)
    hist = h.update(hist, [prod(199)], NOW + 60)           # uendret: ingen nytt punkt
    assert len(next(iter(hist["o"].values()))["h"]) == 1
    other = {"s": "nm3d", "p": 210, "u": "https://b/y", "a": "out"}
    hist = h.update(hist, [prod(149, extra=[other])], NOW + 1440)
    ch = h.changes(hist, [prod(149, extra=[other])], NOW + 1500)
    assert len(ch) == 1 and ch[0]["ch"] == [{"s": "poly", "f": 199, "t": 149, "at": NOW + 1440}]
    assert [o["s"] for o in ch[0]["o"]] == ["poly", "nm3d"]  # alle butikker følger med for lenker
    assert h.changes(hist, [prod(149)], NOW + 1440 + 31 * 1440) == []  # eldre enn 30 dager


def test_rydder_gamle_tilbud_og_ugyldige_priser():
    hist = h.update(None, [prod(100), prod(0, url="https://z/z")], NOW)
    assert len(hist["o"]) == 1
    hist = h.update(hist, [], NOW + (h.KEEP_DAYS + 1) * 1440)
    assert hist["o"] == {}


def test_load_previous(monkeypatch=None):
    class R:
        def __init__(s, b): s.b = b
        def read(s): return s.b
        def __enter__(s): return s
        def __exit__(s, *a): return False
    orig = h.urllib.request.urlopen
    try:
        h.urllib.request.urlopen = lambda *a, **k: R(json.dumps({"v": 1, "since": 5, "o": {}}).encode())
        assert h.load_previous("http://x")["since"] == 5

        def nf(*a, **k): raise urllib.error.HTTPError("http://x", 404, "nf", {}, None)
        h.urllib.request.urlopen = nf
        assert h.load_previous("http://x") == h.empty()

        def boom(*a, **k): raise urllib.error.HTTPError("http://x", 500, "err", {}, None)
        h.urllib.request.urlopen = boom
        try:
            h.load_previous("http://x")
        except SystemExit:
            pass
        else:
            raise AssertionError("skulle stoppet")
    finally:
        h.urllib.request.urlopen = orig


def test_bygg_lager_prisendringer_json(tmp_path=None):
    import tempfile
    from src import build
    out = Path(tempfile.mkdtemp()) / "o"
    orig = h.load_previous
    try:
        h.load_previous = lambda url: {"v": 1, "since": 1, "o": {}}
        assert build.main(["--out", str(out), "--keep-history"]) == 0
    finally:
        h.load_previous = orig
    hist = json.loads((out / "history.json").read_text(encoding="utf-8"))
    pj = json.loads((out / "prisendringer.json").read_text(encoding="utf-8"))
    assert hist["o"] and pj["items"] == [] and pj["stores"] and (out / "prisendringer" / "index.html").exists()
    assert "/prisendringer/" in (out / "sitemap.xml").read_text(encoding="utf-8")
    # uten flagget lages ingen historikkfiler
    out2 = out.parent / "o2"
    assert build.main(["--out", str(out2)]) == 0 and not (out2 / "history.json").exists()


def test_varianter_med_samme_lenke_blandes_ikke():
    a = prod(279, url="https://m/p", store="materiex"); a["name"] = "E-PLA Hvit"
    b = prod(349, url="https://m/p", store="materiex"); b["name"] = "E-PLA Glow"
    hist = h.update(None, [a, b], NOW)
    hist = h.update(hist, [a, b], NOW + 1440)
    assert len(hist["o"]) == 2 and h.changes(hist, [a, b], NOW + 1440) == []
