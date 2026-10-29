"""Gjør Elefuns Google Shopping-feed (Feed_Pricespy_NO.CSV) om til data/elefun.csv.

Bruk:
    python tools/elefun_feed.py <feed.csv> [data/elefun.csv]

Feeden har hele nettbutikken (flere tusen varer). Bare rader med product_type som starter på
«3dprint > Filament > Filament 1.75mm» beholdes (2,85 mm-filament, som Ultimaker, tas ikke med, siden
siden ikke skiller på diameter). Utdata har kolonnene Bilde,Lenke,Navn,Produsent,Pris,Lager,
slik malen i config/stores.json forventer. Produsent lar vi stå tom, den leses ut av navnet.
Ren Python, ingen avhengigheter.
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import printers_common as pc  # noqa: E402

STOCK = {"in_stock": "På lager", "out_of_stock": "Utsolgt", "preorder": "Utsolgt, men kan bestilles",
         "backorder": "Utsolgt, men kan bestilles"}


PRINTER_SKIP = re.compile(r"tilbeh|filament|resin|deler|dyse|nozzle|verktøy|kabinett|skriver", re.I)


def is_printer_type(product_type):
    """«3dprint > <gruppe> > ...» der gruppen inneholder «printer» (for eksempel «3D-printere»), men ikke tilbehør."""
    parts = [s.strip() for s in (product_type or "").split(">")]
    return len(parts) >= 2 and parts[0].lower() == "3dprint" and "printer" in parts[1].lower() and not PRINTER_SKIP.search(parts[1])


def printer_rows(rows):
    out, seen = [], set()
    for r in rows:
        if not is_printer_type(r["product_type"]) or r["link"] in seen:
            continue
        m = re.search(r"\d+(?:[.,]\d+)?", (r["price"] or "").replace(" ", ""))
        name = pc.clean_name(r["title"])
        if not m or pc.is_accessory(name):
            continue
        seen.add(r["link"])
        v = float(m.group(0).replace(",", "."))
        price = ("%d" % v) if v == int(v) else ("%.2f" % v).replace(".", ",")
        out.append([r["link"], r["image_link"], name, "", price, "", STOCK.get((r["availability"] or "").strip(), "")])
    return out


def convert(src, dst):
    with open(src, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    need = {"title", "link", "availability", "price", "image_link", "product_type"}
    if not rows or not need <= set(rows[0]):
        raise SystemExit("Feeden mangler kolonner: " + ", ".join(sorted(need - set(rows[0] if rows else []))))
    out, seen = [], set()
    for r in rows:
        if not r["product_type"].lower().startswith("3dprint > filament > filament 1.75mm"):
            continue
        m = re.search(r"\d+(?:[.,]\d+)?", r["price"] or "")
        if not m or r["link"] in seen:
            continue
        seen.add(r["link"])
        price = float(m.group(0).replace(",", "."))
        out.append([r["image_link"], r["link"], r["title"].strip(), "",
                    "kr %s,-" % (int(price) if price == int(price) else str(price).replace(".", ",")),
                    STOCK.get((r["availability"] or "").strip(), "")])
    n_pr = pc.write(printer_rows(rows), pc.path_for(dst))
    print(f"{n_pr} printere skrevet til {pc.path_for(dst)}")
    if not out:
        raise SystemExit("Fant ingen filamentrader i feeden. Filen ble ikke skrevet.")
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Bilde", "Lenke", "Navn", "Produsent", "Pris", "Lager"])
        w.writerows(out)
    return len(out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    n = convert(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "data/elefun.csv")
    print(f"{n} filamentrader skrevet")
