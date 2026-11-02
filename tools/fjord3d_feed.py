"""Henter filament fra Fjord3D (fjord3d.no) og skriver data/fjord3d.csv.

Bruk:
    python tools/fjord3d_feed.py [data/fjord3d.csv]                        # henter https://fjord3d.no/api/products.php
    python tools/fjord3d_feed.py data/fjord3d.csv --sample products.json   # leser en lagret JSON-fil (uten nett)

Butikken har et åpent produkt-API med pris, lagerantall (`stock_qty`), vekt og farge per variant. Bare varer med
`product_type` = filament tas med (ikke silikaposer, vakuumposer osv.). Samme farge kan finnes både med pappspole og
gjenbrukbar spole; da beholdes én rad per farge og vekt (helst den som er på lager). Lenken er variantsiden
`/filament-<materiale>-<farge>` (samme regel som butikkens egne adresser). Prisen inkluderer mva.
Utdata har kolonnene Lenke,Bilde,Navn,Farge,Pris,Lager. Feiler noe, skrives ikke filen. Ren Python, ingen avhengigheter.
"""
import csv
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://fjord3d.no"
API = BASE + "/api/products.php"
UA = "Filamentsok/1.0 (prissammenligning; +https://xn--filamentsk-8cb.no)"
COLUMNS = ["Lenke", "Bilde", "Navn", "Farge", "Pris", "Lager"]
TRANSLIT = str.maketrans({"æ": "ae", "ø": "o", "å": "a", "é": "e", "ä": "a", "ö": "o"})


def fetch_json(url, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (i + 1))
    raise SystemExit(f"Klarte ikke hente {url}: {last}")


def slug(material, color):
    """«PLA», «Mørkblå» -> «filament-pla-morkbla» (som butikkens adresser)."""
    s = f"{material} {color}".lower().translate(TRANSLIT)
    return "filament-" + re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def abs_url(path):
    if not path:
        return ""
    return path if path.startswith("http") else BASE + "/" + path.lstrip("/")


def money(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return ""
    if x <= 0:
        return ""
    return ("%d" % x) if x == int(x) else ("%.2f" % x).replace(".", ",")


def rows_from_products(products):
    best = {}
    for p in products:
        if p.get("product_type") != "filament" or p.get("active") in (0, False, "0"):
            continue
        material, color, grams = (p.get("material") or "").strip(), (p.get("color") or "").strip(), p.get("weight_grams") or 0
        price = money(p.get("price"))
        if not (material and color and grams and price):
            continue
        stock = int(p.get("stock_qty") or 0)
        key = (material, color, grams)
        # én rad per farge og vekt: helst på lager, deretter pappspole (butikkens standard)
        rank = (stock > 0, p.get("spool_type") == "cardboard", bool(p.get("image_url")))
        if key not in best or rank > best[key][0]:
            kg = grams / 1000
            kgs = ("%g" % kg).replace(".", ",")
            name = f"Fjord3D {material} filament 1,75 mm {kgs} kg {color}"
            lager = str(stock) if stock > 0 else "Utsolgt"
            best[key] = (rank, [BASE + "/" + slug(material, color), abs_url(p.get("image_url")), name, color, price, lager])
    return [v[1] for v in best.values()]


def convert(rows, dst):
    if not rows:
        raise SystemExit("Fant ingen varer. Filen ble ikke skrevet.")
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)
    return len(rows)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if "--sample" in argv:
        src = argv[argv.index("--sample") + 1]
        rest = [a for a in args if a != src]
        dst = rest[0] if rest else "data/fjord3d.csv"
        data = json.loads(Path(src).read_text(encoding="utf-8"))
    else:
        dst = args[0] if args else "data/fjord3d.csv"
        data = fetch_json(API)
    if not data.get("ok", True):
        raise SystemExit("API-et svarte ikke ok. Filen ble ikke skrevet.")
    print(f"Skrev {convert(rows_from_products(data.get('products', [])), dst)} rader til {dst}")


if __name__ == "__main__":
    main(sys.argv[1:])
