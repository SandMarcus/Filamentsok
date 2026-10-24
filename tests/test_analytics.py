import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.build import inject_analytics  # noqa: E402

PAGES = ("index.html", "guide/index.html", "partner/index.html", "funksjoner/index.html")


def test_pages_have_placeholders():
    for p in PAGES:
        h = (ROOT / "web" / p).read_text(encoding="utf-8")
        assert "<!--__ANALYTICS__-->" in h and "<!--__ANALYTICS_NOTE__-->" in h, p


def test_inject_off_removes_placeholders():
    out = inject_analytics("a<!--__ANALYTICS__-->b<!--__ANALYTICS_NOTE__-->", "")
    assert out == "ab"


def test_inject_on_adds_goatcounter_without_cookies():
    out = inject_analytics("<!--__ANALYTICS__--><!--__ANALYTICS_NOTE__-->", "filamentsok")
    assert 'data-goatcounter="https://filamentsok.goatcounter.com/count"' in out
    assert "uten cookies" in out



def test_no_google_or_consent_code():
    assert not (ROOT / "web" / "samtykke.js").exists()
    for p in PAGES:
        h = (ROOT / "web" / p).read_text(encoding="utf-8")
        assert "googletagmanager" not in h and "google-analytics" not in h and "samtykke" not in h, p
