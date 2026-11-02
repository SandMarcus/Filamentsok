"""Henter filament fra Dustin (dustin.no) og skriver data/dustin.csv.

Bruk:
    python tools/dustin_feed.py [data/dustin.csv]                          # henter kategorisidene
    python tools/dustin_feed.py data/dustin.csv --sample side.html [side2.html ...]   # leser lagrede sider (uten nett)

Dustin har ingen åpen feed. Kategorien «Forbruksvarer til 3D-skrivere» (`?page=N`, 18 varer per side, sidene overlapper litt) har varelisten
som JSON i sidens `self.__next_f.push`-data (`searchResultProduct`). Skriptet leser den (ikke HTML-kortene) og tar bare
med filament (varer med materiale og tykkhet 1,75/2,85 mm, eller filament i navnet), ikke dyser, byggeplater osv.
Prisen i JSON-en uten mva står i `price`, mens `priceIncludingVat` er prisen kunden betaler. Den siste brukes.
Lager er `internalStock.quantity` når varen kan kjøpes, ellers «Utsolgt».
Utdata har kolonnene Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager. Feiler noe, skrives ikke filen. Ren Python.
"""
import csv
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://www.dustin.no"
CATEGORY = BASE + "/group/hardware/skrivere-forbruksvarer/blekk-tonere-og-forbruksvarer/forbruksvarer-til-3d-skrivere"
UA = "Filamentsok/1.0 (prissammenligning; +https://xn--filamentsk-8cb.no)"
COLUMNS = ["Lenke", "Bilde", "Navn", "Farge", "Pris", "Førpris", "Lager"]
PUSH = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')
NOT_FILAMENT = re.compile(r"dyse|nozzle|byggeplate|build ?plate|hotend|tørk|dryer|sensor|verktøy|spatel|lim\b|resin|harpiks", re.I)
IS_FILAMENT = re.compile(r"filament|\b(pla|petg|abs|asa|tpu|pva|nylon|pet-g)\b", re.I)


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


def flight_text(page):
    """Setter sammen dataene fra alle `self.__next_f.push([1,"..."])` i siden."""
    out = []
    for m in PUSH.finditer(page):
        try:
            out.append(json.loads(m.group(1)))
        except ValueError:
            continue
    return "".join(out)


def parse_page(page):
    """(produktliste, antall treff totalt) fra en kategoriside."""
    txt = flight_text(page)
    dec = json.JSONDecoder()
    prods = []
    for m in re.finditer(r'"searchResultProduct":', txt):
        try:
            obj, _ = dec.raw_decode(txt, m.end())
        except ValueError:
            continue
        prods.append(obj)
    hits = re.search(r'"productHits":(\d+)', txt)
    return prods, int(hits.group(1)) if hits else len(prods)


def spec(p, name):
    for s in p.get("promotedSpecifications") or []:
        if s.get("name") == name:
            return (s.get("value") or "").strip()
    return ""


def is_filament(p):
    name = f"{p.get('displayName', '')} {p.get('englishFullDisplayName', '')}"
    if NOT_FILAMENT.search(name):
        return False
    thick = spec(p, "Tykkhet")
    return bool((spec(p, "Printmateriale") and re.match(r"(1[.,]75|2[.,]85)", thick)) or IS_FILAMENT.search(name))


def kr(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return ""
    if x <= 0:
        return ""
    x = round(x)
    return str(int(x))


def row(p):
    pr = p.get("price") or {}
    price = kr(pr.get("priceIncludingVat") or pr.get("price"))
    if not price:
        return None
    ex, orig = pr.get("price") or 0, pr.get("originalPrice") or 0
    was = ""
    if pr.get("isCampaign") and ex and orig and orig > ex and pr.get("priceIncludingVat"):
        was = kr(orig * pr["priceIncludingVat"] / ex)
        if was and float(was) <= float(price):
            was = ""
    av = p.get("availability") or {}
    qty = (av.get("internalStock") or {}).get("quantity") or 0
    if av.get("isAvailableForSale") and qty > 0:
        stock = str(qty)
    elif av.get("isAvailableForSale"):
        stock = "På lager"
    else:
        stock = "Utsolgt"
    brand = (p.get("manufacturerName") or "").strip()
    title = (p.get("displayName") or "").strip()
    name = title if brand.lower() in title.lower() else f"{brand} {title}".strip()
    img = p.get("primaryImageId") or ""
    stem = img.rsplit(".", 1)[0]
    image = f"https://cf-images.dustin.eu/cdn-cgi/image/format=auto,quality=75,width=300,fit=contain/image/{stem}/{img}" if img else ""
    link = f"{BASE}/product/{p['id']}/{p.get('nameSlug', '')}".rstrip("/")
    color = spec(p, "Farge(r) i blekkpatroner")
    if "," in color or "/" in color:
        color = "Flerfarget"  # f.eks. «Rosa, Gul» (dual-color silke)
    return [link, image, name, color, price, was, stock]


def all_pages(fetch_fn=fetch, max_pages=12, delay=1.0):
    """Blar gjennom `?page=N` til alle treff er funnet. Rekkefølgen mellom sidene er ikke helt stabil hos Dustin (side 2 gjentar
    noen varer fra side 1), så varene slås sammen på id. Stopper når alle treff er funnet, når en side er tom, eller når to
    sider på rad ikke gir noe nytt."""
    prods, seen = [], set()
    total, stale = None, 0
    for n in range(1, max_pages + 1):
        if n > 1 and delay:
            time.sleep(delay)
        got, hits = parse_page(fetch_fn(CATEGORY + (f"?page={n}" if n > 1 else "")))
        total = hits if total is None else total
        if not got:
            break
        new = [p for p in got if p["id"] not in seen]
        for p in new:
            seen.add(p["id"])
        prods += new
        stale = 0 if new else stale + 1
        if len(seen) >= total or stale >= 2:
            break
    if total and len(seen) < total:
        print(f"Advarsel: fant {len(seen)} av {total} varer i kategorien.", file=sys.stderr)
    return prods


def rows_from_products(prods):
    rows, seen = [], set()
    for p in prods:
        if not is_filament(p):
            continue
        r = row(p)
        if r and r[0] not in seen:
            seen.add(r[0])
            rows.append(r)
    return rows


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
        i = argv.index("--sample")
        files = [a for a in argv[i + 1:] if not a.startswith("--")]
        dst = next((a for a in args if a not in files), "data/dustin.csv")
        prods = []
        for f in files:
            prods += parse_page(Path(f).read_text(encoding="utf-8"))[0]
    else:
        dst = args[0] if args else "data/dustin.csv"
        prods = all_pages()
    print(f"Skrev {convert(rows_from_products(prods), dst)} rader til {dst}")


if __name__ == "__main__":
    main(sys.argv[1:])
