# Retningslinjer for dette repoet (Filamentsøk.no)

- Alt kommuniseres på norsk.
- Filene leveres i mappestruktur: `web/`, `data/`, `config/`, `src/`, `tools/`, `tests/`.
- **Funksjonssiden:** `web/funksjoner/index.html` lister alle funksjonene på nettsiden. Når en ny brukervendt funksjon legges til (eller en eksisterende endres på en måte brukeren merker), skal et kort legges til eller oppdateres i riktig gruppe på den siden i samme endring. Lenk til siden funksjonen finnes på når det er naturlig. Nevn i svaret at siden er oppdatert.
- Ikke endre logoen.
- Kjør testene (`pytest`) før ferdige filer leveres.
- **Versjonsnummer:** `config/version.json` (`version` og `date`) vises nederst på alle sider. Øk det (og legg en linje i `CHANGELOG.md`) i hver endring av siden eller funksjonene. Ikke øk det for rene prisoppdateringer eller datafiler. Nevn nytt versjonsnummer i svaret.
