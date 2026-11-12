"""Henter filament fra 3DFixit (3dfixit.no) via WooCommerce sitt åpne Store API og skriver data/3dfixit.csv.

Bruk:
    python tools/fixit_feed.py [data/3dfixit.csv]
    python tools/fixit_feed.py data/3dfixit.csv --sample side.json   # lagret JSON-side, uten nett

Butikken er bygget på WooCommerce, som NorMax3D, Stratum3D og 3D Kongen, så skriptet bruker samme logikk som
tools/nm3d_feed.py (én rad per variant med pris, førpris, lager og bilde). Det tas med produkter i kategorien
«Filamenter 1,75» (`filamenter1_75`) og underkategoriene, og tilbehør som skulle ligge der sorteres bort på navn.
robots.txt hos butikken sperrer bare /wp-admin/, og Store API-et er åpent. Priser er oppgitt i øre og inkluderer mva.
Utdata har kolonnene Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager. Feiler noe, skrives ikke filen.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dkongen_feed as dk  # noqa: E402
import nm3d_feed as nf  # noqa: E402

BASE = "https://3dfixit.no/wp-json/wc/store/v1"
CATEGORY = "filamenter1_75"


def is_filament(p):
    if not any(c.get("slug") == CATEGORY for c in p.get("categories", [])):
        return False
    return not dk.NOT_FILAMENT.search(nf.clean(p.get("name")))  # tørkebokser, dyser og annet tilbehør


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if "--sample" in argv:
        src = argv[argv.index("--sample") + 1]
        rest = [a for a in args if a != src]
        dst = rest[0] if rest else "data/3dfixit.csv"
        n = nf.convert(json.loads(Path(src).read_text(encoding="utf-8")), dst, fetch=None, keep=is_filament)
    else:
        dst = args[0] if args else "data/3dfixit.csv"
        old = nf.BASE
        nf.BASE = BASE  # samme API-logikk som NorMax3D, men mot 3DFixit
        try:
            n = nf.convert(nf.all_products(nf.fetch_json), dst, fetch=nf.fetch_json, keep=is_filament)
        finally:
            nf.BASE = old
    print(f"Skrev {n} rader til {dst}")


if __name__ == "__main__":
    main(sys.argv[1:])
