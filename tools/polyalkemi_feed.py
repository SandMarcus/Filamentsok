"""Henter filament fra Polyalkemi (polyalkemi.no) og skriver data/polyalkemi.csv.

Butikken har ingen åpen feed. Skriptet leser derfor de vanlige sidene (robots.txt tillater dem):
  1. /filament?pageID=110 gir alle filamentvarer i én side (ca. 38 MB) med navn, farge, varenummer, lager, bilde og lenke.
     Mislykkes det, eller blir resultatet for lite, brukes kategorisidene /filament/<materiale>?pageID=100 i stedet.
  2. Prisen fylles inn med JavaScript på listesidene, så den leses fra hver produktsides HTML (data-priceincvat).
Pris hentes med pause mellom hvert kall. Rekker ikke tiden (--budget minutter), eller feiler en side, beholdes
forrige pris fra den eksisterende CSV-en. Varer uten kjent pris tas ikke med. Feiler det stort, skrives ikke filen.

Bruk:
    python tools/polyalkemi_feed.py [data/polyalkemi.csv] [--budget 40] [--delay 0.6] [--no-price]
Utdata har samme kolonner som før: Lenke,Bilde,Navn,Farge/type,Varenummer,Lager,pris
Tomt lagerfelt betyr utsolgt (empty_stock i config/stores.json). Ren Python, ingen avhengigheter.
"""
import csv
import html
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://polyalkemi.no"
UA = "Filamentsok/1.0 (prissammenligning; +https://xn--filamentsk-8cb.no)"
CATEGORIES = ["pla", "petg", "abs", "asa", "cope", "cpe", "fleksibelt", "pa-nylon", "pc", "pctg", "pet", "pp",
              "ppa", "pps", "pva", "wood", "support", "filamentpakker"]
COLUMNS = ["Lenke", "Bilde", "Navn", "Farge/type", "Varenummer", "Lager", "pris"]


def fetch(url, retries=3, timeout=300):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "nb-NO,nb;q=0.9"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (i + 1))
    raise OSError(f"Klarte ikke hente {url}: {last}")


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def stock_text(raw):
    """Lagertekst fra butikken -> tekst bygget forstår ('20+', '7', 'Utsolgt', 'Snart 12.11.2026')."""
    s = clean(raw)
    m = re.match(r"(\d+\+?)\s+på lager", s, re.I)
    if m:
        return m.group(1)
    d = re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", s)
    if re.match(r"(forventet|ubekreftet)", s, re.I):
        return ("Snart " + d.group(0)) if d else "Utsolgt"
    return "Utsolgt"


def parse_list(page):
    """Varekort fra en kategoriside -> liste med dict (lenke, bilde, navn, farge, varenr, lager)."""
    out = []
    # Tåler både vanlig HTML og minifisert HTML (der anførselstegn rundt attributter er fjernet).
    for part in re.split(r'class="?AddProductImage"?', page)[1:]:
        link = re.search(r'href="?(/[^"\s>]+)', part)
        if not link:
            continue
        img = re.search(r'<img\b[^>]*?\bsrc="?([^"\s>]+)', part)
        h1 = re.search(r'class="?AddHeader1"?>([^<]*)', part)
        h2 = re.search(r'class="?AddHeader2"?>([^<]*)', part)
        num = re.search(r'product-desc-prod-num"?><span>([^<]*)', part)
        stock = re.search(r'class="?AddStockContainer"?>(.*?)</div>\s*</div>', part, re.S)
        if not (h1 and num):
            continue
        out.append({
            "Lenke": BASE + link.group(1),
            "Bilde": (BASE + html.unescape(img.group(1)) if img.group(1).startswith("/") else html.unescape(img.group(1))) if img else "",
            "Navn": clean(h1.group(1)),
            "Farge/type": clean(h2.group(1)) if h2 else "",
            "Varenummer": clean(num.group(1)),
            "Lager": stock_text(stock.group(1)) if stock else "Utsolgt",
        })
    return out


def parse_price(page):
    """Pris inkl. mva fra en produktside, f.eks. '209,-' eller '1 090,-'. Tom streng hvis ikke funnet."""
    m = re.search(r'data-priceincvat="([^"]*\d[^"]*)"', page)
    return clean(m.group(1)) if m else ""


def load_old(path):
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {r["Varenummer"]: r["pris"] for r in csv.DictReader(f) if r.get("pris")}


ALL_URL = BASE + "/filament?pageID=110"
MIN_ALL = 1500  # færre enn dette på hovedsiden regnes som en feil, og da brukes kategorisidene


def collect(fetch_fn=fetch):
    try:
        got = parse_list(fetch_fn(ALL_URL))
    except OSError as exc:
        print(f"Advarsel: hovedsiden: {exc}", file=sys.stderr)
        got = []
    print(f"/filament: {len(got)} varer")
    if len(got) >= MIN_ALL:
        uniq = {}
        for it in got:
            uniq.setdefault(it["Varenummer"], it)
        return list(uniq.values())
    print("For få varer på hovedsiden, bruker kategorisidene.", file=sys.stderr)
    items, seen = [], set()
    for cat in CATEGORIES:
        try:
            page = fetch_fn(f"{BASE}/filament/{cat}?pageID=100")
        except OSError as exc:
            print(f"Advarsel: {cat}: {exc}", file=sys.stderr)
            continue
        got = parse_list(page)
        print(f"{cat}: {len(got)} varer")
        for it in got:
            if it["Varenummer"] not in seen:
                seen.add(it["Varenummer"])
                items.append(it)
    return items


def add_prices(items, old, fetch_fn=fetch, delay=0.6, budget_min=40, workers=3):
    deadline = time.time() + budget_min * 60
    stats = {"ny": 0, "gammel": 0, "mangler": 0}

    def one(it):
        price = ""
        if time.time() < deadline:
            try:
                price = parse_price(fetch_fn(it["Lenke"], retries=2, timeout=60))
            except OSError:
                price = ""
            time.sleep(delay)
        if price:
            stats["ny"] += 1
        elif old.get(it["Varenummer"]):
            price = old[it["Varenummer"]]
            stats["gammel"] += 1
        else:
            stats["mangler"] += 1
        it["pris"] = price

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, items))
    return stats


def write(items, dst):
    rows = [it for it in items if it.get("pris")]
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    dst = args[0] if args and not args[0].replace(".", "").isdigit() else "data/polyalkemi.csv"
    old = load_old(dst)
    items = collect()
    if len(items) < 200:
        raise SystemExit(f"Fant bare {len(items)} varer, noe er galt. Filen ble ikke skrevet.")
    if "--no-price" in argv:
        for it in items:
            it["pris"] = old.get(it["Varenummer"], "")
        stats = {"ny": 0, "gammel": sum(1 for it in items if it["pris"]), "mangler": sum(1 for it in items if not it["pris"])}
    else:
        stats = add_prices(items, old, delay=opt("--delay", 0.6), budget_min=opt("--budget", 40))
    n = write(items, dst)
    print(f"Skrev {n} rader til {dst} (pris: {stats['ny']} nye, {stats['gammel']} fra forrige fil, {stats['mangler']} mangler)")


if __name__ == "__main__":
    main(sys.argv[1:])
