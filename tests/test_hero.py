from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_hero_image_is_wired():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert (ROOT / "web" / "hero.webp").stat().st_size > 10_000
    assert 'src="hero.webp"' in html and 'alt="' in html
    assert "hbub" not in html
