"""Felles hjelp for 3D-printer-listene (data/printers_<butikk>.csv).

Hver butikk-feed (NorMax3D, Stratum3D, Materie X, Elefun) skriver i tillegg til filamentfilen en liste med 3D-printere.
Kolonner: Lenke,Bilde,Navn,Type,Pris,Førpris,Lager. Pris og førpris er hele kroner som tekst («5490» eller «5490,50»).
Type er «FDM» eller «Resin» når butikken oppgir det, ellers tom (byggingen gjetter ut fra navnet).
"""
import csv
import html
import re
from pathlib import Path

COLUMNS = ["Lenke", "Bilde", "Navn", "Type", "Pris", "Førpris", "Lager"]

# Tilbehør og deler som ligger i printerkategorier hos noen butikker (filamentsystemer, vaske- og herdestasjoner osv.).
ACCESSORY_RE = re.compile(
    r"\bCFS\b|\bAFU\b|\bMercury\b|\bACE\b.*\bfor\b|\b(dyse|nozzle|hotend|bygg?eplate|build ?plate|"
    r"reservedel|spare|oppgradering|upgrade kit|kabel|cable|vifte|fan|belt|rem)\b|\bwash\b|\bcure\b|\bfilament\b",
    re.I)


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def clean_name(text):
    """Rydder printernavn: HTML-tegn, tankestrek etter merkenavnet og dobbelt merkenavn («ELEGOO Elegoo Jupiter 2»)."""
    s = clean(text).replace("–", " ").replace("—", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(^|\s)(lagersalg|salg|tilbud|kampanje)\s*:\s*", r"\1", s, flags=re.I).strip()
    m = re.match(r"(\w[\w:+-]*)\s+\1\b", s, re.I)
    if m:
        s = s[len(m.group(1)) + 1:]
    s = re.sub(r"\s*\b3D[- ]?printer\b\s*", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def is_accessory(name):
    return bool(ACCESSORY_RE.search(name or ""))


def write(rows, dst):
    """Skriver listen. Tom liste skriver ingen fil (den gamle blir liggende) og gir 0."""
    seen, uniq = set(), []
    for r in rows:
        if not re.search(r"[1-9]", str(r[4])):  # pris 0 eller tom: ikke til salgs
            continue
        key = (r[0], r[2])
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    if not uniq:
        return 0
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(uniq)
    return len(uniq)


def path_for(filament_dst):
    """data/normax3d.csv -> data/printers_normax3d.csv"""
    p = Path(filament_dst)
    return p.with_name("printers_" + p.name)
