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
