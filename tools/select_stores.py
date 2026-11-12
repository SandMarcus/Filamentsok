"""Velger hvilke butikker som hentes på nytt i bygget «Bygg og publiser», og hvilke som får forrige publiserte priser tilbake.

Regler:
  - Nattlig kjøring (schedule): alle butikkene hentes, også Polyalkemi.
  - Manuell start (workflow_dispatch): bare butikkene du har krysset av («Hent … på nytt»).
  - Push til main: bare butikkene som er påvirket av endringen, altså de der `tools/<butikk>_feed.py` er endret. Endres
    `tools/nm3d_feed.py`, tas også Stratum3D, 3D Kongen og 3DFixit med, siden de bruker den. Polyalkemi (opptil 40 minutter) tas med
    bare når selve verktøyet er endret. Kan ikke endringen leses, eller er det første bygget uten publiserte butikkfiler
    (`/feeds/`), hentes alle unntatt Polyalkemi, så ingen sitter igjen med gamle priser.
  - Butikker som ikke hentes (eller der hentingen feiler) får siste publiserte butikkfil tilbake (tools/restore_feeds.py).
    Unntak: er butikkens egen fil i `data/` endret i denne pushen, brukes den filen, så en manuell oppdatering ikke overskrives.

Bruk (fra arbeidsflyten):
    python tools/select_stores.py [--changed fil.txt]
Leser EVENT_NAME og INPUTS_JSON fra miljøet, skriver `fetch` og `restore` til $GITHUB_OUTPUT. Ren Python."""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# id i config/stores.json -> valg ved manuell start, og verktøyfilene som gjør at butikken må hentes på nytt ved push
STORES = {
    "elefun": {"input": "hent_elefun", "tools": ["tools/elefun_feed.py"]},
    "nm3d": {"input": "hent_normax3d", "tools": ["tools/nm3d_feed.py"]},
    "stratum": {"input": "hent_stratum3d", "tools": ["tools/stratum_feed.py", "tools/nm3d_feed.py"]},
    "materiex": {"input": "hent_materiex", "tools": ["tools/materiex_feed.py"]},
    "multicom": {"input": "hent_multicom", "tools": ["tools/multicom_feed.py"]},
    "tonerweb": {"input": "hent_tonerweb", "tools": ["tools/tonerweb_feed.py"]},
    "filamentfabrikken": {"input": "hent_filamentfabrikken", "tools": ["tools/filamentfabrikken_feed.py"]},
    "dkongen": {"input": "hent_dkongen", "tools": ["tools/dkongen_feed.py", "tools/nm3d_feed.py"]},
    "fjord3d": {"input": "hent_fjord3d", "tools": ["tools/fjord3d_feed.py"]},
    "fixit": {"input": "hent_3dfixit", "tools": ["tools/fixit_feed.py", "tools/nm3d_feed.py"]},
    "poly": {"input": "hent_polyalkemi", "tools": ["tools/polyalkemi_feed.py"]},
}
SLOW = {"poly"}  # tar opptil 40 minutter, hentes ikke «for sikkerhets skyld»
ORDER = list(STORES)


def truthy(v):
    return v is True or str(v).strip().lower() == "true"


def data_files(root=ROOT):
    """{butikk-id: 'data/xxx.csv'} fra config/stores.json."""
    cfg = json.loads((Path(root) / "config" / "stores.json").read_text(encoding="utf-8"))
    return {s["id"]: s["file"] for s in cfg["stores"]}


def select(event, inputs=None, changed=None, feeds_published=True, files=None):
    """Returnerer (hent, gjenopprett): to lister med butikk-id-er.
    changed: liste med endrede filer ved push, eller None når det ikke lot seg lese."""
    inputs = inputs or {}
    files = files or {}
    if event == "schedule":
        return list(ORDER), list(ORDER)
    if event == "workflow_dispatch":
        fetch = [i for i in ORDER if truthy(inputs.get(STORES[i]["input"]))]
        return fetch, [i for i in ORDER]
    # push (og alt annet): bare det endringen påvirker
    if changed is None or not feeds_published:
        fetch = [i for i in ORDER if i not in SLOW]
    else:
        ch = set(changed)
        fetch = [i for i in ORDER if ch & set(STORES[i]["tools"])]
    # En butikkfil som er endret for hånd i denne pushen skal ikke skrives over av forrige publiserte versjon
    ch = set(changed or [])
    restore = [i for i in ORDER if files.get(i) not in ch]
    return fetch, restore


def feeds_published(site, probe="elefun", fetch_fn=None):
    """True hvis forrige bygg har publisert butikkfiler under /feeds/ (ellers er dette det første bygget)."""
    try:
        name = Path(data_files()[probe]).name
        url = f"{site.rstrip('/')}/feeds/{name}"
        if fetch_fn:
            return bool(fetch_fn(url))
        req = urllib.request.Request(url, headers={"User-Agent": "Filamentsok/1.0 (bygg)"}, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def parse_inputs(text):
    try:
        d = json.loads(text or "{}")
    except ValueError:
        return {}
    return d if isinstance(d, dict) else {}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed", help="fil med endrede filer, én per linje (utelates når de ikke kunne leses)")
    a = ap.parse_args(argv)
    event = os.environ.get("EVENT_NAME", "push")
    inputs = parse_inputs(os.environ.get("INPUTS_JSON"))
    changed = None
    if a.changed and Path(a.changed).exists():
        changed = [ln.strip() for ln in Path(a.changed).read_text(encoding="utf-8").splitlines() if ln.strip()]
    site = json.loads((ROOT / "config" / "site.json").read_text(encoding="utf-8"))["url"]
    pub = feeds_published(site) if event not in ("schedule", "workflow_dispatch") else True
    fetch, restore = select(event, inputs, changed, pub, data_files())

    lines = [f"Hendelse: {event}",
             f"Hentes på nytt: {', '.join(fetch) or 'ingen'}",
             f"Beholder siste publiserte priser: {', '.join(i for i in restore if i not in fetch) or 'ingen'}"]
    if event not in ("schedule", "workflow_dispatch"):
        if changed is None:
            lines.append("Kunne ikke lese endrede filer, så alle butikkene (unntatt Polyalkemi) hentes.")
        elif not pub:
            lines.append("Ingen publiserte butikkfiler ennå (første bygg), så alle butikkene (unntatt Polyalkemi) hentes.")
    print("\n".join(lines))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"fetch={' '.join(fetch)}\n")
            f.write(f"restore={' '.join(restore)}\n")
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write("### Butikker i dette bygget\n\n" + "\n".join(f"- {ln}" for ln in lines) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
