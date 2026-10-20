"""Tolking av celler i CSV-filene: pris, lager, vekt. Ren Python, ingen avhengigheter."""
import re

from .enrich import parse_weight


def parse_price(text):
    """«1 590,00 kr», «kr 9.999,-», «299,90», «499,-» -> flyttall. Tomt eller 0 -> None."""
    text = (text or "").replace("kr", "").replace("inkl. mva", "").strip()
    m = re.search(r"(\d[\d . ]*)(?:,(\d{1,2}))?", text)
    if not m:
        return None
    whole = re.sub(r"[ . ]", "", m.group(1))
    if not whole:
        return None
    value = float(whole + ("." + m.group(2) if m.group(2) else ""))
    return value if value > 0 else None


def parse_stock(text):
    """Returnerer None (ukjent) | 'out' | 'order' | 'soon:<dato>' | 'yes' | antall som tekst ('27', '25+', '10-25')."""
    s = (text or "").strip()
    if not s:
        return None
    low = s.lower()
    if low.startswith("utsolgt, men"):
        return "order"
    if low.startswith("utsolgt"):
        return "out"
    if low.startswith(("snart", "ubekreftet")):
        m = re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", s)
        return "soon:" + (m.group(0) if m else "")
    if low == "usikker":
        return None
    m = re.match(r"(\d+(?:-\d+)?\+?)(?:\s*(?:stk\.?|på lager))?$", low)
    if m:
        return m.group(1)
    m = re.match(r"(\d+\+?)\s+på lager", low)
    if m:
        return m.group(1)
    if low.startswith("på lager"):
        return "yes"
    return None


# Ord som viser at en rad er en pakke, et sett eller en bunt. Da gjetter vi aldri vekt.
PACK_WORDS = re.compile(r"bundle|\bset\b|pack|sample|\bkit\b|\btrial\b|\bbox\b|halloween|cmyk", re.I)
ROLLS = re.compile(r"(\d+)\s*(ruller|rull|rolls)", re.I)


def weight_kg(name, *, rolls_as_kg=False, default_kg=None, default_kg_brands=None, brand=None, material=None, additive=None):
    """Vekt i kg. Rekkefølge: oppgitt i navnet, «N ruller» (1 kg per rull), standardvekt fra malen."""
    kg = parse_weight(re.sub(r"(\d)\s*gr\b", r"\1 g", name))
    if kg is not None:
        return kg
    if rolls_as_kg:
        m = ROLLS.search(name)
        if m:
            return float(m.group(1))
    if PACK_WORDS.search(name):
        return None
    if default_kg:
        return float(default_kg)
    if default_kg_brands and brand in default_kg_brands and material in ("PLA", "PETG", "ABS", "ASA") \
            and not additive and not re.search(r"support", name, re.I):
        return float(default_kg_brands[brand])
    return None
