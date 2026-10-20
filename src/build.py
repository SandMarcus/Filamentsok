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

from .csvparse import parse_price, parse_stock, weight_kg
from .enrich import REJECT, enrich
from .grouping import group

ROOT = Path(__file__).resolve().parent.parent
SITE_COLORS = {"Svart", "Hvit", "Grå", "Rød", "Blå", "Grønn", "Gul", "Oransje", "Lilla", "Rosa", "Gull", "Sølv", "Brun",
               "Beige", "Turkis", "Naturell", "Gjennomsiktig", "Flerfarget"}
MONTHS = ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "desember"]


class ConfigError(Exception):
    pass


def norwegian_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day}. {MONTHS[d.month - 1]} {d.year}"


def cell(row, spec, *, store, path):
    """Henter en eller flere kolonner. spec er et kolonnenavn, en liste av kolonnenavn (slås sammen med mellomrom) eller None."""
    if not spec:
        return ""
    names = [spec] if isinstance(spec, str) else list(spec)
    parts = []
    for n in names:
        if n not in row:
            raise ConfigError(f"{store}: kolonnen «{n}» finnes ikke i {path}. Kolonner i filen: {', '.join(row.keys())}")
        parts.append((row[n] or "").strip())
    return " ".join(p for p in parts if p)


def read_store(cfg, report):
    store, path = cfg["id"], ROOT / cfg["file"]
    if not path.exists():
        raise ConfigError(f"{store}: finner ikke {cfg['file']}")
    cols = cfg["columns"]
    out = []
    with open(path, encoding=cfg.get("encoding", "utf-8-sig"), newline="") as f:
        reader = csv.DictReader(f, delimiter=cfg.get("delimiter", ","))
        for n, row in enumerate(reader, start=2):
            c = lambda k: cell(row, cols.get(k), store=store, path=cfg["file"])
            name = c("name")
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
            url = c("url")
            if url and not re.match(r"https?://", url):
                url = urljoin(cfg.get("url_base", cfg["home"]), url)
            image = c("image")
            offer = {
                "store": store, "name": name, "brand": brand, "mat": e.ui_material, "fin": e.finish,
                "col": e.color if e.color in SITE_COLORS else "Ikke oppgitt", "add": e.additive, "kg": kg,
                "price": parse_price(c("price")), "url": url or None, "avail": parse_stock(stock_text),
                "img": image if image.startswith("http") else None, "was": 0,
            }
            out.append(offer)
    return out


def compact(o, product_name):
    d = {"s": o["store"]}
    if o["price"] is not None:
        d["p"] = round(o["price"], 2) if o["price"] % 1 else int(o["price"])
    if o["url"]:
        d["u"] = o["url"]
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
    report = {"skipped": Counter(), "stores": {}, "warnings": []}
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
    for page in ("index.html", "guide/index.html"):
        f = out / page
        if f.exists():
            f.write_text(f.read_text(encoding="utf-8").replace("__BUILD__", build_id), encoding="utf-8")
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
