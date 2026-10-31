"""Henter filament fra 3D Kongen (3dkongen.no) via WooCommerce sitt åpne Store API og skriver data/3dkongen.csv.

Bruk:
    python tools/dkongen_feed.py [data/3dkongen.csv]
    python tools/dkongen_feed.py data/3dkongen.csv --sample side.json   # lagret JSON-side, uten nett

Butikken er bygget på WooCommerce, som NorMax3D og Stratum3D, så skriptet bruker samme logikk som tools/nm3d_feed.py
(én rad per variant med pris, førpris, lager og bilde). Kategoriene hos 3D Kongen er ikke ryddige (for eksempel
ligger filament i «Tømmesalg»), så filament gjenkjennes på navn og kategori, og tilbehør sorteres bort.
Utdata har kolonnene Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager. Feiler noe, skrives ikke filen.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nm3d_feed as nf  # noqa: E402

BASE = "https://www.3dkongen.no/wp-json/wc/store/v1"
MATERIAL = re.compile(r"\b(pla|pla\+|petg|pet-g|abs|asa|tpu|tpe|pa-?cf|pa12|pa6|nylon|pc|pctg|pva|hips|peek|pp)\b|filament|polyterra|polylite|polymax", re.I)
NOT_FILAMENT = re.compile(
    r"dry(er|box)|tørk|hotend|nozzle|dyse|byggeplate|build\s*plate|printer\b|skriver|resin|harpiks|sensor|spoleholder|"
    r"verktøy|tool|kit\b|gavekort|gift|lim\b|glue|vask|wash|cure|ams\b|mmu|extruder|belt|reim|fan\b|vifte|kabel|lcd", re.I)


def is_filament(p):
    name = nf.clean(p.get("name"))
    cats = " ".join(nf.clean(c.get("name")) + " " + c.get("slug", "") for c in p.get("categories", []))
    if NOT_FILAMENT.search(name) and not re.search(r"\bfilament\b", name, re.I):
        return False
    if re.search(r"resin|harpiks|printer", cats, re.I) and not re.search(r"filament", cats, re.I):
        return False
    return bool(MATERIAL.search(name) or re.search(r"filament", cats, re.I))


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if "--sample" in argv:
        src = argv[argv.index("--sample") + 1]
        rest = [a for a in args if a != src]
        dst = rest[0] if rest else "data/3dkongen.csv"
        n = nf.convert(json.loads(Path(src).read_text(encoding="utf-8")), dst, fetch=None, keep=is_filament)
    else:
        dst = args[0] if args else "data/3dkongen.csv"
        old = nf.BASE
        nf.BASE = BASE  # samme API-logikk som NorMax3D, men mot 3D Kongen
        try:
            n = nf.convert(nf.all_products(nf.fetch_json), dst, fetch=nf.fetch_json, keep=is_filament)
        finally:
            nf.BASE = old
    print(f"Skrev {n} rader til {dst}")


if __name__ == "__main__":
    main(sys.argv[1:])
