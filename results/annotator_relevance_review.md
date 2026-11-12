# Annotator Re-Review — stale `is_relevant = f` on fulfilled items

> **For Annotator A.** These **8** items are `is_applicable = yes` and carry an
> `is_fulfilled` label, yet `is_relevant = f`. They were all flagged
> `length_judgment = too_short` during the first pass: the *originally shown*
> candidate passage was rejected, and better evidence was added via the
> "text too short" flow. After `rebuild_passages` that evidence is now folded into
> the passage below — so the `is_relevant = f` flag is likely **stale**.
>
> **Please check each: given the passage now shown, should `is_relevant` flip f → t?**
> Also re-confirm `is_fulfilled`.

---

## Krug_2024 / R11 — Gesamtbild der Risiko- und Chancenlage  (item_id 71)

- `is_applicable` = **yes**  |  `is_relevant` = **f**  |  `is_fulfilled` = **partially**  |  `length_judgment` = too_short
- annotator's `missing_info`: 'Wird eine Aussage zum Gesamtbild der Risiko- und Chancenlage getroffen?'
- annotator's `comment`: ''

**Evaluated passage (current, post-rebuild):**

> Für die nächsten Jahre sind wir für den weiteren Verkauf unserer Produkte weiter positiv gestimmt , wobei wir segmentspezifisch unterschiedliche Entwicklungen sehen .
> [...]
> Spezieller Risikobericht :
> Die Liquiditätslage ist sehr gut .
> Aufgrund der vollständigen Finanzierung durch Eigenkapital und Gesellschafterdarlehen wird es zu keinen Liquiditätsengpässen kommen .
> Zu den im Unternehmen bestehenden Finanzinstrumenten zählen im Wesentlichen Forderungen , Verbindlichkeiten und Guthaben bei Kreditinstituten .
> Ziel des Finanz - und Risikomanagements der Gesellschaft ist die Sicherung gegen finanzielle Risiken jeglicher Art . Beim Finanzmanagement verfolgt das Unternehmen eine konservative Risikopolitik .
> [...]
> Für das Geschäftsjahr 2025/2026 sowie die folgenden Geschäftsjahre gehen wir von einem profitablen , weiter leicht wachsenden Geschäft aus .
> Den Umsatzbeitrag der neuen Geschäftsfelder am Gesamtgeschäft erwarten wir weiter zunehmend .

---

## Miethke_2024 / R03 — Angabe der wesentlichen Annahmen der Prognose  (item_id 81)

- `is_applicable` = **yes**  |  `is_relevant` = **f**  |  `is_fulfilled` = **yes**  |  `length_judgment` = too_short
- annotator's `missing_info`: 'Was sind die wesentlichen Annahmen der Prognose?'
- annotator's `comment`: ''

**Evaluated passage (current, post-rebuild):**

> Unsere Erwartungen zur zukünftigen Geschäftsentwicklung sind nach wie vor optimistisch und werden auch durch den Auftragseingang gestützt .
> In wichtigen Exportmärkten wie z . B . Großbritannien , Brasilien , Vereinigte Staaten und Dänemark konnten signifikante Umsatzsteigerungen durch unseren Vertriebspartner erzielt werden .
> Ebenfalls hat sich die Nachfrage in China wieder erholt .
> Auf Basis unseres aktuellen Weltmarktanteils in Höhe von etwa 10 % und unserer guten Positionierung in den Wachstumsmärkten , sehen wir gute Chancen für ein stetiges weiteres Wachstum und eine Erhöhung unseres Marktanteils .
> Als gemeinsames strategisches Ziel ist mit unserem Vertriebspartner Aesculap AG für die nächsten Jahre ein weiterhin kontinuierliches Wachstum zwischen 5 % und 10 % angestrebt .
> [...]
> Negativen Einfluss auf das Geschäftsergebnis haben die signifikant erhöhten Raumkosten durch den Bezug der neuen Räumlichkeiten am Standort „ Rote Kaserne “ .
> Die Anstellung eines zweiten Geschäftsführers , die Schaffung strategischer Schlüsselpositionen sowie zu erwartende Gehaltssteigerungen in Zusammenhang mit der aktuellen Inflation führen zu einem überproportionalen Anstieg der Personalkosten .
> Mittelfristig wird eine Personalkostenquote von unter 50 % angestrebt .

---

## Miethke_2024 / R19 — Anlagenspiegel  (item_id 89)

- `is_applicable` = **yes**  |  `is_relevant` = **f**  |  `is_fulfilled` = **no**  |  `length_judgment` = too_short
- annotator's `missing_info`: ''
- annotator's `comment`: ''

**Evaluated passage (current, post-rebuild):**

> Bilanz
> Aktiva
> | | **30.9.2024 EUR** | **30.9.2023 EUR** |
> | --- | --- | --- |
> | A. Anlagevermögen | 3.919.795,91 | 3.630.134,56 |
> | I. Immaterielle Vermögensgegenstände | 138.682,91 | 252.414,91 |
> | II. Sachanlagen | 3.781.113,00 | 3.377.719,65 |
> | 1. Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 364.577,00 | 383.870,00 |
> | 2. technische Anlagen und Maschinen | 2.346.533,00 | 2.378.052,00 |
> | 3. andere Anlagen, Betriebs- und Geschäftsausstattung | 1.000.869,00 | 530.403,00 |
> | 4. geleistete Anzahlungen und Anlagen im Bau | 69.134,00 | 85.394,65 |
> | B. Umlaufvermögen | 10.356.550,10 | 7.882.907,52 |
> | I. Vorräte | 3.409.733,75 | 3.452.406,37 |
> | 1. erhaltene Anzahlungen auf Bestellungen | 150.145,00 | |
> | II. Forderungen und sonstige Vermögensgegenstände | 2.706.787,49 | 2.944.021,04 |
> | 1. Forderungen gegen Gesellschafter | | 236.116,90 |
> | 2. sonstige Vermögensgegenstände | 2.706.787,49 | 2.707.904,14 |
> | davon mit einer Restlaufzeit von mehr als einem Jahr | 2.580,00 | 2.080,00 |
> | III. Kassenbestand, Bundesbankguthaben, Guthaben bei Kreditinstituten und Schecks | 4.240.028,86 | 1.486.480,11 |
> | C. Rechnungsabgrenzungsposten | 290.540,78 | 416.021,64 |
> | Summe Aktiva | 14.566.886,79 | 11.929.063,72 |

---

## Schrott_2024 / R03 — Angabe der wesentlichen Annahmen der Prognose  (item_id 107)

- `is_applicable` = **yes**  |  `is_relevant` = **f**  |  `is_fulfilled` = **yes**  |  `length_judgment` = too_short
- annotator's `missing_info`: 'Zeige die wesentlichen Annahmen, auf denen die Prognosen beruhen'
- annotator's `comment`: ''

**Evaluated passage (current, post-rebuild):**

> Die Weltrohstahlproduktion wird weiter zurückgehen .
> Unsere Abnehmer geben keine klaren Planungen bekannt , sondern produzieren gedrosselt und unstetig .
> Die Wirtschaft hofft und baut auf einen Strategiewandel und eine pragmatische und wirtschaftsorientierte Politik , in der Deutschland als Industriestandort auf Europäischer Bühne und auch wieder international wettbewerbsfähig auftreten kann .
> Auf staatliche Hilfsprogramme und Subventionen allein können und wollen wir nicht bauen .
> Die Rohstoffpreise , auch die Metall - und Stahlschrottpreise , werden aufgrund der Unsicherheiten und der Eskalation bei den Zöllen weiter nachgeben .
> Es ist nicht zu erwarten , dass im 2 .
> Halbjahr ein schneller , nachhaltiger Preisanstieg eintreten oder sich ein rasanter , krisenbedingter Anstieg , wie während Coronapandemie , einstellen werden .
> Es muss aufgrund der schwachen Impulse aus Industrie und Handel von einem weiteren Mengenrückgang ausgegangen werden .
> [...]
> Wir rechnen aufgrund der plan - und turnusmäßig durchgeführten Lohn - und Gehaltsanpassungen zum 01.01 . mit leicht steigenden Personalkosten .

---

## Schrott_2024 / R17 — Finanzielle Leistungsindikatoren  (item_id 114)

- `is_applicable` = **yes**  |  `is_relevant` = **f**  |  `is_fulfilled` = **no**  |  `length_judgment` = too_short
- annotator's `missing_info`: 'Was sind die bedeutsamsten finanziellen Leistungsindikatoren und werden diese in die Analyse einbezogen und ihre Berechnung dargestellt?'
- annotator's `comment`: ''

**Evaluated passage (current, post-rebuild):**

> Roherträge waren im Jahre 2024 aber immer noch gut und auskömmlich .
> [...]
> Das Betriebsergebnis aus dem Geschäftsjahr 2024 war wie erwartet .
> [...]
> In dem vorstehenden , zur Offenlegung bestimmten verkürzten Jahresabschluss wurden die größenabhängigen Erleichterungen nach § 327 HGB zutreffend in Anspruch genommen .
> Zu dem vollständigen Jahresabschluss und dem Lagebericht haben wir den folgenden Bestätigungsvermerk erteilt :

---

## Tennet_TSO_2024 / R17 — Finanzielle Leistungsindikatoren  (item_id 127)

- `is_applicable` = **yes**  |  `is_relevant` = **f**  |  `is_fulfilled` = **partially**  |  `length_judgment` = too_short
- annotator's `missing_info`: 'Was sind die bedeutsamsten finanziellen Leistungsindikatoren der Gesellschaft?'
- annotator's `comment`: ''

**Evaluated passage (current, post-rebuild):**

> Die Versorgungssicherheit wird u . a . durch die branchenübliche Steuerungskennzahl „ Average System Interruption Duration Index “ ( ASIDI ) gemessen und lag 2024 bei null Minuten durchschnittlicher Versorgungsunterbrechung und damit auf höchstem Niveau .
> Im Geschäftsjahr 2024 kam es ungeachtet der herausfordernden Netzsituation zu keinem Versorgungsausfall mit Ursache im Netz der TTG .
> [...]
> Im letztjährigen Prognosebericht für das Geschäftsjahr 2024 wurde für die TTG ein handelsrechtliches Betriebsergebnis deutlich über dem Niveau von 2023 erwartet .
> Das Betriebsergebnis 2024 liegt mit 792,5 Mio . € der Prognose entsprechend tatsächlich deutlich über dem des Vorjahres
> ( 606,4 Mio . €). Die Geschäftsführung der TTG beurteilt den Geschäftsverlauf und die wirtschaftliche Lage positiv .
> Die Finanzlage kann als solide bezeichnet werden .

---

## Wajos_2024 / R02 — Angabe des Prognosezeitraums  (item_id 145)

- `is_applicable` = **yes**  |  `is_relevant` = **f**  |  `is_fulfilled` = **no**  |  `length_judgment` = too_short
- annotator's `missing_info`: 'Wird der Prognosezeitraum angegeben?'
- annotator's `comment`: ''

**Evaluated passage (current, post-rebuild):**

> Durch die allgemeinen politischen sowie weltwirtschaftlichen Lage bestehen weiterhin Unsicherheiten zur wirtschaftlichen Entwicklung .
> Die Auswirkungen das Jahresergebnis und auf die wirtschaftliche Entwicklung sind gegenwärtig nicht konkret abzuschätzen .
> Wir werden auch zukünftig in der Lage sein , unseren Zahlungsverpflichtungen fristgerecht nachzukommen .

---

## Wajos_2024 / R17 — Finanzielle Leistungsindikatoren  (item_id 153)

- `is_applicable` = **yes**  |  `is_relevant` = **f**  |  `is_fulfilled` = **partially**  |  `length_judgment` = too_short
- annotator's `missing_info`: 'Werden die  bedeutsamsten finanziellen Leistungsindikatoren in die Analyse einbezogen?'
- annotator's `comment`: 'Es wird nicht beschrieben, was die finanziellen Leistungsindikatoren sind.'

**Evaluated passage (current, post-rebuild):**

> Obwohl das Jahresergebnis im Vergleich zum Vorjahr um 27,3 % gesunken ist bleibt das Betriebsergebnis weiterhin positiv .
> [...]
> Unser Finanzmanagement ist darauf ausgerichtet , Verbindlichkeiten stets innerhalb der Zahlungsfrist zu begleichen und Forderungen innerhalb der Zahlungsziele zu vereinnahmen .
