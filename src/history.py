"""Prishistorikk: husker pris per tilbud mellom byggene og lager listen til siden /prisendringer/.

Historikken (`history.json`) ligger på den publiserte siden. Hvert bygg henter forrige versjon derfra, legger til
dagens priser og publiserer den nye. Hentes ikke forrige versjon (annet enn «finnes ikke»), stoppes bygget, så
historikken ikke går tapt. Tidspunkt lagres som minutter siden 1970 (heltall). Ren Python, ingen avhengigheter."""
import hashlib
import json
import urllib.error
import urllib.request

KEEP_DAYS = 45      # tilbud som ikke er sett på så lenge, glemmes
MAX_POINTS = 30     # antall prispunkter vi husker per tilbud (eldre punkter forsvinner først)
SHOW_DAYS = 90      # lengste periode siden viser (valgfritt fra–til-intervall kan gå så langt tilbake som historikken finnes)


def offer_key(store, url):
    return hashlib.sha1(f"{store}|{url}".encode("utf-8")).hexdigest()[:12]


def keyed(products):
    """(produkt, tilbud, nøkkel) for hvert tilbud med lenke og pris. Deler flere varianter samme lenke (f.eks. farger på én
    produktside), tas navnet med i nøkkelen, så variantene ikke blandes. Samme nøkkel brukes bare én gang per bygg."""
    count = {}
    for p in products:
        for off in p["offers"]:
            if off.get("u"):
                count[(off["s"], off["u"])] = count.get((off["s"], off["u"]), 0) + 1
    seen = set()
    for p in products:
        for off in p["offers"]:
            url = off.get("u")
            if not url:
                continue
            k = offer_key(off["s"], url if count[(off["s"], url)] == 1 else f"{url}|{off.get('n') or p['name']}")
            if k not in seen:
                seen.add(k)
                yield p, off, k


def empty():
    return {"v": 1, "since": None, "o": {}}


def load_previous(url, timeout=60):
    """Henter forrige historikk fra den publiserte siden. 404 (første gang) gir tom historikk, andre feil stopper bygget."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Filamentsok/1.0"}), timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return empty()
        raise SystemExit(f"Klarte ikke hente forrige historikk ({url}): HTTP {exc.code}. Bygget stoppes så historikken ikke går tapt.")
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Klarte ikke hente forrige historikk ({url}): {exc}. Bygget stoppes så historikken ikke går tapt.")
    if not isinstance(data, dict) or data.get("v") != 1 or not isinstance(data.get("o"), dict):
        raise SystemExit(f"Ugyldig historikkfil fra {url}. Bygget stoppes så historikken ikke går tapt.")
    return data


def update(hist, products, now):
    """Legger dagens priser inn i historikken (`now` = minutter siden 1970). Bare prisendringer gir et nytt punkt."""
    hist = hist or empty()
    o = hist.setdefault("o", {})
    hist["since"] = hist.get("since") or now
    for _p, off, k in keyed(products):
        price = off.get("p")
        if not price or price <= 0:
            continue
        rec = o.setdefault(k, {"s": off["s"], "h": []})
        rec["s"], rec["l"] = off["s"], now
        if not rec["h"] or rec["h"][-1][1] != price:
            rec["h"].append([now, price])
            rec["h"] = rec["h"][-MAX_POINTS:]
    for k in [k for k, r in o.items() if r.get("l", 0) < now - KEEP_DAYS * 1440]:
        del o[k]
    return hist


def changes(hist, products, now, days=SHOW_DAYS):
    """Produkter med minst én prisendring siste `days` dager, nyeste endring først. Hvert tilbud som har endret pris får hele
    historikken sin (`h`: [[tidspunkt, pris], ...], eldst først), så siden selv kan velge intervall og vise «Se historikk».
    Hver rad har også alle butikkene (for lenker)."""
    since = now - days * 1440
    keys = {id(off): k for _p, off, k in keyed(products)}
    out = []
    for p in products:
        ch, offers = [], []
        for off in p["offers"]:
            offers.append({"s": off["s"], "p": off.get("p"), "u": off.get("u"), "a": off.get("a")})
            rec = hist["o"].get(keys.get(id(off)))
            if rec and len(rec["h"]) >= 2 and rec["h"][-1][0] >= since:
                ch.append({"s": off["s"], "h": [list(pt) for pt in rec["h"]]})
        if ch:
            img = next((x.get("i") for x in p["offers"] if x.get("i")), "")
            out.append({"n": p["name"], "b": p.get("brand", ""), "c": p.get("col", ""), "m": p.get("mat", ""), "kg": p.get("kg"),
                        "i": img, "o": offers, "ch": sorted(ch, key=lambda c: -c["h"][-1][0])})
    out.sort(key=lambda it: -it["ch"][0]["h"][-1][0])
    return out


def page_json(hist, products, now, stores=None):
    return {"v": 1, "now": now, "since": hist.get("since"), "stores": stores or {}, "items": changes(hist, products, now)}
