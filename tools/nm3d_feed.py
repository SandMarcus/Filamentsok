"""Henter filament fra NorMax3D (nm3d.no) via WooCommerce sitt åpne Store API og skriver data/normax3d.csv.

Bruk:
    python tools/nm3d_feed.py [data/normax3d.csv]                 # henter fra nettet
    python tools/nm3d_feed.py data/normax3d.csv --sample side.json  # leser en lagret JSON-side (uten nett)

Hvert produkt med varianter (farge, vekt) blir én rad per variant, med egen pris, førpris, lager og bilde.
Utdata har kolonnene Lenke,Bilde,Navn,Farge,Pris,Førpris,Lager, slik malen i config/stores.json forventer.
Priser er oppgitt i øre i API-et og inkluderer mva. Feiler noe, skrives ikke filen, så den gamle blir liggende.
Ren Python, ingen avhengigheter.
"""
import csv
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://nm3d.no/wp-json/wc/store/v1"
UA = "Filamentsok/1.0 (prissammenligning; +https://xn--filamentsk-s5a.no)"
WEIGHT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kg|g)\b", re.I)
SIZE_ATTR = re.compile(r"vekt|weight|størrelse|pakke|mengde", re.I)
COLOR_ATTR = re.compile(r"farge|color|colour", re.I)


def fetch_json(url, retries=3):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (i + 1))
    raise SystemExit(f"Klarte ikke hente {url}: {last}")


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def is_filament(p):
    slugs = [c["slug"] for c in p.get("categories", [])]
    # «filament» og «filament-og-resin» (også merkenes underkategorier, som «raise3d-filament-og-resin»).
    # «filament-lagring» (tørkebokser og lagring) er tilbehør og tas ikke med.
    if not any(s == "filament" or s.endswith("filament-og-resin") for s in slugs):
        return False
    # Harpiks (resin) og underkategorier av den er ikke filament.
    return not any("resin" in s and not s.endswith("filament-og-resin") for s in slugs)


def money(prices, key):
    """Pris i øre (tekst) -> kroner som tekst med komma, eller ''."""
    raw = (prices or {}).get(key)
    if raw in (None, ""):
        return ""
    minor = int((prices or {}).get("currency_minor_unit", 2))
    v = int(raw) / (10 ** minor)
    return ("%d" % v) if v == int(v) else ("%.2f" % v).replace(".", ",")


def stock_text(p):
    if p.get("is_on_backorder"):
        return "Utsolgt, men kan bestilles"
    if not p.get("is_in_stock", True):
        return "Utsolgt"
    txt = clean((p.get("stock_availability") or {}).get("text"))
    if re.match(r"\d+\+? på lager", txt):
        return re.match(r"\d+\+? på lager", txt).group(0)
    if "kan bestilles" in txt.lower():
        return "Utsolgt, men kan bestilles"
    return "På lager"


def attr_terms(p, pattern):
    """Navn på verdiene til attributtet som matcher mønsteret (verdiene kan være tekst eller objekter)."""
    for a in p.get("attributes", []):
        if re.search(pattern, a.get("name", ""), re.I):
            return [clean(t.get("name", "") if isinstance(t, dict) else t) for t in a.get("terms", [])]
    return []


def tag_weight(p):
    """Vekt fra etiketten (for eksempel «750g filament») eller attributtet «Vekt» når navnet ikke har noen."""
    for t in p.get("tags", []):
        m = WEIGHT_RE.fullmatch(clean(t.get("name", "")).replace(" filament", "").strip())
        if m:
            return m.group(0).replace(" ", "")
    terms = attr_terms(p, r"^(vekt|weight)$")
    if len(terms) == 1:
        m = WEIGHT_RE.fullmatch(terms[0].replace(" ", ""))
        if m:
            return m.group(0)
    return ""


def term_names(p):
    out = {}
    for a in p.get("attributes", []):
        out[a["name"].lower()] = {t["slug"].lower(): clean(t["name"]) for t in a.get("terms", [])}
    return out


def variant_label(p, variant):
    """Gir (tekst som legges til navnet, farge) for en variant."""
    terms = term_names(p)
    parts, color = [], ""
    for a in variant.get("attributes", []):
        name, val = a.get("name", ""), a.get("value", "")
        shown = terms.get(name.lower(), {}).get(val.lower(), clean(val))
        if not shown:
            continue
        if COLOR_ATTR.search(name):
            color = shown
        parts.append(shown)
    return " ".join(parts), color


def get_variations(p, fetch):
    """Henter hver variant som eget produkt (pris, lager, bilde). Faller tilbake til foreldreproduktet."""
    out = {}
    try:
        lst = fetch(f"{BASE}/products?type=variation&parent={p['id']}&per_page=100")
        if isinstance(lst, list):
            out = {v["id"]: v for v in lst if v.get("parent") in (p["id"], 0, None) or v.get("id")}
    except SystemExit:
        out = {}
    for v in p.get("variations", []):
        if v["id"] in out:
            continue
        try:
            one = fetch(f"{BASE}/products/{v['id']}")
            if isinstance(one, dict) and one.get("prices"):
                out[v["id"]] = one
        except SystemExit:
            pass
        time.sleep(0.2)
    return out


def rows_for(p, fetch=None):
    base_name = clean(p["name"])
    has_w = bool(WEIGHT_RE.search(base_name))
    extra_w = "" if has_w else tag_weight(p)
    img = (p.get("images") or [{}])[0].get("src", "")
    link = p["permalink"]
    out = []
    if p["type"] == "variable" and p.get("variations"):
        rng = (p.get("prices") or {}).get("price_range")
        if not fetch and rng and rng.get("min_amount") != rng.get("max_amount"):
            return []  # uten nett vet vi ikke prisen per variant, så produktet venter til neste kjøring med nett
        full = get_variations(p, fetch) if fetch else {}
        for v in p["variations"]:
            src = full.get(v["id"], p)
            pr = src.get("prices") or p["prices"]
            label, color = variant_label(p, v)
            name = " ".join(x for x in (base_name, label, extra_w) if x)
            vimg = (src.get("images") or [{}])[0].get("src", "") or img
            was = money(pr, "regular_price") if src.get("on_sale") else ""
            out.append([link, vimg, name, color, money(pr, "price"), was, stock_text(src if src is not p else p)])
    else:
        pr = p["prices"]
        name = " ".join(x for x in (base_name, extra_w) if x)
        was = money(pr, "regular_price") if p.get("on_sale") else ""
        colors = attr_terms(p, r"^(farge|color|colour)$")
        out.append([link, img, name, colors[0] if len(colors) == 1 else "", money(pr, "price"), was, stock_text(p)])
    return [r for r in out if r[4]]


def all_products(fetch):
    page, res = 1, []
    while True:
        batch = fetch(f"{BASE}/products?per_page=100&page={page}")
        if not isinstance(batch, list) or not batch:
            break
        res += batch
        if len(batch) < 100:
            break
        page += 1
        time.sleep(0.3)
    return res


def convert(products, dst, fetch=None, keep=None):
    keep = keep or is_filament
    rows = []
    for p in products:
        if p.get("parent") or not keep(p):
            continue
        rows += rows_for(p, fetch)
    if not rows:
        raise SystemExit("Fant ingen filamentrader. Filen ble ikke skrevet.")
    seen, uniq = set(), []
    for r in rows:
        key = (r[0], r[2])
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
    dst = args[0] if args else "data/normax3d.csv"
    if "--sample" in argv:
        src = argv[argv.index("--sample") + 1]
        dst = [a for a in args if a != src][0] if len([a for a in args if a != src]) else dst
        products = json.loads(Path(src).read_text(encoding="utf-8"))
        n = convert(products, dst, fetch=None)
    else:
        n = convert(all_products(fetch_json), dst, fetch=fetch_json)
    print(f"Skrev {n} rader til {dst}")


if __name__ == "__main__":
    main(sys.argv[1:])
