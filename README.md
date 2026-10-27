# Filamentsøk.no på GitHub Pages

Prisoversikt for 3D-printer-filament i norske nettbutikker. Hele siden er statisk: en nettside (`web/index.html`) som leser `products.json`. `products.json` bygges av CSV-filene fra din egen scraper og malen `config/stores.json`.

```
 din scraper ─► data/*.csv ─┐
                            ├─► python -m src.build ─► dist/products.json + dist/index.html ─► GitHub Pages
 config/stores.json (malen) ┘        berik · samle på tvers av butikker
```

Ingen server, ingen database og ingen avhengigheter: byggingen bruker bare Python 3.9+ sin standardbibliotek.

## Sett opp GitHub Pages (én gang)

1. Legg innholdet i et GitHub-repo (grenen `main`).
2. Repo › Settings › Pages › Source: **GitHub Actions**.
3. Push. Jobben i `.github/workflows/pages.yml` kjører testene, bygger og publiserer. Adressen står i jobben og under Settings › Pages. Eget domene (filamentsøk.no) legger du til samme sted.

Jobben kjører når `data/`, `config/`, `src/` eller `web/` endres, og kan startes for hånd (Actions › Bygg og publiser › Run workflow).

## Slik oppdaterer du prisene

Alternativ A, du gjør det selv: bytt ut CSV-filene i `data/` med nye (samme filnavn og kolonner), oppdater `snapshot` i `config/stores.json` til datoen, og push.

Alternativ B, jeg gjør det: send CSV-filene til Claude. Claude fyller ut malen for filene (kolonner, standardvekt og så videre), kjører byggingen og leverer ferdig `products.json` og et repo klart til å pushe.

## Elefun: automatisk henting fra feed

Elefun har en åpen prisfeed (Google Shopping-format): `https://www.elefun.no/dokumenter/pricefeed/Feed_Pricespy_NO.CSV`. Den har hele nettbutikken, så `tools/elefun_feed.py` plukker ut radene under «3dprint > Filament > Filament 1.75mm» og skriver `data/elefun.csv` i samme format som før. Filament med 2,85 mm (for eksempel Ultimaker) tas ikke med.

`pages.yml` laster ned feeden og kjører skriptet hver natt (kl. 04:00 UTC) og ved hver push. Feiler nedlastingen, brukes `data/elefun.csv` som ligger i repoet. Du kan kjøre det for hånd også:

```
python tools/elefun_feed.py Feed_Pricespy_NO.CSV data/elefun.csv
```

Feeden oppgir bare «på lager» eller «utsolgt», ikke antall. Datoen i `snapshot` i `config/stores.json` gjelder de andre butikkene og må fortsatt oppdateres for hånd.

## Mørkt og lyst tema

Alle sidene har en bryter (sol/måne) øverst til høyre. Siden følger først innstillingen i nettleseren eller systemet, og valget huskes i nettleseren (`localStorage`, nøkkelen `theme`). Fargene ligger som variabler øverst i hver HTML-fil.

## Søkeforslag

Når man skriver i søkefeltet på forsiden, vises forslag (farger, typer, materialer, merker, butikker og vanlige ord fra produktnavnene) med antall treff. Treffene tar hensyn til filtrene som allerede er valgt, slik at du bare får forslag som gir resultater. Klikker man i feltet igjen etter et søk, foreslås ord som snevrer inn søket. Søket matcher alle ordene i vilkårlig rekkefølge («pla svart»). Koden ligger under «Søkeforslag» i `web/index.html`.

Kjente ord i søket gjøres om til filtre: «pla matt» gir pillene Materiale: PLA og Type: Matt (farge, type, materiale, tilsetning, merke og butikk gjenkjennes, også flerords-navn som «Bambu Lab»). Ord som ikke er kjent, blir stående som fritekst («Søk: …»). Fjerner du et ord i søkefeltet og søker igjen, forsvinner filteret. Fjerner du en pille, forsvinner ordet fra søkefeltet. Et helt nytt søk uten felles ord med forrige søk nullstiller alle filtre. Koden ligger i `commit()` i `web/index.html`.

## Huskeliste

Hvert kort har et bokmerke øverst til høyre i bildet. Valgte filamenter lagres i nettleseren (`localStorage`, nøkkel `huskeliste`) og blir værende selv om filtrene endres. Første gang du legger til noe, dukker en boble med antall opp nede til høyre. Den følger med når man scroller. Trykk på den for å åpne listen (navn, materiale, farge og butikk), og minimer den med «–». Åpen eller lukket husker nettleseren. «Last ned PDF» lager en PDF direkte i nettleseren, uten eksterne biblioteker, med bilde, pris, pris per kg og lenke til hver butikk. Mange butikker blokkerer at andre sider leser bildene deres, så PDF-en prøver først bildet direkte og deretter via den åpne bildetjenesten images.weserv.nl (`PROXY` i koden). Lykkes ingen av delene, tegnes en spole i riktig farge i stedet. Huk av «Sammenlign» på 2–4 filamenter i listen og trykk «Sammenlign» for å se dem side om side (bilde, materiale, vekt, pris, kilopris og butikker). Beste pris og kilopris utheves. Priser vises bare hvis de ikke er skrudd av i `CONFIG`.

## Mobilmeny

På skjermer under 700 px samles menyen bak en hamburger-knapp øverst (på forsiden, guiden og partnersiden). «Om priser og lager» ligger nederst på forsiden, rett over bunnteksten. Første gang noen legger noe i huskelisten, vises en kort hjelpetekst over boblen. Den vises bare én gang per nettleser (`localStorage`-nøkkel `hk_tip`).

## Kolonner og listevisning

Over resultatene finnes en knappegruppe for visning: 1–4 kolonner og listevisning. På telefon (≤800 px) er 2 kolonner standard, med 1 og 2 som valg. På PC er valgene 2, 3 og 4 (uten valg brukes automatisk antall). Valget lagres i `localStorage` (`visning`), separat for telefon og PC. Koden ligger under «Visning» i `web/index.html`.

## Temaer (stiler)

Siden har flere valgbare stiler: Standard, Verksted, Glass, Rolig, 2005 og 1999. Velgeren (`web/themes.js`) ligger i hamburgermenyen på mobil og som palett-knapp ved siden av mørk/lys-bryteren på PC. Valget lagres i `localStorage` (`style`) og settes som `data-style` på `<html>`. Standard har ingen `data-style`. Alle stilene ligger i `web/themes.css`, hver under `html[data-style="navn"]`. Verksted, 2005 og 1999 er bare lyse, og da skjules mørk/lys-bryteren. Nytt tema: legg reglene i `themes.css`, legg navnet i `T`-listen i `themes.js` og i listen i hode-scriptet på hver side.

## Besøksstatistikk (valgfritt)

Siden kan telle besøk med GoatCounter (gratis, uten cookies, ingen samtykkebanner). Google-tjenester brukes ikke, for å slippe cookie-banner.

1. Opprett en konto på goatcounter.com og velg en kode, for eksempel `filamentsok`.
2. Sett GitHub-variabelen `GOATCOUNTER_CODE` til koden (Settings → Secrets and variables → Actions → Variables).
3. Start «Bygg og publiser» for hånd (Actions → Run workflow), eller vent på nattkjøringen.
4. Tallene ser du på `https://<kode>.goatcounter.com`.

Er koden tom (standard), settes ingenting inn. Lokalt kan du bruke en valgfri `config/analytics.json` med `{"goatcounter": "kode"}`. Plassholderne `<!--__ANALYTICS__-->` og `<!--__ANALYTICS_NOTE__-->` i sidene byttes ut av `src/build.py`.

## Funksjonssiden (`/funksjoner/`)

`web/funksjoner/index.html` viser alle funksjonene på siden, gruppert i kort. Ny funksjon: legg til et `<div class="card">` i riktig gruppe. `CLAUDE.md` ber Claude gjøre dette automatisk når en ny funksjon bygges.

## Støtt siden (Vipps)

Nederst på forsiden finnes en «Støtt med Vipps»-boks som er skjult til du fyller ut `SUPPORT` i `web/index.html` (rett under `CONFIG`):

```js
var SUPPORT={vippsNumber:'123 45 678',vippsLink:'',qrImage:''};
```

- `vippsNumber`: telefonnummer eller Vipps-nummer. Vises med en «Kopier»-knapp.
- `vippsLink`: lenke fra Vipps (for eksempel fra å dele din Vipps-QR). Gir knappen «Åpne i Vipps».
- `logo`: filnavn på den offisielle Vipps-logoen (last ned fra Vipps' designguide), for eksempel `vipps-logo.svg`. Legg filen i `web/`. Vises i knappene.
- `officialButton`: `true` (standard) viser Vipps' egen «Bidra med Vipps»-knapp i boksen nederst. Scriptet lastes fra `cdn.vippsmobilepay.com`. Feiler det, vises en vanlig knapp. Sett til `false` for å slå det av.
- `qrImage`: filnavn på et bilde av Vipps-QR-koden, for eksempel `vipps-qr.png`. Legg bildet i `web/` ved siden av `index.html`.

Fyll ut ett eller flere felt. Er alle tomme, vises ingenting.

## Skjule og vise priser

Øverst i scriptet i `web/index.html` (ca. linje 223) står:

```js
var CONFIG={showPrices:true,hidePricesFor:[]};
```

- **Skjule alle priser:** sett `showPrices:false`. Prisene vises som «Se pris i butikken», og forsiden viser et notat om at priser ikke vises.
- **Skjule priser for noen butikker:** la `showPrices:true` stå og list butikk-id-ene (fra `config/stores.json`), for eksempel `hidePricesFor:['kjell','poly']`. Notatet får tillegget «Enkelte butikker vises uten pris.»
- **Vise priser igjen:** sett `showPrices:true` og tøm `hidePricesFor:[]`.

Trykk «Commit changes» i GitHub, så oppdateres siden etter et minutt eller to. Last siden på nytt med Ctrl+Shift+R hvis du ikke ser endringen.

## Malen: `config/stores.json`

`config/stores.template.json` er den tomme malen med forklaring til hvert felt. `stores.json` er den utfylte versjonen for filene i `data/`. Én blokk per butikk:

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

Feil i malen gir en tydelig melding med kolonnene filen faktisk har. Hjelpeverktøy: `python tools/suggest_mapping.py data/*.csv` viser kolonnene og foreslår hva de er.

### Nåværende utfylling

| Butikk | Fil | Kolonner | Vekt som antas |
|---|---|---|---|
| Kjell & Company | `kjell.csv` | Lenke, Navn, Price, Bilde (ingen lagerkolonne) | 1 kg |
| 3D Klubben | `3dklubben.csv` | Lenke, Navn, Pris, Bilde | ingen |
| NorMax3D | `normax3d.csv` (lages av `tools/nm3d_feed.py`) | Lenke, Bilde, Navn, Farge, Pris, Førpris, Lager | ingen |
| Stratum3D | `stratum3d.csv` | Navn, Pris, lager, Bilde. Ingen lenke, så kortet viser «Link kommer» | ingen |
| Clas Ohlson | `clasohlson.csv` | `Bilde` (inneholder produktlenken), Navn + featureValue, Pris | ingen |
| Elefun | `elefun.csv` | Lenke, Navn, Pris, Lager, Bilde, Produsent | 1 kg for Bambu Lab-PLA/PETG/ABS/ASA |
| Polyalkemi | `polyalkemi.csv` | Lenke, Navn + Farge/type, pris, Lager, Bilde | 1 kg |

`3dklubben.csv` og `normax3d.csv` er lagd fra utvalget som lå på siden fra før. Bytt dem ut med egen scraping når du har den.

### NorMax3D (automatisk henting)

NorMax3D bruker WooCommerce, som har et åpent Store API (`https://nm3d.no/wp-json/wc/store/v1/products`). `tools/nm3d_feed.py` henter alle produkter, beholder filament (kategorien «Filament og Resin», uten harpiks) og skriver `data/normax3d.csv`. Hver farge eller vekt blir en egen rad med egen pris, lager og bilde. Er varen på tilbud, står vanlig pris i `Førpris`, og kortet viser tilbudsmerke og «før»-pris. Priser er inkl. mva. Vekt som bare står i etiketten (for eksempel «750g filament») legges til navnet.

`pages.yml` kjører skriptet hver natt og ved hver push. Feiler det, beholdes filen som ligger i repoet. Kjør det for hånd med `python tools/nm3d_feed.py data/normax3d.csv`. Har du en lagret JSON-side fra API-et, kan du teste uten nett: `python tools/nm3d_feed.py data/normax3d.csv --sample side.json` (da brukes prisen på hovedproduktet for alle varianter).

### Polyalkemi (automatisk henting)

Polyalkemi har ingen åpen feed, så `tools/polyalkemi_feed.py` leser de vanlige sidene som robots.txt tillater. Hovedsiden `/filament?pageID=110` (ca. 38 MB) gir alle varer med lager, bilde og lenke i ett kall. Mislykkes det, brukes kategorisidene `/filament/<materiale>?pageID=100`. Prisen fylles inn av JavaScript der, så den leses fra hver produktside (`data-priceincvat`), med ca. 0,6 sekunds pause. Rekker ikke skriptet alt innen tidsrammen (`--budget`, standard 40 minutter), eller feiler en side, brukes forrige pris fra `data/polyalkemi.csv`. Varer uten kjent pris tas ikke med.

`pages.yml` kjører dette bare nattlig og ved manuell start, ikke ved hver push, fordi det tar lang tid. Kjør for hånd: `python tools/polyalkemi_feed.py data/polyalkemi.csv`. Med `--no-price` oppdateres bare lager og nye varer, og prisene hentes fra forrige fil. Vil du heller ha en egen prisfil fra butikken, kan du lagre den som `data/polyalkemi.csv` i samme kolonner.

### Materie X (automatisk henting)

Materie X publiserer en Google Shopping-feed på `https://materiex.no/gshopping.xml`. `tools/materiex_feed.py` leser den, beholder produkter med produkttype «Filament» og skriver `data/materiex.csv` (én rad per farge, med pris, `sale_price` som pris og vanlig pris som `Førpris`, og lager). `pages.yml` kjører skriptet hver natt. Test uten nett: `python tools/materiex_feed.py data/materiex.csv --sample feed.xml`. Filen som ligger i repoet er en startfil og erstattes ved første kjøring.

I malen heter nøkkelen for førpris `was`. Eldre filer med to priser (`sale_price` og `onsale`) kan fortsatt leses.

Tomt lagerfelt betyr «utsolgt» for butikker som har `"empty_stock": "Utsolgt"` i `config/stores.json` (gjelder Polyalkemi). Andre butikker tolker tomt felt som ukjent lager.

Valgfrie kolonner (lager, bilde, merke, farge) kan mangle i en fil. Byggingen hopper da over dem og skriver en merknad, men stopper ikke. Navn og pris må finnes.

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
python -m src.build         # bygger dist/
cd dist && python -m http.server 8000   # se resultatet på http://localhost:8000
```

## Kjente begrensninger

- Produktbildene lastes direkte fra butikkenes servere (godkjent av butikkene) med `loading="lazy"` og uten referer. Hvis en butikk blokkerer lasting fra andre nettsteder eller flytter bildene, vises den tegnede spolen i stedet. Bildelenkene kommer fra kolonnen `image` i malen.
- Priser og lager er et øyeblikksbilde fra datoen i `snapshot`. Nettsiden sier det.
- Stratum3D mangler produktlenke i filen. Legg til en lenkekolonne i scraperen, og sett `"url"` i malen.
- Materiale, farge og merke leses fra navnet. Se rapporten for rader som ikke ble gjenkjent, og utvid listene i `src/enrich.py` ved behov.

## Guide til filament (`/guide/`)

Guiden er én side med datakort, bygget fra masterdatabladet i Excel.

- Arket ligger i `data/guide/master.xlsx`. Det er kilden for alle verdier i guiden.
- Siden leser `data/guide.json`, som lages av arket. Når du har endret arket, kjører du på din egen maskin:
  ```
  pip install openpyxl
  python tools/xlsx_to_guide.py
  ```
  og committer `master.xlsx` og `guide.json` sammen. GitHub bygger siden på nytt av seg selv.
- Arket er på engelsk. Oversettelsene ligger i `tools/guide_no.py`. Hvis du legger til nye verdier eller materialer i arket, stopper skriptet og sier hva som mangler oversettelse for.
- Søket i guiden filtrerer mens du skriver. Teksten må starte forkortelsen eller det tekniske navnet (P viser PLA og PETG, PL viser bare PLA og PLA+ / Pro).
- Materialer på nettsiden som mangler i arket (nå: PSU) får ikke datakort. Skriptet skriver ut hvilke det gjelder.
- De seks kolonnene Beginner Friendly, Outdoor, Mechanical Parts, High Temp, Support Material og Post-Process / Special vises ikke, fordi verdiene i arket ser feil ut (for eksempel Outdoor = Yes for PVA og Beginner Friendly = No for PLA).

### Filter og forslag i guiden

Knappen «Finn riktig filament» åpner et filter med to temperatur-sliders (dyse og seng) og avkrysning for «Ønsker» / «Unngå». Listen oppdateres med en gang. Kriteriene er definert i `CG` i `web/guide/index.html` og leser direkte fra `guide.json`. Materialer med manglende eller varierende data skjules som standard (og kan vises med et valg). Forslag er materialer som bryter høyst to av valgene, med begrunnelse hentet fra de samme dataene. Temperaturer finnes bare for materialene som har et oppgitt område i masterarket.

## Forsidebildet

Bildet på forsiden ligger som `web/hero.webp` (840 px bred, vises 420 px bredt på PC): en mann som klør seg i hodet foran en høy hylle med filamentspoler. Det står til høyre for overskriften og søkefeltet, og skjules på telefon. Bakgrunnen er ren hvit, og i lyst tema blandes bildet inn i sidens bakgrunn (`mix-blend-mode:multiply`). I mørkt tema vises det som et kort med runde hjørner. Rolig og 1999 skjuler bildet. Skal bildet byttes, lag en ny `hero.webp` med ren hvit bakgrunn.
