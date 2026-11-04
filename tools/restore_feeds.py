"""Henter forrige publiserte butikkfiler tilbake før et nytt bygg, så butikker som ikke hentes på nytt (valgt bort eller feilet)
beholder prisene fra siste publiserte versjon i stedet for den eldre filen som ligger i repoet.

Hvert bygg publiserer CSV-filene det brukte under `<adresse>/feeds/`. Bruk:
    python tools/restore_feeds.py elefun nm3d stratum ...      # butikk-id-er fra config/stores.json

Filen overskrives bare når den nedlastede er gyldig (samme overskrift som filen i repoet og minst én rad). 404 (første gang),
nettfeil eller en ugyldig fil gir en advarsel og lar filen i repoet ligge. Steget stopper aldri bygget. Ren Python."""
import csv
import io
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Filamentsok/1.0 (prissammenligning; +https://xn--filamentsk-8cb.no)"


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def header_and_rows(data):
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    return (rows[0] if rows else []), max(len(rows) - 1, 0)


def restore(ids, root=ROOT, fetch_fn=fetch):
    """Returnerer {id: 'hentet' | 'beholdt: grunn'}."""
    root = Path(root)
    site = json.loads((root / "config" / "site.json").read_text(encoding="utf-8"))["url"].rstrip("/")
    files = {s["id"]: root / s["file"] for s in json.loads((root / "config" / "stores.json").read_text(encoding="utf-8"))["stores"]}
    out = {}
    for sid in ids:
        dst = files.get(sid)
        if dst is None:
            out[sid] = "beholdt: ukjent butikk"
            continue
        try:
            data = fetch_fn(f"{site}/feeds/{dst.name}")
            head, n = header_and_rows(data)
        except Exception as exc:  # noqa: BLE001
            out[sid] = f"beholdt: {exc}"
            continue
        if n < 1:
            out[sid] = "beholdt: tom fil"
        elif dst.exists() and head != header_and_rows(dst.read_bytes())[0]:
            out[sid] = "beholdt: annen overskrift"
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            out[sid] = f"hentet ({n} rader)"
    return out


def main(argv):
    for sid, status in restore(argv).items():
        print(f"{sid}: {status}")


if __name__ == "__main__":
    main(sys.argv[1:])
