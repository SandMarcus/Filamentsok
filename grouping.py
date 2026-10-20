"""Samler samme produkt fra flere butikker. To tilbud er samme produkt når merke, materiale, tilsetning,
vekt og navnet (uten merke, vekt og fyllord, med norske og engelske grunnfarger likestilt) er likt."""
import collections
import re

from .enrich import BRANDS, COLORS, FINISHES, _tokens

_BASE_COLORS = {
    "svart": "svart black", "hvit": "hvit white", "grå": "grå grey gray", "rød": "rød red", "blå": "blå blue",
    "grønn": "grønn green", "gul": "gul yellow", "oransje": "oransje orange", "lilla": "lilla purple",
    "rosa": "rosa pink", "gull": "gull gold", "sølv": "sølv silver", "brun": "brun brown", "turkis": "turkis turquoise",
    "natur": "natur natural naturell", "klar": "transparent gjennomsiktig clear",
}
CMAP = {w: canon for canon, words in _BASE_COLORS.items() for w in words.split()}
FMAP = {}
for _canon, _kws in FINISHES:
    for _k in _kws:
        if " " not in _k and "-" not in _k:
            FMAP.setdefault(_k, _canon.lower())
FMAP["matte"] = "matt"
SYN = {"mørk": "dark", "lys": "light", "kald": "cold", "varm": "warm"}
STOP = {"filament", "filamenter", "3d", "skriver", "skrivere", "skriv", "printer", "printing", "for", "til", "og",
        "med", "mm", "kg", "g", "gr", "gram", "spole", "spool", "the", "av", "inkl", "with", "w", "e"}
BRANDTOK = {"add", "north", "bambu", "lab"}
for _aliases in BRANDS.values():
    for _a in _aliases:
        BRANDTOK.update(_tokens(_a))


def key(o):
    """Nøkkelen to tilbud må dele for å havne på samme kort. o er en dict med brand, mat, add, kg og name."""
    t = o["name"].lower()
    t = t.replace("e-pla", "epla").replace("e pla", "epla").replace("x-pla", "xpla").replace("x pla", "xpla")
    toks = []
    for w in _tokens(t):
        if w in STOP or w in BRANDTOK or w.isdigit() or re.fullmatch(r"\d+(kg|g|mm|gr)", w):
            continue
        if re.fullmatch(r"\d+[a-z]?", w) and len(w) <= 2:
            continue
        w = SYN.get(w, w)
        w = FMAP.get(w, CMAP.get(w, w))
        toks.append("pla" if w == "epla" else w)
    return (o["brand"], o["mat"], o["add"], o["kg"], tuple(sorted(set(toks))))


def group(offers):
    """offers: liste av dicts med store, price, brand, mat, add, kg, name. Returnerer liste av grupper (lister av tilbud).
    Bare tilbud med kjent vekt slås sammen. Fra samme butikk samles bare det billigste."""
    by = collections.defaultdict(list)
    singles = []
    for o in offers:
        if o["kg"] is None:
            singles.append([o])
        else:
            by[key(o)].append(o)
    groups = []
    for members in by.values():
        if len({m["store"] for m in members}) < 2:
            groups.extend([m] for m in members)
            continue
        members = sorted(members, key=lambda m: (m["price"] is None, m["price"] or 0))
        seen, g = set(), []
        for m in members:
            if m["store"] in seen:
                groups.append([m])
            else:
                seen.add(m["store"])
                g.append(m)
        groups.append(g)
    return groups + singles
