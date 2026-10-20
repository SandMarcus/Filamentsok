"""Hjelper når du fyller ut malen: viser kolonnene i hver CSV-fil og foreslår hva de er.

    python tools/suggest_mapping.py data/*.csv
"""
import csv
import sys

GUESS = {
    "url": ("lenke", "url", "link", "href"), "name": ("navn", "name", "tittel", "title", "produkt"),
    "price": ("pris", "price"), "stock": ("lager", "stock", "beholdning"), "image": ("bilde", "image", "img"),
    "brand": ("produsent", "merke", "brand", "manufacturer"), "color": ("farge", "color", "colour", "featurevalue"),
}

for path in sys.argv[1:]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        first = next(reader, {})
        print(f"\n{path}")
        for col in reader.fieldnames or []:
            low = col.lower()
            kind = next((k for k, words in GUESS.items() if any(w in low for w in words)), "?")
            print(f"  {col:<22} -> {kind:<7} eksempel: {(first.get(col) or '')[:60]!r}")
