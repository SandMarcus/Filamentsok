"""Henter filament fra Stratum3D (stratum3d.no) via WooCommerce sitt åpne Store API og skriver data/stratum3d.csv.

Bruk:
    python tools/stratum_feed.py [data/stratum3d.csv]
    python tools/stratum_feed.py data/stratum3d.csv --sample side.json   # lagret JSON-side, uten nett

Butikken er bygget på WooCommerce, som NorMax3D, så skriptet bruker samme logikk som tools/nm3d_feed.py
(én rad per variant med pris, førpris, lager og bilde). Her tas kategorien «3d-print-filament» med.
Utdata har kolonnene Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager. Feiler noe, skrives ikke filen.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nm3d_feed as nf  # noqa: E402

BASE = "https://stratum3d.no/wp-json/wc/store/v1"


def is_filament(p):
    slugs = [c["slug"] for c in p.get("categories", [])]
    # Pass på: «3d-printer-filament» er en annen kategori (der ligger også printere), og skal ikke med.
    return any(s == "3d-print-filament" or s.startswith("3d-print-filament-") for s in slugs)


PRINTER_SKIP = {"3d-printer-materialer", "3d-print-filament", "tilbehor", "reservedeler", "3d-print-resin"}


def is_printer(p):
    """Printere ligger i kategorier som starter på «3d-printer» (for eksempel «3d-printer-filament», som er feilnavngitt
    og har CreatBot-printere), men ikke i materialkategoriene. Tilbehør sorteres bort på navn."""
    slugs = [c["slug"] for c in p.get("categories", [])]
    if any(s in PRINTER_SKIP or s.startswith("3d-print-filament") for s in slugs):
        return False
    return any(s.startswith("3d-printer") for s in slugs)


def printer_rows(products):
    out = []
    for p in products:
        if p.get("parent") or not is_printer(p):
            continue
        name = nf.pc.clean_name(p["name"])
        price = nf.money(p.get("prices"), "price")
        if not price or nf.pc.is_accessory(name):
            continue
        was = nf.money(p["prices"], "regular_price") if p.get("on_sale") else ""
        img = (p.get("images") or [{}])[0].get("src", "")
        out.append([p["permalink"], img, name, "", price, was, nf.stock_text(p)])
    return out


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if "--sample" in argv:
        src = argv[argv.index("--sample") + 1]
        rest = [a for a in args if a != src]
        dst = rest[0] if rest else "data/stratum3d.csv"
        n = nf.convert(json.loads(Path(src).read_text(encoding="utf-8")), dst, fetch=None, keep=is_filament, printer_fn=printer_rows)
    else:
        dst = args[0] if args else "data/stratum3d.csv"
        old = nf.BASE
        nf.BASE = BASE  # samme API-logikk som NorMax3D, men mot Stratum3D
        try:
            n = nf.convert(nf.all_products(nf.fetch_json), dst, fetch=nf.fetch_json, keep=is_filament, printer_fn=printer_rows)
        finally:
            nf.BASE = old
    print(f"Skrev {n} rader til {dst}")


if __name__ == "__main__":
    main(sys.argv[1:])
