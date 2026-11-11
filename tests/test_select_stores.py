import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import select_stores as s  # noqa: E402

ALLE = list(s.STORES)
FILER = s.data_files()


def test_natten_henter_alle_butikkene_ogsa_polyalkemi():
    fetch, restore = s.select("schedule")
    assert fetch == ALLE and "poly" in fetch and restore == ALLE


def test_manuell_start_henter_bare_de_som_er_krysset_av():
    inputs = {"hent_elefun": True, "hent_fjord3d": "true", "hent_normax3d": False, "hent_polyalkemi": False}
    fetch, _ = s.select("workflow_dispatch", inputs)
    assert fetch == ["elefun", "fjord3d"]


def test_manuell_start_uten_valg_henter_ingenting_men_gjenoppretter_alt():
    fetch, restore = s.select("workflow_dispatch", {})
    assert fetch == [] and restore == ALLE


def test_manuell_start_med_polyalkemi_avkrysset():
    fetch, _ = s.select("workflow_dispatch", {"hent_polyalkemi": True})
    assert fetch == ["poly"]


def test_push_henter_bare_butikken_der_verktoyet_er_endret():
    fetch, _ = s.select("push", changed=["tools/fjord3d_feed.py", "web/index.html"], feeds_published=True)
    assert fetch == ["fjord3d"]


def test_push_uten_butikkendring_henter_ingenting():
    fetch, restore = s.select("push", changed=["web/index.html", "CHANGELOG.md", "src/build.py"], feeds_published=True)
    assert fetch == [] and restore == ALLE


def test_endret_felles_verktoy_tar_med_alle_som_bruker_det():
    fetch, _ = s.select("push", changed=["tools/nm3d_feed.py"], feeds_published=True)
    assert fetch == ["nm3d", "stratum", "dkongen", "fixit"]


def test_polyalkemi_hentes_ved_push_bare_nar_verktoyet_er_endret():
    assert "poly" in s.select("push", changed=["tools/polyalkemi_feed.py"], feeds_published=True)[0]
    assert "poly" not in s.select("push", changed=["tools/elefun_feed.py"], feeds_published=True)[0]


def test_push_der_endringene_ikke_kan_leses_henter_alle_unntatt_polyalkemi():
    fetch, _ = s.select("push", changed=None, feeds_published=True)
    assert fetch == [i for i in ALLE if i != "poly"]


def test_forste_bygg_uten_publiserte_butikkfiler_henter_alle_unntatt_polyalkemi():
    fetch, _ = s.select("push", changed=["web/index.html"], feeds_published=False)
    assert fetch == [i for i in ALLE if i != "poly"]


def test_butikkfil_endret_for_hand_blir_ikke_overskrevet_av_publisert_versjon():
    _, restore = s.select("push", changed=["data/elefun.csv"], feeds_published=True, files=FILER)
    assert "elefun" not in restore and "fjord3d" in restore


def test_alle_butikker_finnes_i_stores_json_og_har_verktoy_og_valg():
    for sid, c in s.STORES.items():
        assert sid in FILER, sid
        assert c["input"].startswith("hent_")
        for t in c["tools"]:
            assert (Path(__file__).resolve().parent.parent / t).exists(), t


def test_inputs_json_tolkes_trygt():
    assert s.parse_inputs('{"hent_elefun": true}') == {"hent_elefun": True}
    assert s.parse_inputs("") == {} and s.parse_inputs("null") == {} and s.parse_inputs("ikke json") == {}


def test_feeds_publisert_sjekk():
    assert s.feeds_published("https://x.no", fetch_fn=lambda url: url.endswith("/feeds/elefun.csv")) is True
    assert s.feeds_published("https://x.no", fetch_fn=lambda url: (_ for _ in ()).throw(OSError("404"))) is False


def test_main_skriver_fetch_og_restore(tmp_path, monkeypatch, capsys):
    out = tmp_path / "out.txt"
    ch = tmp_path / "changed.txt"
    ch.write_text("tools/materiex_feed.py\nREADME.md\n", encoding="utf-8")
    monkeypatch.setenv("EVENT_NAME", "push")
    monkeypatch.setenv("INPUTS_JSON", "{}")
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(s, "feeds_published", lambda site, **kw: True)
    s.main(["--changed", str(ch)])
    lines = dict(l.split("=", 1) for l in out.read_text(encoding="utf-8").splitlines())
    assert lines["fetch"] == "materiex" and lines["restore"].split() == ALLE
    assert "Hentes på nytt: materiex" in capsys.readouterr().out
