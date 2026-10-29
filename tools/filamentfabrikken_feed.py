"""Henter filament fra Filamentfabrikken (filamentfabrikken.no, Shopify) og skriver data/filamentfabrikken.csv.

Bruk:
    python tools/filamentfabrikken_feed.py [data/filamentfabrikken.csv]                    # henter /collections/filament/products.json
    python tools/filamentfabrikken_feed.py data/filamentfabrikken.csv --sample products.json  # leser en lagret JSON-fil (uten nett)

Shopify publiserer varelisten som JSON (maks 250 per side, `page=N`). Hver variant (farge/størrelse) blir én rad.
Shopify oppgir bare om varen kan kjøpes (`available`), ikke antall, så lager blir «På lager» eller «Utsolgt».
Utdata har kolonnene Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager. Prisene inkluderer mva.
Feiler noe, skrives ikke filen, så den gamle blir liggende. Ren Python, ingen avhengigheter.
"""
import csv
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://filamentfabrikken.no"
URL = BASE + "/collections/filament/products.json?limit=250&page={page}"
UA = "Filamentsok/1.0 (prissammenligning; +https://xn--filamentsk-s5a.no)"
COLUMNS = ["Lenke", "Bilde", "Navn", "Farge", "Pris", "Førpris", "Lager"]
NOT_FILAMENT = re.compile(r"tørk|dryer|dry box|hotend|dyse|nozzle|byggeplate|sensor|verktøy|gavekort|gift card", re.I)


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


def all_products(fetch=fetch_json, max_pages=10):
    out = []
    for page in range(1, max_pages + 1):
        got = fetch(URL.format(page=page)).get("products", [])
        out += got
        if len(got) < 250:
            break
    return out


def money(v):
    """«199.00» -> «199», «249.50» -> «249,50». Tomt hvis ikke et tall."""
    try:
        x = float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return ""
    if x <= 0:
        return ""
    return ("%d" % x) if x == int(x) else ("%.2f" % x).replace(".", ",")


def rows_from_products(products):
    rows = []
    for p in products:
        title = html.unescape((p.get("title") or "").strip())
        if not title or NOT_FILAMENT.search(title):
            continue
        variants = p.get("variants") or []
        imgs = {im.get("id"): im.get("src") for im in p.get("images") or []}
        first_img = (p.get("images") or [{}])[0].get("src", "") if p.get("images") else ""
        for v in variants:
            price = money(v.get("price"))
            if not price:
                continue
            vt = (v.get("title") or "").strip()
            name = title if vt in ("", "Default Title") else f"{title} {vt}"
            was = money(v.get("compare_at_price"))
            if was and float(was.replace(",", ".")) <= float(price.replace(",", ".")):
                was = ""
            img = imgs.get(v.get("image_id")) or (v.get("featured_image") or {}).get("src") or first_img
            link = f"{BASE}/products/{p['handle']}" + (f"?variant={v['id']}" if len(variants) > 1 else "")
            rows.append([link, img or "", name, "", price, was, "På lager" if v.get("available") else "Utsolgt"])
    return rows


def convert(rows, dst):
    seen, uniq = set(), []
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            uniq.append(r)
    if not uniq:
        raise SystemExit("Fant ingen varer. Filen ble ikke skrevet.")
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(uniq)
    return len(uniq)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if "--sample" in argv:
        src = argv[argv.index("--sample") + 1]
        rest = [a for a in args if a != src]
        dst = rest[0] if rest else "data/filamentfabrikken.csv"
        products = json.loads(Path(src).read_text(encoding="utf-8")).get("products", [])
    else:
        dst = args[0] if args else "data/filamentfabrikken.csv"
        products = all_products()
    print(f"Skrev {convert(rows_from_products(products), dst)} rader til {dst}")


if __name__ == "__main__":
    main(sys.argv[1:])
