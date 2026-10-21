> Dette er den flate versjonen: alle filer ligger i roten av repoet. Bare `.github/workflows/pages.yml` ligger i en mappe, fordi GitHub krever det.

# Filamentsøk.no på GitHub Pages

Prisoversikt for 3D-printer-filament i norske nettbutikker. Hele siden er statisk: en nettside (`index.html`) som leser `products.json`. `products.json` bygges av CSV-filene fra din egen scraper og malen `stores.json`.

```
 din scraper ─► *.csv ─┐
                            ├─► python build.py ─► dist/products.json + dist/index.html ─► GitHub Pages
 stores.json (malen) ┘        berik · samle på tvers av butikker
```

Ingen server, ingen database og ingen avhengigheter: byggingen bruker bare Python 3.9+ sin standardbibliotek.

## Sett opp GitHub Pages (én gang)

1. Legg innholdet i et GitHub-repo (grenen `main`).
2. Repo › Settings › Pages › Source: **GitHub Actions**.
3. Push. Jobben i `.github/workflows/pages.yml` kjører testene, bygger og publiserer. Adressen står i jobben og under Settings › Pages. Eget domene (filamentsøk.no) legger du til samme sted.

Jobben kjører når ``, `config/`, `src/` eller `` endres, og kan startes for hånd (Actions › Bygg og publiser › Run workflow).

## Slik oppdaterer du prisene

Alternativ A, du gjør det selv: bytt ut CSV-filene i `` med nye (samme filnavn og kolonner), oppdater `snapshot` i `stores.json` til datoen, og push.

Alternativ B, jeg gjør det: send CSV-filene til Claude. Claude fyller ut malen for filene (kolonner, standardvekt og så videre), kjører byggingen og leverer ferdig `products.json` og et repo klart til å pushe.

## Skjule og vise priser

Øverst i scriptet i `index.html` (ca. linje 223) står:

```js
var CONFIG={showPrices:true,hidePricesFor:[]};
```

- **Skjule alle priser:** sett `showPrices:false`. Prisene vises som «Se pris i butikken», og forsiden viser et notat om at priser ikke vises.
- **Skjule priser for noen butikker:** la `showPrices:true` stå og list butikk-id-ene (fra `stores.json`), for eksempel `hidePricesFor:['kjell','poly']`. Notatet får tillegget «Enkelte butikker vises uten pris.»
- **Vise priser igjen:** sett `showPrices:true` og tøm `hidePricesFor:[]`.

Trykk «Commit changes» i GitHub, så oppdateres siden etter et minutt eller to. Last siden på nytt med Ctrl+Shift+R hvis du ikke ser endringen.

## Malen: `stores.json`

`stores.template.json` er den tomme malen med forklaring til hvert felt. `stores.json` er den utfylte versjonen for filene i ``. Én blokk per butikk:

| Felt | Betydning |
|---|---|
| `id`, `name`, `home` | Kortnavn, visningsnavn og butikkens forside |
| `file`, `delimiter`, `encoding` | CSV-filen |
| `columns.url / name / price / stock / image / brand / color` | Kolonnenavn i CSV-filen. `name` kan være en liste (slås sammen med mellomrom), for eksempel `["Navn", "Farge/type"]`. Tomt eller `null` betyr at filen ikke har den kolonnen |
| `columns.stock_fallback` | Kolonne som brukes når `stock` er tom |
| `default_kg` | Vekt som antas når den ikke står i navnet. Pakker, sett og bunter får aldri standardvekt |
| `default_kg_brands` | Standardvekt bare for noen merker, for eksempel `{"Bambu Lab": 1}` |
| `rolls_as_kg` | `true`: «(10 ruller)» betyr 10 kg |
| `brand_strip`, `default_brand`, `url_base` | Rydding av merkekolonne, reservemerke og relative lenker |

Feil i malen gir en tydelig melding med kolonnene filen faktisk har. Hjelpeverktøy: `python suggest_mapping.py *.csv` viser kolonnene og foreslår hva de er.

### Nåværende utfylling

| Butikk | Fil | Kolonner | Vekt som antas |
|---|---|---|---|
| Kjell & Company | `kjell.csv` | Lenke, navn, Pris, lager, Bilde | 1 kg |
| 3D Klubben | `3dklubben.csv` | Lenke, Navn, Pris, Lager | ingen |
| NorMax3D | `normax3d.csv` | Lenke, Navn, Pris, Lager | ingen |
| Stratum3D | `stratum3d.csv` | Navn, Pris, lager (ellers lagerbeholding), Bilde. Ingen lenke, så kortet viser «Link kommer» | ingen |
| Clas Ohlson | `clasohlson.csv` | `Bilde` (inneholder produktlenken), Navn + featureValue, Pris | ingen |
| Elefun | `elefun.csv` | Lenke, Navn, Pris, Lager, Bilde, Produsent | 1 kg for Bambu Lab-PLA/PETG/ABS/ASA |
| Polyalkemi | `polyalkemi.csv` | Lenke, Navn + Farge/type, pris, Lager, Bilde | 1 kg |

`3dklubben.csv` og `normax3d.csv` er lagd fra utvalget som lå på siden fra før. Bytt dem ut med egen scraping når du har den.

## Hva byggingen gjør

1. Leser hver CSV etter malen: pris (`299,90`, `499,-`, `kr 9.999,-`, `1 590,00 kr`), lager (`Utsolgt`, `25+ på lager`, `10-25`, `27`, `Snart tilgjengelig`) og vekt.
2. Beriker hvert produkt ut fra navnet (`src/enrich.py`): merke, materiale (49 kategorier, fra ABS og PLA til PEEK og PVDF), finish (silk, matt, glitter og så videre), farge, tilsetning (karbon, glassfiber, ESD, flammehemmende, lettvekt, antibakteriell) og vekt.
3. Samler samme produkt på tvers av butikker (`src/grouping.py`) til ett kort med én linje per butikk. To tilbud er samme produkt når merke, materiale, tilsetning, vekt og navnet (uten merke, vekt og fyllord) er likt. Norske og engelske grunnfarger regnes som like, nyanser holdes adskilt. Produkter uten kjent vekt slås aldri sammen.
4. Skriver `dist/products.json` (kompakt, ca. 1,2 MB, ca. 160 kB over nettet med gzip som Pages bruker), kopierer nettsiden og legger inn en byggnøkkel i adressen til `products.json` slik at nettlesere aldri viser gammel data.
5. Skriver en rapport (antall per butikk, mangler pris, vekt, farge, materiale, lenke) til loggen og til jobbsammendraget. `--strict` i Actions stopper publiseringen hvis en butikk mangler data helt eller over 25 % av radene mangler pris.

## products.json

```json
{"v":1,"snapshot":"19. oktober 2026",
 "stores":{"elefun":{"n":"Elefun","home":"https://www.elefun.no/"}},
 "products":[{"id":"p0","brand":"Bambu Lab","name":"Bambu Lab ABS 1kg - Olive","mat":"ABS","fin":"Standard","col":"Grønn","kg":1,
   "offers":[{"s":"elefun","p":339,"u":"https://…","a":"10-25","i":"https://…jpg"},
             {"s":"poly","p":339,"u":"https://…","a":"16","n":"Bambu Lab ABS Olive"}]}]}
```

`add` (tilsetning) og `kg` utelates når de er ukjente. Tilbudene er sortert billigste først. `a`: `out`, `order` (utsolgt, kan bestilles), `soon:<dato>`, `yes`, eller antall som tekst. `n` finnes bare når butikkens navn avviker fra kortets navn.

## Utvikling

```bash
python -m pytest            # tester (pip install pytest)
python build.py         # bygger dist/
cd dist && python -m http.server 8000   # se resultatet på http://localhost:8000
```

## Kjente begrensninger

- Produktbildene lastes direkte fra butikkenes servere (godkjent av butikkene) med `loading="lazy"` og uten referer. Hvis en butikk blokkerer lasting fra andre nettsteder eller flytter bildene, vises den tegnede spolen i stedet. Bildelenkene kommer fra kolonnen `image` i malen.
- Priser og lager er et øyeblikksbilde fra datoen i `snapshot`. Nettsiden sier det.
- Stratum3D mangler produktlenke i filen. Legg til en lenkekolonne i scraperen, og sett `"url"` i malen.
- Materiale, farge og merke leses fra navnet. Se rapporten for rader som ikke ble gjenkjent, og utvid listene i `src/enrich.py` ved behov.

## Guide til filament (`/guide/`)

Guiden er én side med datakort, bygget fra masterdatabladet i Excel.

- Arket ligger i `guide/master.xlsx`. Det er kilden for alle verdier i guiden.
- Siden leser `guide.json`, som lages av arket. Når du har endret arket, kjører du på din egen maskin:
  ```
  pip install openpyxl
  python xlsx_to_guide.py
  ```
  og committer `master.xlsx` og `guide.json` sammen. GitHub bygger siden på nytt av seg selv.
- Arket er på engelsk. Oversettelsene ligger i `guide_no.py`. Hvis du legger til nye verdier eller materialer i arket, stopper skriptet og sier hva som mangler oversettelse for.
- Søket i guiden filtrerer mens du skriver. Teksten må starte forkortelsen eller det tekniske navnet (P viser PLA og PETG, PL viser bare PLA og PLA+ / Pro).
- Materialer på nettsiden som mangler i arket (nå: PSU) får ikke datakort. Skriptet skriver ut hvilke det gjelder.
- De seks kolonnene Beginner Friendly, Outdoor, Mechanical Parts, High Temp, Support Material og Post-Process / Special vises ikke, fordi verdiene i arket ser feil ut (for eksempel Outdoor = Yes for PVA og Beginner Friendly = No for PLA).

### Filter og forslag i guiden

Knappen «Finn riktig filament» åpner et filter med to temperatur-sliders (dyse og seng) og avkrysning for «skal ha» / «skal ikke ha». Listen oppdateres med en gang. Kriteriene er definert i `CG` i `index.html` og leser direkte fra `guide.json`. Materialer med manglende eller varierende data skjules som standard (og kan vises med et valg). Forslag er materialer som bryter høyst to av valgene, med begrunnelse hentet fra de samme dataene. Temperaturer finnes bare for materialene som har et oppgitt område i masterarket.
