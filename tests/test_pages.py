from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
PAGES = ["index.html", "guide/index.html", "funksjoner/index.html", "partner/index.html", "3d-print/index.html"]


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
