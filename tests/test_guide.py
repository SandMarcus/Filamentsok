import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
G = json.loads((ROOT / "data" / "guide.json").read_text(encoding="utf-8"))


def site_materials():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    return set(re.findall(r"^    '([^']+)':\{n:", html, re.M)) - {"Annet", "Support"}


def test_every_sheet_material_is_a_site_material():
    keys = {m["key"] for m in G["materials"]}
    assert keys <= site_materials()


def test_missing_list_matches_reality():
    keys = {m["key"] for m in G["materials"]}
    assert set(G["missing"]) == site_materials() - keys


def test_cards_are_complete():
    for m in G["materials"]:
        assert m["abbr"] and m["tech"] and m["fam"], m["abbr"]
        assert all(v not in (None, "") for v in m["gen"].values()), m["abbr"]
        assert all(v not in (None, "") for v in m["spec"].values()), m["abbr"]
    ids = [m["id"] for m in G["materials"]]
    assert len(ids) == len(set(ids))


def test_no_english_leftovers_in_levels():
    bad = {"Low", "Medium", "High", "Unknown", "Verify", "Yes", "No", "Good"}
    for m in G["materials"]:
        for v in list(m["gen"].values()) + list(m["spec"].values()):
            assert v not in bad, (m["abbr"], v)


def test_prefix_search_rule():
    """Samme regel som i siden: forkortelse (eller ord i den) eller teknisk navn begynner med teksten."""
    def match(m, q):
        s = m["abbr"].lower()
        toks = [s] + [t for t in re.split(r"[\s/()]+", s) if t]
        return any(t.startswith(q) for t in toks) or m["tech"].lower().startswith(q)
    names = lambda q: [m["abbr"] for m in G["materials"] if match(m, q)]
    assert {"PLA", "PETG"} <= set(names("p"))
    assert set(names("pl")) == {"PLA", "PLA+ / Pro"}
    assert "HIPS" not in names("p")


def test_build_copies_guide(tmp_path):
    from src import build
    out = tmp_path / "dist"
    assert build.main(["--out", str(out)]) == 0
    assert (out / "guide.json").exists()
    page = (out / "guide" / "index.html").read_text(encoding="utf-8")
    assert "__BUILD__" not in page


def test_no_contradictions_between_detail_and_spec():
    """Hver egenskap skal bare ha ett svar. PLA skal for eksempel ikke ha høy slagfasthet ett sted og lav et annet."""
    pla = next(m for m in G["materials"] if m["abbr"] == "PLA")
    assert pla["gen"]["tough"] in ("Lav", "Svært lav")
    assert pla["gen"]["warp"] in ("Lav", "Svært lav")
    keys = set(pla["spec"])
    assert not keys & {"impact", "heatr", "chemr", "fatr", "flexr", "elast", "uvw"}


def test_dimensional_stability_is_opposite_of_warping():
    order = ["Svært lav", "Lav", "Middels", "Høy", "Svært høy"]
    for m in G["materials"]:
        w, d = m["gen"]["warp"], m["spec"]["dim"]
        if w in order and d in order:
            assert order.index(w) + order.index(d) == 4, m["abbr"]


def test_card_front_data():
    for m in G["materials"]:
        assert m["gen"]["uses"] and m["gen"]["diff"]


def test_filter_and_menu_wiring():
    html = (ROOT / "web" / "guide" / "index.html").read_text(encoding="utf-8")
    assert "Utvidet informasjon" in html and "Tekniske spesifikasjoner" not in html
    assert 'id="fbtn"' in html and 'id="sug"' in html and 'type="range"' in html
    for f in ("index.html", "partner.html"):
        assert 'class="hot"' not in (ROOT / "web" / f).read_text(encoding="utf-8")
