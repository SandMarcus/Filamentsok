"""Henter filament fra Materie X (materiex.no) via Google Shopping-feeden og skriver data/materiex.csv.

Bruk:
    python tools/materiex_feed.py [data/materiex.csv]                    # henter https://materiex.no/gshopping.xml
    python tools/materiex_feed.py data/materiex.csv --sample feed.xml    # leser en lagret feed (uten nett)

Feeden er RSS med g:-felt. Hver <item> er en variant (farge) med egen pris, lager og bilde.
Utdata har kolonnene Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager, slik malen i config/stores.json forventer.
Prisene i feeden inkluderer mva. Feiler noe, skrives ikke filen, så den gamle blir liggende.
Ren Python, ingen avhengigheter.
"""
import csv
import html
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

FEED = "https://materiex.no/gshopping.xml"
UA = "Filamentsok/1.0 (prissammenligning; +https://xn--filamentsk-s5a.no)"
G = "{http://base.google.com/ns/1.0}"
NOT_FILAMENT = re.compile(r"resin|harpiks|tørk|dryer|dry box|hotend|dyse|nozzle|plate|byggeplate|printer\b|sensor|verktøy|lim\b", re.I)


def fetch(url, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (i + 1))
    raise SystemExit(f"Klarte ikke hente {url}: {last}")


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def money(text):
    """«299.00 NOK» -> «299» eller «299,90». Tomt hvis ikke et tall."""
    m = re.search(r"\d+(?:[.,]\d+)?", text or "")
    if not m:
        return ""
    v = float(m.group(0).replace(",", "."))
    return ("%d" % v) if v == int(v) else ("%.2f" % v).replace(".", ",")


def val(item, tag):
    el = item.find(G + tag)
    if el is None:
        el = item.find(tag)
    return clean(el.text) if el is not None and el.text else ""


def is_filament(item):
    ptype = val(item, "product_type").lower()
    title = val(item, "title")
    # Produkttypene er «Filament» og «Refill» (spoleløse refiller). Resin, printere og tilbehør tas ikke med.
    if ptype in ("filament", "refill"):
        return not NOT_FILAMENT.search(title)
    return False


def stock_text(avail):
    a = (avail or "").lower().replace(" ", "_")
    if a in ("in_stock", "instock"):
        return "På lager"
    if a in ("backorder", "preorder", "pre_order"):
        return "Utsolgt, men kan bestilles"
    return "Utsolgt"


def rows_from_feed(xml_bytes):
    root = ET.fromstring(xml_bytes)
    rows = []
    for item in root.iter("item"):
        if not is_filament(item):
            continue
        price, sale = money(val(item, "price")), money(val(item, "sale_price"))
        was = ""
        if sale and price and float(sale.replace(",", ".")) < float(price.replace(",", ".")):
            price, was = sale, price
        if not price:
            continue
        link, name, color = val(item, "link"), val(item, "title"), val(item, "color")
        rows.append([link, val(item, "image_link"), name, color, price, was, stock_text(val(item, "availability"))])
    return rows


def convert(xml_bytes, dst):
    rows = rows_from_feed(xml_bytes)
    if not rows:
        raise SystemExit("Fant ingen filamentrader i feeden. Filen ble ikke skrevet.")
    seen, uniq = set(), []
    for r in rows:
        key = (r[0], r[2], r[3])
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Lenke", "Bilde", "Navn", "Farge", "Pris", "Førpris", "Lager"])
        w.writerows(uniq)
    return len(uniq)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if "--sample" in argv:
        src = argv[argv.index("--sample") + 1]
        rest = [a for a in args if a != src]
        dst = rest[0] if rest else "data/materiex.csv"
        data = Path(src).read_bytes()
    else:
        dst = args[0] if args else "data/materiex.csv"
        data = fetch(FEED)
    print(f"Skrev {convert(data, dst)} rader til {dst}")


if __name__ == "__main__":
    main(sys.argv[1:])
