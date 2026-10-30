"""Henter 3D-filament fra Tonerweb (tonerweb.no) og skriver data/tonerweb.csv.

Bruk:
    python tools/tonerweb_feed.py [data/tonerweb.csv]                  # henter kategorisiden
    python tools/tonerweb_feed.py data/tonerweb.csv --sample side.html # leser en lagret side (uten nett)

Tonerweb har ingen åpen feed, så vi leser varelisten på kategorisiden «3D Filament». Kategorien er liten
(rundt 15 varer, 20 per side). Utdata har kolonnene Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager.
Prisene inkluderer mva. Feiler noe, skrives ikke filen, så den gamle blir liggende. Ren Python, ingen avhengigheter.
"""
import csv
import html
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://www.tonerweb.no"
CATEGORY = BASE + "/k/kontormaskiner/skrivere/3d_skrivere/3d_filament"
UA = "Filamentsok/1.0 (prissammenligning; +https://xn--filamentsk-8cb.no)"
COLUMNS = ["Lenke", "Bilde", "Navn", "Farge", "Pris", "Førpris", "Lager"]
NOT_FILAMENT = re.compile(r"tørk|dryer|dry box|hotend|dyse|nozzle|byggeplate|printer\b(?!\s+filament)|sensor|verktøy", re.I)


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
    """«315,-» -> «315», «1 290,-» -> «1290», «299,90» -> «299,90». Tomt hvis ikke et tall."""
    s = re.sub(r"[\s ]", "", clean(text))
    m = re.match(r"(\d+)(?:[,.](\d{1,2}))?", s)
    if not m:
        return ""
    return m.group(1) + ("," + m.group(2) if m.group(2) and m.group(2) != "00" else "")


def stock_text(info):
    """«Lagerstatus:1 stk på lokallager.» -> «1», «2 stk på fjernlager» -> «2» (sendes om 1-3 dager), ellers «Utsolgt»."""
    m = re.search(r"Lagerstatus:\s*(\d+)\s*stk\s+på\s+(?:lokal|fjern)lager", info, re.I)
    return m.group(1) if m else "Utsolgt"


def name_of(block):
    m = re.search(r'data-fullname="([^"]*)"', block)
    name = clean(m.group(1)) if m else clean((re.search(r'itemprop="name">(.*?)</h3>', block, re.S) or [None, ""])[1])
    brand = clean((re.search(r'data-manufacturer="([^"]*)"', block) or [None, ""])[1])
    name = re.sub(r"^VERB\.\s*", "Verbatim ", name)
    name = re.sub(r"\bBl\b", "Blå", name)  # Verbatim forkorter fargene («1KG Bl», «Rd TRANSPARENT»)
    name = re.sub(r"\bRd\b", "Rød", name)
    name = re.sub(r"\bSort\b", "Svart", name)
    if brand and brand.lower() not in name.lower():
        name = brand + " " + name
    return name


def parse_list(page):
    """Varekort fra en kategoriside -> liste med rader (Lenke, Bilde, Navn, Farge, Pris, Førpris, Lager)."""
    out = []
    for block in page.split('class="full-view-product product-item')[1:]:
        pid = re.search(r'data-id="(\d+)"', block)
        price = re.search(r'itemprop="price"\s+content="([^"]*)"', block)
        if not pid or not price:
            continue
        name = name_of(block)
        p = money(price.group(1))
        if not p or NOT_FILAMENT.search(name):
            continue
        img = re.search(r'itemprop="image"\s+src="([^"]*)"', block)
        src = html.unescape(img.group(1)) if img else ""
        if not src or "no_image" in src:
            src = ""
        elif src.startswith("/"):
            src = BASE + src
        elif not src.startswith("http"):
            src = BASE + "/" + src
        was = re.search(r'class="before_price">([^<]*)', block)
        info = clean(re.search(r'<ul class="mt-10 list-unstyled">(.*?)</ul>', block, re.S).group(1)) if re.search(r'<ul class="mt-10', block) else ""
        out.append([f"{BASE}/pv.php?pid={pid.group(1)}", src, name, "", p, money(was.group(1)) if was else "", stock_text(info)])
    return out


def page_info(page):
    """(antall på siden, antall per side) fra rutenettet, eller (0, 0)."""
    m = re.search(r'id="category-products-grid"[^>]*?data-per_page="(\d+)"[^>]*?data-items="(\d+)"', page)
    return (int(m.group(2)), int(m.group(1))) if m else (0, 0)


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
        dst = rest[0] if rest else "data/tonerweb.csv"
        page = Path(src).read_text(encoding="utf-8")
    else:
        dst = args[0] if args else "data/tonerweb.csv"
        page = fetch(CATEGORY)
    rows = parse_list(page)
    items, per_page = page_info(page)
    if items and len(rows) < items * 0.8:
        raise SystemExit(f"Leste {len(rows)} av {items} varer, noe er galt. Filen ble ikke skrevet.")
    if per_page and items >= per_page:
        print(f"Advarsel: siden viser {items} varer (maks per side), det kan finnes flere sider. Sjekk kategorien.", file=sys.stderr)
    print(f"Skrev {convert(rows, dst)} rader til {dst}")


if __name__ == "__main__":
    main(sys.argv[1:])
