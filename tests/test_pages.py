from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
PAGES = ["index.html", "guide/index.html", "funksjoner/index.html", "partner/index.html", "3d-print/index.html", "prisendringer/index.html"]


def test_alle_sider_har_sprakknapp_og_skript():
    for p in PAGES:
        html = (WEB / p).read_text(encoding="utf-8")
        assert 'id="lang"' in html, p
        assert "i18n.js" in html, p
        if p != "3d-print/index.html":  # siden lenker til seg selv med «./»
            assert "3d-print/" in html, p


def test_3d_print_siden_har_signal_og_vilkar():
    html = (WEB / "3d-print" / "index.html").read_text(encoding="utf-8")
    assert "signal.me/#eu/" in html and "marcus.5017" in html
    assert "100 % forskuddsbetaling" in html and "Angrerett" in html
    assert (WEB / "signal-qr.jpg").exists()


def test_ordlisten_er_lastbar_og_vedlikeholdssiden_er_borte():
    js = (WEB / "i18n-en.js").read_text(encoding="utf-8")
    assert "window.I18N_EN" in js and "'Hjem': 'Home'" in js
    assert not (WEB / "404.html").exists()


def test_forsiden_viser_antall_tilbud_under_tellingen():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'id="offSub"' in html and "tilbud fra " in html
    assert 'id="quick"' not in html and 'id="stats"' not in html


def test_alle_sider_har_plass_til_versjonsnummer_og_bygget_fyller_det():
    import json
    import tempfile
    from src import build
    root = Path(__file__).resolve().parent.parent
    v = json.loads((root / "config" / "version.json").read_text(encoding="utf-8"))
    assert v["version"] and v["date"]
    for p in PAGES:
        assert "<!--__VERSION__-->" in (WEB / p).read_text(encoding="utf-8"), p
    out = Path(tempfile.mkdtemp()) / "o"
    assert build.main(["--out", str(out)]) == 0
    for p in PAGES:
        html = (out / p).read_text(encoding="utf-8")
        assert f'Versjon {v["version"]} (' in html and "__VERSION__" not in html, p


def test_prisendringer_har_sortering_og_filtre():
    html = (WEB / "prisendringer" / "index.html").read_text(encoding="utf-8")
    for i in ("fSort", "fDir", "fStore", "fMat", "fMin", "fStock", "fReset"):
        assert f'id="{i}"' in html, i
    assert "farge" not in html.lower().split("<main>")[1].split("</main>")[0]  # ingen fargefilter, som på forsiden


def test_sok_forstar_norsk_engelsk_og_nyanser():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert "var NY={Rosegull:" in html and "var ALIAS=" in html
    assert "checks('Nyanse','ny'" in html and 'id="qp"' not in html  # nyanser ligger i filteret, ikke under søkefeltet
    assert "ph.replace(/-/g,' ')" in html  # «rose-gull» tolkes som «rose gull»
    js = (WEB / "i18n-en.js").read_text(encoding="utf-8")
    for k in ("Nyanse", "Rosegull", "Kobber", "Bronse", "Regnbue", "Neon",
              "Pastell", "Mint", "Lavendel", "Himmelblå", "Marine", "Perle"):
        assert f"'{k}': '" in js, f"mangler engelsk ordliste for {k}"
    fn = (WEB / "funksjoner" / "index.html").read_text(encoding="utf-8")
    assert "Norsk og engelsk i søket, og nyanser" in fn
    assert "'Norsk og engelsk i søket, og nyanser': " in js


def test_workflow_lar_deg_velge_butikker_ved_manuell_start():
    import re
    wf = (Path(__file__).resolve().parent.parent / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    steps = re.findall(r"- name: (Hent [^\n]+)\n(.*?)(?=\n      - |\Z)", wf, re.S)
    assert len(steps) >= 10
    for name, body in steps:
        m = re.search(r"inputs\.(hent_\w+)", body)
        assert m, f"{name}: mangler valg for manuell start"
        assert re.search(rf"^      {m.group(1)}:", wf, re.M), f"{name}: inputen {m.group(1)} finnes ikke"
