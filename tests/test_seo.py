import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import seo  # noqa: E402

PAGE = '<html><head><title>Tittel</title><meta name="description" content="Beskrivelse &amp; mer"></head><body></body></html>'
CFG = {"url": "https://example.no", "google_verification": "abc123"}


def test_inject_seo():
    out = seo.inject_seo(PAGE, "/guide/", CFG)
    assert '<link rel="canonical" href="https://example.no/guide/">' in out
    assert 'og:title" content="Tittel"' in out and "Beskrivelse &amp; mer" in out
    assert 'google-site-verification" content="abc123"' in out
    assert out.count("</head>") == 1
    assert seo.inject_seo(out, "/guide/", CFG) == out  # idempotent


def test_uten_adresse_gjores_ingenting():
    assert seo.inject_seo(PAGE, "/", {"url": ""}) == PAGE


def test_forside_har_strukturerte_data():
    out = seo.inject_seo(PAGE, "/", CFG)
    assert "application/ld+json" in out and '"@type":"WebSite"' in out


def test_filer(tmp_path):
    seo.write_files(tmp_path, CFG, "2026-10-29", lambda p: p != "partner/index.html")
    sm = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://example.no/guide/" in sm and "/partner/" not in sm and "2026-10-29" in sm
    assert "Sitemap: https://example.no/sitemap.xml" in (tmp_path / "robots.txt").read_text(encoding="utf-8")
