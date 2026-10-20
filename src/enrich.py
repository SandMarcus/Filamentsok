"""Berikelse: trekker ut merke, materiale, finish, farge, vekt og diameter fra produktnavn m.m.

Ren Python uten avhengigheter, slik at den kan testes uten RabbitMQ og database.
"""
import hashlib
import re
from dataclasses import dataclass
from typing import Optional

BRANDS = {
    "Addnorth": ["addnorth", "add:north", "add north"],
    "Bambu Lab": ["bambu lab", "bambulab", "bambu"],
    "Copymaster3D": ["copymaster3d", "copymaster"],
    "Creality": ["creality"],
    "Elegoo": ["elegoo"],
    "eSUN": ["esun"],
    "Sunlu": ["sunlu"],
    "Polymaker": ["polymaker"],
    "Prusament": ["prusament"],
    "Primaselect": ["primaselect"],
    "Primacreator": ["primacreator", "easyprint"],
    "Polyalkemi": ["polyalkemi"],
    "Azurefilm": ["azurefilm"],
    "Raise3D": ["raise3d"],
    "BASF Ultrafuse": ["ultrafuse", "basf"],
    "Fiberlogy": ["fiberlogy"],
    "Anycubic": ["anycubic"],
    "Overture": ["overture"],
    "Kingroon": ["kingroon"],
    "Flashforge": ["flashforge"],
    "3DXTech": ["3dxtech"],
    "FormFast": ["formfast", "form fast"],
    "Intam": ["intam"],
    "Essentium": ["essentium"],
    "Nile Polymers": ["nile polymers", "flourinar"],
    "Prusa": ["prusa"],
    "Spectrum": ["spectrum"],
    "Smartfil": ["smartfil"],
    "PolySmart": ["polysmart"],
    "FilamentPM": ["filamentpm"],
    "FormFutura": ["formfutura"],
    "Siraya Tech": ["siraya"],
    "Innovatefil": ["innovatefil"],
    "BIQU": ["biqu"],
    "Mingda": ["mingda"],
    "colorFabb": ["colorfabb"],
    "Fillamentum": ["fillamentum"],
}

# Rekkefølgen avgjør hva som vinner når flere finishtyper nevnes.
FINISHES = [
    ("Silk", ["silk", "silke"]),
    ("Matt", ["matt", "matte"]),
    ("Glitter", ["glitter", "glitz", "sparkle", "glitrende", "galaxy", "twinkling", "starlight"]),
    ("Metall", ["metal", "metallic", "metall"]),
    ("Tre", ["wood", "tre-filament"]),
    ("Stein", ["rock", "stein"]),
    ("Gjennomsiktig", ["translucent", "transculent"]),
    ("Fargeskift", ["chameleon", "fargeskift"]),
    ("Marmor", ["marble", "marmor"]),
    ("Selvlysende", ["selvlysende", "glow", "luminous"]),
    ("Glossy", ["glossy", "gloss", "blank"]),
]

# Flerfarget først, så de vanlige fargene. Nøkkelord på 3 tegn eller færre må være hele ord.
COLORS = [
    ("Flerfarget", ["multi", "rainbow", "regnbue", "dual color", "dual colour", "tricolor", "tri-color", "flerfarget",
                    "cmyk", "gradient", "4-farger", "4 x neon", "mix$"]),
    ("Turkis", ["turkis", "turquoise", "cyan", "teal", "aqua"]),
    ("Svart", ["svart", "black", "schwarz", "onyx"]),
    ("Hvit", ["hvit", "white", "kaldhvit"]),
    ("Grå", ["grå", "grey", "gray", "graphite", "antrasitt", "anthracite", "charcoal", "granite", "antracite", "concrete"]),
    ("Rød", ["rød", "red", "bordeaux", "burgundy", "maroon", "scarlet"]),
    ("Blå", ["blå", "blue", "navy", "sapphire", "safir"]),
    ("Grønn", ["grønn", "green", "lime", "olive", "oliven", "mint", "jade", "sage"]),
    ("Gul", ["gul", "yellow"]),
    ("Oransje", ["oransje", "orange", "tangerine", "apricot", "blaze"]),
    ("Lilla", ["lilla", "lila", "purple", "violet", "lavender", "plum", "grape", "lilac", "peri"]),
    ("Rosa", ["rosa", "pink", "magenta", "rosy", "rose$", "coral", "blush"]),
    ("Gull", ["gull", "gold", "brass"]),
    ("Sølv", ["sølv", "silver", "inox", "aluminium", "aluminum"]),
    ("Brun", ["brun", "brown", "copper", "kobber", "bronze", "caramel", "terracotta", "chocolate", "cocoa", "khaki", "tan", "rosewood", "cappuccino", "espresso", "cork", "eik", "oak", "clay", "mocha", "walnut"]),
    ("Beige", ["beige", "champagne", "flesh", "sandstone", "creamstone", "cream", "skin", "latte", "macchiato", "birch"]),
    ("Naturell", ["natur", "natural", "naturel", "naturlig", "naturell"]),
    ("Gjennomsiktig", ["gjennomsiktig", "transparent", "clear"]),
]
SHORT_NO = {"blå", "grå", "rød", "gul"}  # også treff i sammensetninger: lysegrå, mørkerød

COLOR_MODIFIERS = {
    "dark", "light", "medium", "army", "baby", "sea", "deep", "bright", "pastel", "neon",
    "paper", "cool", "warm", "jungle", "flame", "pistachio", "princess", "gleam", "aurora", "natural",
    "amber", "18k", "mørk", "lys", "kald", "varm", "bambu",
}

STOPWORDS = {
    "filament", "filamenter", "3d", "skriver", "skrivere", "skriv", "printer", "printing", "for", "til",
    "og", "med", "mm", "kg", "g", "universal", "premium", "basic", "pro", "plus", "kg", "gram",
    "spole", "spool", "the", "av",
}

# Ord som viser at det ikke er filament
REJECT = ("holder", "dyse", "nozzle", "hotend", "resin", "harpiks", "3d-penn", "3doodler", "cleaning", "rense")

ADDITIVES = [
    ("Karbon", ["carbon", "karbon", "cf"]),
    ("Glassfiber", ["glass", "glassfiber", "glassfibre", "gf"]),
    ("ESD", ["esd"]),
    ("Flammehemmende", ["fr", "flameretardant", "flammehemmende", "v0"]),
    ("Lettvekt", ["lw", "lightweight", "foam", "foaming"]),
    ("Antibakteriell", ["antibacterial", "antibakteriell"]),
]


@dataclass
class Enriched:
    is_filament: bool
    brand: Optional[str]
    material: Optional[str]
    additive: Optional[str]
    finish: str
    color: Optional[str]
    weight_kg: Optional[float]
    diameter_mm: Optional[float]
    line: str

    @property
    def key(self) -> str:
        parts = [
            self.brand or "", self.material or "", self.additive or "", self.finish,
            self.color or "", f"{self.weight_kg or ''}", f"{self.diameter_mm or ''}", self.line,
        ]
        return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()

    @property
    def ui_material(self) -> str:
        """Gruppen nettsiden filtrerer på: selve polymeren. Tilsetning er et eget filter."""
        return self.material or "Annet"


def _tokens(text: str):
    return re.findall(r"[a-zæøå0-9]+", text.lower())


def _has_kw(kw: str, text: str, tokens: list) -> bool:
    if kw.endswith("$"):
        return kw[:-1] in tokens
    if " " in kw or "-" in kw:
        return re.search(rf"(?<![a-zæøå]){re.escape(kw)}(?![a-zæøå])", text) is not None
    if kw in SHORT_NO:
        return any(t == kw or t.endswith(kw) for t in tokens)
    if len(kw) <= 3:
        return kw in tokens
    return kw in text


def detect_brand(text: str, hint: Optional[str]) -> Optional[str]:
    for source in (text, (hint or "").lower()):
        for canon, aliases in BRANDS.items():
            for a in aliases:
                if re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", source):
                    return canon
    return None


def detect_material(text: str, tokens: list) -> Optional[str]:
    """Polymeren produktet er laget av. Rekkefølgen betyr noe: mer spesifikke først.

    Returnerer en av kategoriene nettsiden bruker (MATERIALS under), ellers None."""
    T = set(tokens)

    def rx(p):
        return re.search(p, text) is not None

    W = r"(?<![a-z0-9])"  # ordgrense foran
    if "support" in T or rx(r"supp+ort"):
        return "Support"
    # Høytemperatur og tekniske
    if rx(W + r"peek"):
        return "PEEK"
    if rx(W + r"pekk"):
        return "PEKK"
    if rx(W + r"(pei|ultem)(?![a-z])"):
        return "PEI"
    if rx(W + r"ppsu(?![a-z])"):
        return "PPSU"
    if rx(W + r"pps(?![a-z])"):
        return "PPS"
    if rx(W + r"psu(?![a-z])"):
        return "PSU"
    if rx(W + r"ppa(?![a-z])"):
        return "PPA"
    if rx(W + r"pvdf"):
        return "PVDF"
    # Blandinger før enkeltmaterialene
    if rx(W + r"pc[- /]?abs"):
        return "PC-ABS"
    if rx(W + r"pc[- /]?pbt"):
        return "PC-PBT"
    if rx(W + r"pbt(?![a-z])"):
        return "PBT"
    if rx(W + r"(pctg|ptcg)"):
        return "PCTG"
    if rx(W + r"pipg"):
        return "PIPG"
    # Nylon
    if rx(W + r"e?paht"):
        return "PAHT"
    if rx(W + r"(co-?pa|copa)(?![a-z])"):
        return "CoPA"
    if rx(W + r"e?pa612"):
        return "PA612"
    if rx(W + r"e?pa-?6(?![0-9])") :
        return "PA6"
    if rx(W + r"e?pa-?12"):
        return "PA12"
    if rx(r"nylon") or rx(W + r"(e?pa\d+|pa|htpa)(?![a-z])") or rx(r"htpa"):
        return "PA"
    # Polyester
    if rx(r"pet-?g(\+| plus)"):
        return "PETG+"
    if rx(r"pet-?g"):
        return "PETG"
    if rx(W + r"(r?pet|ecopet)(?![a-z])") or rx(r"ecopet"):
        return "PET"
    # Elastomerer
    if rx(W + r"peba"):
        return "PEBA"
    if rx(r"tpu") or rx(r"flex"):
        return "TPU"
    if rx(W + r"tpe(?![a-z])"):
        return "TPE"
    if rx(W + r"tpr(?![a-z])"):
        return "TPR"
    # PLA-familien
    if rx(W + r"ht-?pla"):
        return "HT-PLA"
    if rx(W + r"apla(?![a-z])"):
        return "APLA"
    if rx(W + r"e?pla ?\+") or rx(W + r"e?pla (plus|pro)(?![a-z])") or rx(r"pla\+"):
        return "PLA+"
    if rx(r"(?<![a-z])e?pla(?![a-z])"):
        return "PLA"
    if rx(W + r"(all)?pha(?![a-z])"):
        return "PHA"
    # ABS/ASA-familien
    if rx(W + r"asa ?(\+|plus)"):
        return "ASA+"
    if "asa" in T or "lw-asa" in text:
        return "ASA"
    if "mabs" in T:
        return "MABS"
    if rx(W + r"abs ?(\+|plus|pro)(?![a-z])"):
        return "ABS+"
    if "abs" in T:
        return "ABS"
    if rx(W + r"san(?![a-z])"):
        return "SAN"
    if rx(W + r"sbs(?![a-z])"):
        return "SBS"
    if "pc" in T or rx(r"polycarbonate"):
        return "PC"
    if rx(W + r"pp(?![a-z])") or rx(r"polypropylen"):
        return "PP"
    if rx(W + r"pe(?![a-z])"):
        return "PE"
    if rx(W + r"pcl(?![a-z])"):
        return "PCL"
    if rx(W + r"pmma"):
        return "PMMA"
    if rx(W + r"pvb(?![a-z])"):
        return "PVB"
    if rx(W + r"smp(?![a-z])"):
        return "SMP"
    if "pva" in T:
        return "PVA"
    if "bvoh" in T:
        return "BVOH"
    if "hips" in T:
        return "HIPS"
    if "cpe" in T or "cope" in T:
        return "CPE"
    # Produktlinjer som ikke nevner polymeren i navnet.
    if rx(r"cospla|polyterra|woodfill|fiberwood|stonefil|smartfil e\.p|(?<![a-z])silk(?![a-z])|(?<![a-z])wood(?![a-z])"):
        return "PLA"
    return None


MATERIALS = [
    "ABS", "ABS+", "APLA", "ASA", "ASA+", "BVOH", "CoPA", "CPE", "HIPS", "HT-PLA", "MABS", "PA6", "PA12",
    "PA612", "PA", "PAHT", "PBT", "PC", "PC-ABS", "PC-PBT", "PCL", "PCTG", "PE", "PEBA", "PEEK", "PEI",
    "PEKK", "PET", "PETG", "PETG+", "PHA", "PIPG", "PLA", "PLA+", "PMMA", "PP", "PPA", "PPS", "PPSU", "PSU",
    "PVA", "PVB", "PVDF", "SAN", "SBS", "SMP", "TPE", "TPR", "TPU", "Support",
]


def detect_finish(text: str, tokens: list) -> str:
    for canon, kws in FINISHES:
        if any(_has_kw(k, text, tokens) for k in kws):
            return canon
    return "Standard"


def detect_color(text: str, tokens: list, extra: Optional[str] = None) -> Optional[str]:
    # Fargen kan stå i et eget felt (f.eks. variantvalg). Søk der først.
    for hay_text in ([extra.lower()] if extra else []) + [text]:
        hay_tokens = _tokens(hay_text)
        for canon, kws in COLORS:
            if any(_has_kw(k, hay_text, hay_tokens) for k in kws):
                return canon
    return None


def _tok_match(k: str, t: str) -> bool:
    if len(k) <= 3:
        return t == k or re.fullmatch(rf"{re.escape(k)}\d+", t) is not None
    return k in t


def detect_additive(tokens: list) -> Optional[str]:
    for canon, kws in ADDITIVES:
        if any(_tok_match(k, t) for k in kws for t in tokens):
            return canon
    return None


_WEIGHT_RE = re.compile(r"(\d{1,3}(?:[  ]\d{3})+|\d+(?:[.,]\d+)?)\s*-?\s*(kg|g)\b", re.I)
_DIAM_RE = re.compile(r"(1[.,]75|2[.,]85|3[.,]0{1,2})\s*mm", re.I)


_PACK_RE = re.compile(r"(\d+)\s*x\s*(\d+(?:[.,]\d+)?)\s*(kg|g)\b", re.I)


def parse_weight(text: str) -> Optional[float]:
    pm = _PACK_RE.search(text)
    if pm:
        each = float(pm.group(2).replace(",", "."))
        each = each / 1000 if pm.group(3).lower() == "g" else each
        return round(int(pm.group(1)) * each, 3)
    best = None
    for num, unit in _WEIGHT_RE.findall(text):
        value = float(re.sub(r"[  ]", "", num).replace(",", "."))
        kg = value / 1000 if unit.lower() == "g" else value
        if 0.05 <= kg <= 10:
            best = round(kg, 3)
            break
    if best is None:
        # «CF20 500g»: mellomrommet er ikke tusenskille
        for num, unit in re.findall(r"(\d+(?:[.,]\d+)?)\s*-?\s*(kg|g)\b", text, re.I):
            value = float(num.replace(",", "."))
            kg = value / 1000 if unit.lower() == "g" else value
            if 0.05 <= kg <= 10:
                return round(kg, 3)
    return best


def parse_diameter(text: str) -> Optional[float]:
    m = _DIAM_RE.search(text)
    return round(float(m.group(1).replace(",", ".")), 2) if m else None


def _line(tokens: list, brand: Optional[str], material: Optional[str]) -> str:
    drop = set(STOPWORDS) | COLOR_MODIFIERS
    for _, kws in COLORS + FINISHES:
        for k in kws:
            drop.update(_tokens(k))
    if brand:
        for a in BRANDS[brand]:
            drop.update(_tokens(a))
    if material:
        drop.add(material.lower())
    drop.update({"pla", "petg", "abs", "asa", "tpu", "pa", "pc", "pctg", "pet", "peek", "pp", "pva", "hips", "nylon", "pa6", "pa12", "pa612", "paht", "tpe", "tpr"})
    kept = []
    for t in tokens:
        if t in drop or t.isdigit() or re.fullmatch(r"\d+(kg|g|mm)", t) or re.fullmatch(r"\d{2,3}a", t):
            continue
        kept.append(t)
    return " ".join(sorted(set(kept)))


def enrich(name: str, brand_hint: Optional[str] = None, description: Optional[str] = None,
           color_hint: Optional[str] = None) -> Enriched:
    text = (name or "").lower().replace(" ", " ")
    tokens = _tokens(text)

    brand = detect_brand(text, brand_hint)
    material = detect_material(text, tokens)
    weight = parse_weight(name or "")
    stated_diameter = parse_diameter(name or "")
    # Nesten alt hjemmeprinterfilament er 1,75 mm. 2,85 mm står alltid oppgitt i navnet.
    diameter = stated_diameter or 1.75
    mentions_filament = "filament" in text

    is_filament = (
        not any(r in text for r in REJECT)
        and (material is not None or (mentions_filament and (weight or stated_diameter)))
        and (weight is not None or stated_diameter is not None or mentions_filament or material is not None)
    )
    if material in ("PA", "PC", "PP", "PET", "PSU", "PEI", "PE", "SAN", "SBS", "SMP", "PCL") and not (mentions_filament or weight or stated_diameter):
        is_filament = False

    return Enriched(
        is_filament=bool(is_filament),
        brand=brand,
        material=material,
        additive=detect_additive(tokens),
        finish=detect_finish(text, tokens),
        color=detect_color(text, tokens, color_hint),
        weight_kg=weight,
        diameter_mm=diameter,
        line=_line(tokens, brand, material),
    )
