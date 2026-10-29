"""3D-printere: leser data/printers_<butikk>.csv fra butikkene som har automatisk feed, slår sammen samme modell på tvers
av butikker og lager printers.json til siden /3d-printere/. Ren Python, ingen avhengigheter."""
import csv
import html
import re
from pathlib import Path

from .csvparse import parse_price, parse_stock

BRANDS = ["Bambu Lab", "Creality", "Anycubic", "Elegoo", "Prusa", "Flashforge", "Snapmaker", "Raise3D", "CreatBot",
          "Mingda", "FLSUN", "PioCreat", "Artillery", "Qidi", "Sovol", "Ultimaker", "UltiMaker", "Formlabs", "Phrozen",
          "BIQU", "Voron", "Zortrax", "Kingroon", "Two Trees", "Longer", "Peopoly", "Sunlu", "Nobufil", "Atomstack", "xTool",
          "Fiberlogy", "Markforged", "Stratasys", "BCN3D", "Anker", "Eufy", "Geeetech", "Tronxy", "Wanhao", "Uniz", "Copymaster3D", "Modix"]
RESIN_RE = re.compile(r"\b(mars|saturn|jupiter|photon|halot|phrozen|sonic|form ?[1-9]l?|resin|sla|dlp|lcd|mercury)\b", re.I)
OTHER_RE = re.compile(r"laser|cnc|gravør|engrav|xtool|falcon|scanner|vinyl", re.I)
DROP_WORDS = {"3d", "printer", "printers", "fdm", "the", "with", "and", "og", "med"}


def detect_brand(name):
    low = name.lower()
    for b in sorted(BRANDS, key=len, reverse=True):
        if low.startswith(b.lower()):
            return b
    for b in sorted(BRANDS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(b.lower()) + r"\b", low):
            return b
    return name.split(" ")[0] if name else "Annet"


def guess_type(name, given):
    if given in ("FDM", "Resin"):
        return given
    if OTHER_RE.search(name):
        return "Annet"
    return "Resin" if RESIN_RE.search(name) else "FDM"


def model_key(name, brand):
    s = name.lower()
    if s.startswith(brand.lower()):
        s = s[len(brand):]
    toks = [t for t in re.sub(r"[^a-z0-9æøå+]+", " ", s).split() if t not in DROP_WORDS]
    return " ".join(toks)


def fix_case(name):
    """«CREALITY ENDER-3 V3 KE» -> «Creality Ender-3 V3 KE»: ord i store bokstaver beholdes bare hvis de har tall eller er korte."""
    if not name.isupper():
        return name
    return " ".join(w if (len(w) <= 2 or any(c.isdigit() for c in w)) else w.capitalize() for w in name.split(" "))


def display_name(name, brand):
    name = fix_case(name)
    return name if name.lower().startswith(brand.lower()) else f"{brand} {name}"


def read_file(path, store_id, report):
    """Rader som dict. Mangler filen, noteres det i rapporten, men det er ikke en feil."""
    path = Path(path)
    if not path.exists():
        report["merknader"].append(f"printere: {store_id}: finner ikke {path.name}, hoppet over")
        return []
    out = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            name = re.sub(r"\s+", " ", html.unescape(r.get("Navn", ""))).strip()
            price = parse_price(r.get("Pris", ""))
            if not name or price is None:
                continue
            was = parse_price(r.get("Førpris", ""))
            out.append({"s": store_id, "name": name, "type": (r.get("Type") or "").strip(), "price": price,
                        "was": was if was and was > price else None, "avail": parse_stock(r.get("Lager", "")),
                        "url": (r.get("Lenke") or "").strip() or None, "img": (r.get("Bilde") or "").strip() or None})
    return out


def build_printers(stores, root, report):
    groups = {}
    per_store = {}
    for s in stores:
        pf = s.get("printers_file")
        if not pf:
            continue
        rows = read_file(Path(root) / pf, s["id"], report)
        per_store[s["id"]] = len(rows)
        for r in rows:
            brand = detect_brand(r["name"])
            key = (brand.lower(), model_key(r["name"], brand))
            g = groups.setdefault(key, {"b": brand, "n": display_name(r["name"], brand), "t": "", "i": None, "o": {}})
            if g["n"].isupper() or (g["n"] != fix_case(g["n"])):
                g["n"] = display_name(r["name"], brand)
            g["t"] = g["t"] or guess_type(r["name"], r["type"])
            g["i"] = g["i"] or r["img"]
            if r["s"] in g["o"] and g["o"][r["s"]]["p"] <= r["price"]:
                continue  # samme butikk to ganger: behold den billigste
            o = {"s": r["s"], "p": r["price"], "a": r["avail"], "u": r["url"]}
            if r["was"]:
                o["w"] = r["was"]
            if r["img"]:
                o["i"] = r["img"]
            g["o"][r["s"]] = o
    items = []
    for g in groups.values():
        offers = sorted(g["o"].values(), key=lambda o: o["p"])
        items.append({"n": g["n"], "b": g["b"], "t": g["t"], "i": g["i"] or next((o["i"] for o in offers if o.get("i")), None),
                      "o": offers})
    items.sort(key=lambda p: (p["b"].lower(), p["n"].lower()))
    report["printere"] = {"butikker": per_store, "produkter": len(items),
                          "i_flere_butikker": sum(len(p["o"]) > 1 for p in items)}
    return items
