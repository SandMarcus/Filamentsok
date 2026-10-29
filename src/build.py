"""Bygger dist/ til GitHub Pages: products.json fra CSV-filene og malen config/stores.json, pluss nettsiden.

Bruk:   python -m src.build            (bygger dist/)
        python -m src.build --strict   (feiler hvis noe ser galt ut, brukes i GitHub Actions)
Ingen avhengigheter utenom Python 3.9+.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

from .csvparse import parse_price, parse_stock
from .csvparse import weight_kg
from .enrich import REJECT, enrich
from .grouping import group

ROOT = Path(__file__).resolve().parent.parent
SITE_COLORS = {"Svart", "Hvit", "Grå", "Rød", "Blå", "Grønn", "Gul", "Oransje", "Lilla", "Rosa", "Gull", "Sølv", "Brun",
               "Beige", "Turkis", "Naturell", "Gjennomsiktig", "Flerfarget"}
MONTHS = ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "desember"]


def analytics_config(root):
    """Leser GOATCOUNTER_CODE (GitHub-variabel), ellers valgfri config/analytics.json. Tomt betyr avslått."""
    d = {}
    f = root / "config" / "analytics.json"
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
    gc = (os.environ.get("GOATCOUNTER_CODE") or str(d.get("goatcounter", ""))).strip().lower()
    if gc and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", gc):
        raise ConfigError("analytics: GOATCOUNTER_CODE må være kun bokstaver, tall og bindestrek")
    return gc


def inject_analytics(html, gc=""):
    """Setter inn GoatCounter (uten cookies) og en kort merknad i bunnteksten, eller fjerner plassholderne."""
    script = note = ""
    if gc:
        script = (f'<script data-goatcounter="https://{gc}.goatcounter.com/count" '
                  'async src="//gc.zgo.at/count.js"></script>')
        note = " · Anonym besøksstatistikk, uten cookies"
    return html.replace("<!--__ANALYTICS__-->", script).replace("<!--__ANALYTICS_NOTE__-->", note)


class ConfigError(Exception):
    pass


def norwegian_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day}. {MONTHS[d.month - 1]} {d.year}"


def cell(row, spec, *, store, path, optional=False, missing=None):
    """Henter en eller flere kolonner. spec er et kolonnenavn, en liste av kolonnenavn (slås sammen med mellomrom) eller None.
    Valgfrie kolonner (lager, bilde, merke ...) som mangler i filen gir tom tekst og en merknad, ikke feil."""
    if not spec:
        return ""
    names = [spec] if isinstance(spec, str) else list(spec)
    parts = []
    for n in names:
        if n not in row and optional:
            if missing is not None:
                missing.add(n)
            continue
        if n not in row:
            raise ConfigError(f"{store}: kolonnen «{n}» finnes ikke i {path}. Kolonner i filen: {', '.join(row.keys())}")
        parts.append((row[n] or "").strip())
    return " ".join(p for p in parts if p)


ACRONYMS = {"PLA", "PETG", "PET", "TPU", "ABS", "ASA", "PC", "CF", "GF", "HT", "ESD", "PA", "PA6", "PA11", "PA12", "PEI", "PEEK", "PPS",
            "PPA", "HIPS", "PVA", "BVOH", "CR", "UV", "LCF", "TPE", "PCTG", "EPLA", "ABS+", "PLA+", "PETG+"}
BRAND_CASE = {"ESUN": "eSUN", "PRIMASELECT": "PrimaSelect", "PRIMACREATOR": "PrimaCreator", "3DXTECH": "3DXTech", "BASF": "BASF",
              "RAISE3D": "Raise3D", "COPYMASTER3D": "Copymaster3D", "EASYPRINT": "EasyPrint", "EASYFLEX": "EasyFlex",
              "POLYMAKER": "Polymaker", "CREALITY": "Creality", "SUNLU": "Sunlu", "ELEGOO": "Elegoo", "POLYTERRA": "PolyTerra",
              "POLYLITE": "PolyLite", "POLYFLEX": "PolyFlex", "ULTRAFUSE": "Ultrafuse", "NYLONPOWER": "NylonPower",
              "PRIMACREATOR™": "PrimaCreator™", "COPYMASTER": "Copymaster", "ADDNORTH": "Addnorth"}


def smart_case(name):
    """«CREALITY CR-PLA MATTE – 1.75 MM – 1 KG» -> «Creality CR-PLA Matte – 1.75 mm – 1 kg». Bare for navn som er skrevet med store bokstaver."""
    if name != name.upper() or not any(ch.isalpha() for ch in name):
        return name

    def word(w):
        up = w.upper()
        if up in BRAND_CASE:
            return BRAND_CASE[up]
        m = re.fullmatch(r"(\d+(?:[.,]\d+)?)(MM|KG|G|GR|M)", up)
        if m:
            return m.group(1) + " " + m.group(2).lower()
        if up in ACRONYMS or re.fullmatch(r"[A-Z]{1,2}\d*\+?", up) or any(c.isdigit() for c in up):
            return up.lower() if up in ("MM", "KG", "G") else up
        return up.capitalize()

    def token(t):
        return "-".join(word(part) for part in t.split("-"))
    return re.sub(r"\s+", " ", " ".join(token(t) for t in name.split(" "))).strip()


def apply_sale(offer, sale_text, onsale_text, cfg, report, name):
    """Tilbud: kolonnen «sale_price» er den andre prisen, «onsale» er merket (for eksempel «Tilbud!»).
    Kun rader som er merket som tilbud brukes. Lavest pris blir prisen, høyest blir førprisen.
    Er forskjellen urimelig stor (over 3 ganger) ignoreres tilbudet, og raden meldes som merknad."""
    if not sale_text:
        return
    other = parse_price(sale_text)
    main = offer["price"]
    if cfg["columns"].get("onsale") and not onsale_text.strip():
        if other and main and max(other, main) / min(other, main) > 1.0:
            report["merknader"].append(f"{cfg['id']}: «{name}» har to priser ({main:g} og {other:g}) men er ikke merket som tilbud. Bruker {main:g}")
        return
    if not (other and main) or other == main:
        return
    low, high = min(main, other), max(main, other)
    if high / low > 3:
        report["merknader"].append(f"{cfg['id']}: «{name}» er merket som tilbud, men prisene ({main:g} og {other:g}) ser feil ut. Bruker {main:g} uten tilbud")
        return
    offer["price"], offer["was"] = low, high


def read_store(cfg, report):
    store, path = cfg["id"], ROOT / cfg["file"]
    if not path.exists():
        raise ConfigError(f"{store}: finner ikke {cfg['file']}")
    cols = cfg["columns"]
    out = []
    absent = set()
    with open(path, encoding=cfg.get("encoding", "utf-8-sig"), newline="") as f:
        reader = csv.DictReader(f, delimiter=cfg.get("delimiter", ","))
        for n, row in enumerate(reader, start=2):
            c = lambda k: cell(row, cols.get(k), store=store, path=cfg["file"],
                               optional=k not in ("name", "price"), missing=absent)
            name = c("name")
            if cfg.get("smart_case"):
                name = smart_case(name)
            if not name:
                report["skipped"][store + ": tomt navn"] += 1
                continue
            if any(r in name.lower() for r in REJECT) or re.search(r"(?<![a-z])clean(?![a-z])", name.lower()):
                report["skipped"][store + ": ikke filament"] += 1
                continue
            brand_hint = c("brand")
            if cfg.get("brand_strip") and brand_hint.startswith(cfg["brand_strip"]):
                brand_hint = brand_hint[len(cfg["brand_strip"]):].strip()
            e = enrich(name, brand_hint or None, None, c("color") or None)
            brand = e.brand or brand_hint or cfg.get("default_brand") or "Andre"
            kg = weight_kg(
                name, rolls_as_kg=cfg.get("rolls_as_kg", False), default_kg=cfg.get("default_kg"),
                default_kg_brands=cfg.get("default_kg_brands"), brand=brand, material=e.ui_material, additive=e.additive)
            stock_text = c("stock") or c("stock_fallback")
            if not stock_text and cfg.get("empty_stock"):
                stock_text = cfg["empty_stock"]  # tomt lagerfelt betyr utsolgt i denne butikkens fil
            url = c("url")
            if url and not re.match(r"https?://", url):
                url = urljoin(cfg.get("url_base", cfg["home"]), url)
            image = c("image")
            offer = {
                "store": store, "name": name, "brand": brand, "mat": e.ui_material, "fin": e.finish,
                "col": e.color if e.color in SITE_COLORS else "Ikke oppgitt", "add": e.additive, "kg": kg,
                "price": parse_price(c("price")), "was": 0, "url": url or None, "avail": parse_stock(stock_text),
                "img": image if image.startswith("http") else None,
            }
            apply_sale(offer, c("sale_price"), c("onsale"), cfg, report, name)
            was = parse_price(c("was"))
            if was and offer["price"] and was > offer["price"] and was / offer["price"] <= 3:
                offer["was"] = was
            out.append(offer)
    if absent:
        report["merknader"].append(f"{store}: kolonnene {', '.join(sorted(absent))} finnes ikke i {cfg['file']} og er hoppet over")
    return out


def compact(o, product_name):
    d = {"s": o["store"]}
    if o["price"] is not None:
        d["p"] = round(o["price"], 2) if o["price"] % 1 else int(o["price"])
    if o["url"]:
        d["u"] = o["url"]
    if o.get("was") and o["price"] is not None and o["was"] > o["price"]:
        d["w"] = round(o["was"], 2) if o["was"] % 1 else int(o["was"])
    if o["avail"]:
        d["a"] = o["avail"]
    if o["img"]:
        d["i"] = o["img"]
    if o["name"] != product_name:
        d["n"] = o["name"]
    return d


def build_products(offers):
    products = []
    for g in group(offers):
        g = sorted(g, key=lambda o: (o["price"] is None, o["price"] or 0))
        first = g[0]
        p = {"id": "p%d" % len(products), "brand": first["brand"], "name": first["name"], "mat": first["mat"],
             "fin": first["fin"], "col": first["col"]}
        if first["add"]:
            p["add"] = first["add"]
        if first["kg"]:
            p["kg"] = first["kg"]
        p["offers"] = [compact(o, first["name"]) for o in g]
        products.append(p)
    return products


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--config", default=str(ROOT / "config" / "stores.json"))
    ap.add_argument("--out", default=str(ROOT / "dist"))
    args = ap.parse_args(argv)

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    report = {"skipped": Counter(), "stores": {}, "warnings": [], "merknader": []}
    offers = []
    for s in cfg["stores"]:
        rows = read_store(s, report)
        offers += rows
        n = len(rows)
        report["stores"][s["id"]] = {
            "tilbud": n,
            "uten_pris": sum(o["price"] is None for o in rows),
            "uten_vekt": sum(o["kg"] is None for o in rows),
            "uten_farge": sum(o["col"] == "Ikke oppgitt" for o in rows),
            "uten_materiale": sum(o["mat"] == "Annet" for o in rows),
            "uten_lenke": sum(o["url"] is None for o in rows),
        }
        if n == 0:
            report["warnings"].append(f"{s['id']}: ingen rader")
        elif report["stores"][s["id"]]["uten_pris"] / n > 0.25 and s["id"] != "clas":
            report["warnings"].append(f"{s['id']}: over 25 % uten pris. Sjekk kolonnen for pris i malen")

    products = build_products(offers)
    snapshot = cfg.get("snapshot") or dt.date.today().isoformat()
    body = {
        "v": 1,
        "snapshot": norwegian_date(snapshot),
        "stores": {s["id"]: {"n": s["name"], "home": s["home"]} for s in cfg["stores"]},
        "products": products,
    }
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    build_id = hashlib.sha1(payload.encode()).hexdigest()[:10]

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "web", out)
    (out / "products.json").write_text(payload, encoding="utf-8")
    gc = analytics_config(ROOT)
    for page in ("index.html", "guide/index.html", "partner/index.html", "funksjoner/index.html", "3d-print/index.html"):
        f = out / page
        if f.exists():
            f.write_text(inject_analytics(f.read_text(encoding="utf-8").replace("__BUILD__", build_id), gc), encoding="utf-8")
    guide = ROOT / "data" / "guide.json"
    if guide.exists():
        shutil.copy(guide, out / "guide.json")
    (out / ".nojekyll").write_text("")

    multi = sum(len({o["s"] for o in p["offers"]}) > 1 for p in products)
    report["produkter"] = len(products)
    report["tilbud"] = len(offers)
    report["produkter_i_flere_butikker"] = multi
    report["materialer"] = dict(Counter(p["mat"] for p in products).most_common())
    report["products_json_kb"] = round(len(payload.encode()) / 1024)
    report["build"] = build_id
    report["skipped"] = dict(report["skipped"])
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text("### Bygg\n```json\n" + text + "\n```\n", encoding="utf-8")
    if args.strict and report["warnings"]:
        print("Feil: " + "; ".join(report["warnings"]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConfigError as exc:
        print(f"Feil i malen: {exc}", file=sys.stderr)
        sys.exit(2)
