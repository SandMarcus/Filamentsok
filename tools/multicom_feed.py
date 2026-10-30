"""Henter filament fra Multicom (multicom.no) og skriver data/multicom.csv.

Bruk:
    python tools/multicom_feed.py [data/multicom.csv]                  # henter kategorisiden (opptil 100 varer per side)
    python tools/multicom_feed.py data/multicom.csv --sample side.html # leser en lagret side (uten nett)

Multicom har ingen åpen feed, så vi leser varelisten på kategorisiden «Filament». Siden tar opptil 100 varer
(`ps_100`); skulle butikken få flere, følger vi sidene (`pi_2`, `pi_3` ...) til alle er hentet.
Utdata har kolonnene Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager. Prisene inkluderer mva.
Feiler noe, skrives ikke filen, så den gamle blir liggende. Ren Python, ingen avhengigheter.
"""
import csv
import html
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://www.multicom.no"
CATEGORY = BASE + "/filament/cat-c/c1000798"
UA = "Filamentsok/1.0 (prissammenligning; +https://xn--filamentsk-8cb.no)"
COLUMNS = ["Lenke", "Bilde", "Navn", "Farge", "Pris", "Førpris", "Lager"]
NOT_FILAMENT = re.compile(r"tørk|dryer|dry box|hotend|dyse|nozzle|byggeplate|printer\b|sensor|verktøy|spoleholder", re.I)


def fetch(url, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "nb-NO,nb;q=0.9"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (i + 1))
    raise SystemExit(f"Klarte ikke hente {url}: {last}")


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def money(text):
    """«299,-» -> «299», «1 290,-» -> «1290», «299,90» -> «299,90». Tomt hvis ikke et tall."""
    s = re.sub(r"[\s ]", "", clean(text))
    m = re.match(r"(\d+)(?:,(\d{1,2}))?", s)
    if not m:
        return ""
    return m.group(1) + ("," + m.group(2) if m.group(2) and m.group(2) != "00" else "")


def stock_text(block):
    """Lagertekst fra varekortet -> tekst bygget forstår ('20+', '3', 'Utsolgt', 'Utsolgt, men kan bestilles')."""
    m = re.search(r'b-stock-info__in-stock">(.*?)(?=b-product-list__service-buttons|b-stock-info__out-of-stock|$)', block, re.S)
    if not m:
        return "Utsolgt"
    seg = m.group(1)
    amount = re.search(r'b-stock-info__amount">(.*?)</span>', seg, re.S)
    store = re.search(r'b-stock-info__store-name"[^>]*>(.*?)</span>', seg, re.S)
    n = re.match(r"(\d+\+?)", clean(amount.group(1))) if amount else None
    if store and re.search(r"leverand", clean(store.group(1)), re.I):
        return "Utsolgt, men kan bestilles"  # ligger hos leverandør, sendes etter noen dager
    return n.group(1) if n else "På lager"


def parse_list(page):
    """Varekort fra en kategoriside -> liste med rader (Lenke, Bilde, Navn, Farge, Pris, Førpris, Lager)."""
    out = []
    for block in page.split('<div class="b-product-list__item">')[1:]:
        if "data-product-link" not in block or "{{" in block[:600]:  # hopper over malene (Handlebars) i skriptene
            continue
        a = re.search(r'<a\s+data-product-link="?\d+"?[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not a:
            continue
        brand = re.search(r'_brand_name">(.*?)</span>', a.group(2), re.S)
        name = clean(re.sub(r'<span class="_brand_name">.*?</span>', "", a.group(2), flags=re.S))  # selve navnet, inkl. «name-tail» (vekt)
        if brand and not name.lower().startswith(clean(brand.group(1)).lower()):
            name = clean(brand.group(1)) + " " + name
        img = re.search(r'<img\b[^>]*?\bsrc="([^"]+)"', block)
        price = re.search(r'b-product-price__main[^"]*">(.*?)</span>', block, re.S)
        was = re.search(r'b-product-price__(?:old|before|regular|previous)[^"]*">(.*?)</span>', block, re.S)
        p = money(price.group(1)) if price else ""
        if not p or NOT_FILAMENT.search(name):
            continue
        href = html.unescape(a.group(1))
        out.append([href if href.startswith("http") else BASE + href, html.unescape(img.group(1)) if img else "", name, "",
                    p, money(was.group(1)) if was else "", stock_text(block)])
    return out


def total(page):
    m = re.search(r"Viser\s+\d+\s*-\s*(\d+)\s+av\s+(\d+)", clean(page))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def collect(fetch_fn=fetch):
    page = fetch_fn(CATEGORY + "/ps_100")
    rows = parse_list(page)
    shown, tot = total(page)
    n = 1
    while shown and shown < tot and n < 10:  # flere enn 100 varer: følg sidene
        n += 1
        page = fetch_fn(f"{CATEGORY}/pi_{n}/ps_100")
        got = parse_list(page)
        if not got:
            break
        rows += got
        shown = total(page)[0]
    return rows, tot


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
        dst = rest[0] if rest else "data/multicom.csv"
        rows, tot = parse_list(Path(src).read_text(encoding="utf-8")), 0
    else:
        dst = args[0] if args else "data/multicom.csv"
        rows, tot = collect()
    if tot and len(rows) < tot * 0.8:
        raise SystemExit(f"Leste {len(rows)} av {tot} varer, noe er galt. Filen ble ikke skrevet.")
    print(f"Skrev {convert(rows, dst)} rader til {dst}")


if __name__ == "__main__":
    main(sys.argv[1:])
