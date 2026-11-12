"""Hand-reformatted R19 Anlagenspiegel passages, keyed by annotation_items.id.

Data only — see clean_anlagenspiegel.py for the apply/verify logic. Only the
table FORMATTING is changed; numeric values are preserved verbatim (enforced by
the number-conservation check).
"""

CLEAN: dict[int, str] = {}

# Tokens that legitimately appear as "added" because a single number was split
# across a "[...]" separator in the source and has been rejoined. Keyed by item id.
ALLOW_ADDED: dict[int, set[str]] = {}

# ── Amazon_2024 (item 11) ────────────────────────────────────────────────────
CLEAN[11] = """\
| **Anschaffungs- und Herstellungskosten** | **01.01.2024 TEUR** | **Zugänge TEUR** | **Abgänge TEUR** | **Umgliederungen TEUR** | **31.12.2024 TEUR** |
| --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | |
| Entgeltlich erworbene Software | 17 | - | - | - | 17 |
| II. Sachanlagen | | | | | |
| 1. Mietereinbauten | 40.512 | 766 | 652 | -414 | 40.213 |
| 2. Technische Anlagen und Maschinen | 2.786 | 1.424 | 268 | - | 3.942 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 31.045 | 2.236 | 2.691 | - | 30.590 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 44.829 | 47.428 | - | 414 | 92.672 |
| | 119.172 | 51.855 | 3.611 | - | 167.416 |
| | 119.189 | 51.855 | 3.611 | - | 167.433 |

| **Kumulierte Abschreibungen** | **01.01.2024 TEUR** | **Zugänge TEUR** | **Abgänge TEUR** | **Umgliederungen TEUR** | **31.12.2024 TEUR** |
| --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | |
| Entgeltlich erworbene Software | 17 | - | - | - | 17 |
| II. Sachanlagen | | | | | |
| 1. Mietereinbauten | 16.012 | 11.141 | - | - | 27.153 |
| 2. Technische Anlagen und Maschinen | 2.400 | 232 | 268 | - | 2.364 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 19.513 | 5.828 | 2.403 | - | 22.938 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | - | - | - | - | - |
| | 37.926 | 17.200 | 2.671 | - | 52.455 |
| | 37.942 | 17.200 | 2.671 | - | 52.471 |

| **Buchwerte** | **31.12.2024 TEUR** | **31.12.2023 TEUR** |
| --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | |
| Entgeltlich erworbene Software | - | - |
| II. Sachanlagen | | |
| 1. Mietereinbauten | 13.060 | 24.499 |
| 2. Technische Anlagen und Maschinen | 1.579 | 386 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 7.652 | 11.532 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 92.672 | 44.829 |
| | 114.962 | 81.247 |"""

# ── Miethke_2024 (item 89) — Bilanz Aktiva (the R19 passage shows the balance sheet) ──
CLEAN[89] = """\
## Bilanz

### Aktiva

| | **30.9.2024 EUR** | **30.9.2023 EUR** |
| --- | --- | --- |
| A. Anlagevermögen | 3.919.795,91 | 3.630.134,56 |
| I. Immaterielle Vermögensgegenstände | 138.682,91 | 252.414,91 |
| II. Sachanlagen | 3.781.113,00 | 3.377.719,65 |
| 1. Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 364.577,00 | 383.870,00 |
| 2. technische Anlagen und Maschinen | 2.346.533,00 | 2.378.052,00 |
| 3. andere Anlagen, Betriebs- und Geschäftsausstattung | 1.000.869,00 | 530.403,00 |
| 4. geleistete Anzahlungen und Anlagen im Bau | 69.134,00 | 85.394,65 |
| B. Umlaufvermögen | 10.356.550,10 | 7.882.907,52 |
| I. Vorräte | 3.409.733,75 | 3.452.406,37 |
| 1. erhaltene Anzahlungen auf Bestellungen | 150.145,00 | |
| II. Forderungen und sonstige Vermögensgegenstände | 2.706.787,49 | 2.944.021,04 |
| 1. Forderungen gegen Gesellschafter | | 236.116,90 |
| 2. sonstige Vermögensgegenstände | 2.706.787,49 | 2.707.904,14 |
| davon mit einer Restlaufzeit von mehr als einem Jahr | 2.580,00 | 2.080,00 |
| III. Kassenbestand, Bundesbankguthaben, Guthaben bei Kreditinstituten und Schecks | 4.240.028,86 | 1.486.480,11 |
| C. Rechnungsabgrenzungsposten | 290.540,78 | 416.021,64 |
| Summe Aktiva | 14.566.886,79 | 11.929.063,72 |"""

# ── Tennet_TSO_2024 (item 128) — in Mio € ────────────────────────────────────
CLEAN[128] = """\
Entwicklung des Anlagevermögens
- in Mio € -

| **Anschaffungs- und Herstellungskosten** | **01.01.2024** | **laufende Zugänge** | **laufende Abgänge** | **Umbuchungen** | **31.12.2024** |
| --- | --- | --- | --- | --- | --- |
| Immaterielle Vermögensgegenstände | | | | | |
| Selbst geschaffene gewerbliche Schutzrechte und ähnliche Rechte und Werte | 2,0 | 3,0 | 0,0 | 0,0 | 5,0 |
| entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 178,4 | 8,6 | 0,0 | 3,6 | 190,6 |
| geleistete Anzahlungen | 38,3 | 35,7 | 0,0 | -3,6 | 70,4 |
| | 218,8 | 47,3 | 0,0 | 0,0 | 266,0 |
| Sachanlagen | | | | | |
| Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 518,6 | 130,9 | 0,6 | 22,5 | 671,4 |
| technische Anlagen und Maschinen | 8.012,3 | 335,5 | 37,6 | 954,7 | 9.264,9 |
| andere Anlagen, Betriebs- und Geschäftsausstattung | 133,0 | 44,6 | 0,2 | 4,4 | 181,8 |
| geleistete Anzahlungen und Anlagen im Bau | 5.131,3 | 3.380,9 | 1,7 | -981,5 | 7.529,0 |
| | 13.795,2 | 3.891,9 | 40,1 | 0,0 | 17.647,0 |
| Summe Immaterielle Vermögensgegenstände und Sachanlagen | 14.014,0 | 3.939,1 | 40,1 | 0,0 | 17.913,1 |
| Finanzanlagen | | | | | |
| Beteiligungen | 0,9 | 0,1 | 0,0 | 0,0 | 0,9 |
| sonstige Ausleihungen | 2,8 | 1,1 | 0,0 | 0,0 | 3,9 |
| | 3,7 | 1,2 | 0,0 | 0,0 | 4,9 |
| Summe Anlagevermögen | 14.017,7 | 3.940,3 | 40,1 | 0,0 | 17.917,9 |

| **Abschreibungen** | **01.01.2024** | **laufende Zugänge** | **laufende Abgänge** | **Umbuchungen** | **31.12.2024** |
| --- | --- | --- | --- | --- | --- |
| Immaterielle Vermögensgegenstände | | | | | |
| Selbst geschaffene gewerbliche Schutzrechte und ähnliche Rechte und Werte | 0,1 | 0,0 | 0,0 | 0,0 | 0,1 |
| entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 121,6 | 10,6 | 0,0 | 0,0 | 132,2 |
| geleistete Anzahlungen | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 |
| | 121,7 | 10,6 | 0,0 | 0,0 | 132,3 |
| Sachanlagen | | | | | |
| Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 108,3 | 6,4 | 0,2 | 0,0 | 114,5 |
| technische Anlagen und Maschinen | 2.868,2 | 200,6 | 34,2 | 0,0 | 3.034,5 |
| andere Anlagen, Betriebs- und Geschäftsausstattung | 65,6 | 17,0 | 0,2 | 0,0 | 82,4 |
| geleistete Anzahlungen und Anlagen im Bau | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 |
| | 3.042,1 | 224,0 | 34,5 | 0,0 | 3.231,5 |
| Summe Immaterielle Vermögensgegenstände und Sachanlagen | 3.163,8 | 234,5 | 34,5 | 0,0 | 3.363,8 |
| Finanzanlagen | | | | | |
| Beteiligungen | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 |
| sonstige Ausleihungen | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 |
| | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 |
| Summe Anlagevermögen | 3.163,8 | 234,5 | 34,5 | 0,0 | 3.363,8 |

| **Buchwerte** | **31.12.2024** | **Vorjahr** |
| --- | --- | --- |
| Immaterielle Vermögensgegenstände | | |
| Selbst geschaffene gewerbliche Schutzrechte und ähnliche Rechte und Werte | 4,9 | 1,9 |
| entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 58,4 | 56,8 |
| geleistete Anzahlungen | 70,4 | 38,3 |
| | 133,7 | 97,0 |
| Sachanlagen | | |
| Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 556,9 | 410,3 |
| technische Anlagen und Maschinen | 6.230,3 | 5.144,1 |
| andere Anlagen, Betriebs- und Geschäftsausstattung | 99,4 | 67,5 |
| geleistete Anzahlungen und Anlagen im Bau | 7.529,0 | 5.131,3 |
| | 14.415,6 | 10.753,1 |
| Summe Immaterielle Vermögensgegenstände und Sachanlagen | 14.549,2 | 10.850,2 |
| Finanzanlagen | | |
| Beteiligungen | 0,9 | 0,9 |
| sonstige Ausleihungen | 3,9 | 2,8 |
| | 4,9 | 3,7 |
| Summe Anlagevermögen | 14.554,1 | 10.853,9 |"""

# ── Wajos_2024 (item 154) ────────────────────────────────────────────────────
CLEAN[154] = """\
| **ANSCHAFFUNGS- UND HERSTELLUNGSKOSTEN** | **1. Jan. 2024 €** | **Zugänge €** | **Abgänge €** | **31. Dez. 2024 €** |
| --- | --- | --- | --- | --- |
| I. IMMATERIELLE VERMÖGENSGEGENSTÄNDE | | | | |
| Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 148.283,12 | 0,00 | 0,00 | 148.283,12 |
| II. SACHANLAGEN | | | | |
| Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 8.367.936,88 | 10.754,66 | 0,00 | 8.378.691,54 |
| Technische Anlagen und Maschinen | 1.535.545,64 | 14.484,09 | 10.875,00 | 1.539.154,73 |
| Andere Anlagen, Betriebs- und Geschäftsausstattung | 2.250.782,97 | 119.306,47 | 22.070,64 | 2.348.018,80 |
| | 12.154.265,49 | 144.545,22 | 32.945,64 | 12.265.865,07 |
| III. FINANZANLAGEN | | | | |
| Ausleihungen an verbundene Unternehmen | 171.337,96 | 51.797,37 | 0,00 | 223.135,33 |
| Sonstige Ausleihungen | 825.030,99 | 0,00 | 91.348,89 | 733.682,10 |
| | 996.368,95 | 51.797,37 | 91.348,89 | 956.817,43 |
| | 13.298.917,56 | 196.342,59 | 124.294,53 | 13.370.965,62 |

| **KUMULIERTE ABSCHREIBUNGEN** | **1. Jan. 2024 €** | **Zugänge €** | **Abgänge €** | **31. Dez. 2024 €** |
| --- | --- | --- | --- | --- |
| I. IMMATERIELLE VERMÖGENSGEGENSTÄNDE | | | | |
| Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 114.512,12 | 19.321,00 | 0,00 | 133.833,12 |
| II. SACHANLAGEN | | | | |
| Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 1.007.855,25 | 270.063,66 | 0,00 | 1.277.918,91 |
| Technische Anlagen und Maschinen | 874.987,64 | 112.879,09 | 10.873,00 | 976.993,73 |
| Andere Anlagen, Betriebs- und Geschäftsausstattung | 1.451.484,97 | 190.036,47 | 21.870,64 | 1.619.650,80 |
| | 3.334.327,86 | 572.979,22 | 32.743,64 | 3.874.563,44 |
| III. FINANZANLAGEN | | | | |
| Ausleihungen an verbundene Unternehmen | 0,00 | 0,00 | 0,00 | 0,00 |
| Sonstige Ausleihungen | 219.449,45 | 0,00 | 0,00 | 219.449,45 |
| | 219.449,45 | 0,00 | 0,00 | 219.449,45 |
| | 3.668.289,43 | 592.300,22 | 32.743,64 | 4.227.846,01 |

| **NETTOBUCHWERTE** | **31. Dez. 2024 €** | **31. Dez. 2023 €** |
| --- | --- | --- |
| I. IMMATERIELLE VERMÖGENSGEGENSTÄNDE | | |
| Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 14.450,00 | 33.771,00 |
| II. SACHANLAGEN | | |
| Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 7.100.772,63 | 7.360.081,63 |
| Technische Anlagen und Maschinen | 562.161,00 | 660.558,00 |
| Andere Anlagen, Betriebs- und Geschäftsausstattung | 728.368,00 | 799.298,00 |
| | 8.391.301,63 | 8.819.937,63 |
| III. FINANZANLAGEN | | |
| Ausleihungen an verbundene Unternehmen | 223.135,33 | 171.337,96 |
| Sonstige Ausleihungen | 514.232,65 | 605.581,54 |
| | 737.367,98 | 776.919,50 |
| | 9.143.119,61 | 9.630.628,13 |"""

# ── Yaveon_2024 (item 167) — extra "Verschmelzung" column; Buchwerte cells were
#    collided onto section-header rows in the source (reconstructed). ───────────
CLEAN[167] = """\
| **ANSCHAFFUNGS- UND HERSTELLUNGSKOSTEN** | **01.01.2024 EUR** | **Verschmelzung EUR** | **Zugänge EUR** | **Abgänge EUR** | **31.12.2024 EUR** |
| --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | |
| Selbst geschaffene gewerbliche Schutzrechte und ähnliche Rechte und Werte | 1.298.821,00 | 0,00 | 166.886,00 | 0,00 | 1.465.707,00 |
| entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 538.381,00 | 0,00 | 325.775,25 | -72.754,62 | 791.401,63 |
| | 1.837.202,00 | 0,00 | 492.661,25 | -72.754,62 | 2.257.108,63 |
| II. Sachanlagen | | | | | |
| andere Anlagen, Betriebs- und Geschäftsausstattung | 612.860,79 | 86.063,94 | 241.987,83 | -76.555,42 | 864.357,14 |
| | 612.860,79 | 86.063,94 | 241.987,83 | -76.555,42 | 864.357,14 |
| III. Finanzanlagen | | | | | |
| Anteile an verbundenen Unternehmen | 3.198.240,84 | -1.965.636,48 | 12.531,52 | -1.147.998,52 | 97.137,36 |
| Ausleihungen an verbundene Unternehmen | 4.680.736,19 | 0,00 | 1.318.972,90 | -300.000,00 | 5.699.709,09 |
| | 7.878.977,03 | -1.965.636,48 | 1.331.504,42 | -1.447.998,52 | 5.796.846,45 |
| | 10.329.039,82 | -1.879.572,54 | 2.066.153,50 | -1.597.308,56 | 8.918.312,22 |

| **AUFGELAUFENE ABSCHREIBUNGEN** | **01.01.2024 EUR** | **Verschmelzung EUR** | **Zugänge EUR** | **Abgänge EUR** | **31.12.2024 EUR** |
| --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | |
| Selbst geschaffene gewerbliche Schutzrechte und ähnliche Rechte und Werte | 991.716,90 | 0,00 | 295.314,10 | 0,00 | 1.287.031,00 |
| entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 472.723,48 | 0,00 | 59.091,65 | -72.754,62 | 459.060,51 |
| | 1.464.440,38 | 0,00 | 354.405,75 | -72.754,62 | 1.746.091,51 |
| II. Sachanlagen | | | | | |
| andere Anlagen, Betriebs- und Geschäftsausstattung | 588.212,09 | 29.035,05 | 98.685,69 | -75.567,75 | 640.365,08 |
| | 588.212,09 | 29.035,05 | 98.685,69 | -75.567,75 | 640.365,08 |
| III. Finanzanlagen | | | | | |
| Anteile an verbundenen Unternehmen | 1.965.636,48 | -1.965.636,48 | 0,00 | 0,00 | 0,00 |
| Ausleihungen an verbundene Unternehmen | 477.522,11 | 0,00 | 0,00 | -300.000,00 | 177.522,11 |
| | 2.443.158,59 | -1.965.636,48 | 0,00 | -300.000,00 | 177.522,11 |
| | 4.495.811,06 | -1.936.601,43 | 453.091,44 | -448.322,37 | 2.563.978,70 |

| **NETTOBUCHWERTE** | **31.12.2024 EUR** | **31.12.2023 EUR** |
| --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | |
| Selbst geschaffene gewerbliche Schutzrechte und ähnliche Rechte und Werte | 178.676,00 | 307.104,10 |
| entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 332.341,12 | 65.657,52 |
| | 511.017,12 | 372.761,62 |
| II. Sachanlagen | | |
| andere Anlagen, Betriebs- und Geschäftsausstattung | 223.992,06 | 24.648,70 |
| | 223.992,06 | 24.648,70 |
| III. Finanzanlagen | | |
| Anteile an verbundenen Unternehmen | 97.137,36 | 1.232.604,36 |
| Ausleihungen an verbundene Unternehmen | 5.522.186,98 | 4.203.214,08 |
| | 5.619.324,34 | 5.435.818,44 |
| | 6.354.333,52 | 5.833.228,76 |"""

# ── Johnson_2025 (item 63) — fiscal year 01.04.2024–31.03.2025 ────────────────
CLEAN[63] = """\
| **Anschaffungs- und Herstellungskosten** | **01.04.2024 €** | **Zugänge €** | **Umbuchungen €** | **Abgänge €** | **31.03.2025 €** |
| --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | |
| entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte u.ä. Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 168.429,14 | 284,42 | 0,00 | 0,00 | 168.713,56 |
| II. Sachanlagen | | | | | |
| 1. Grundstücke, grundstücksgleiche Rechte und Bauten | 5.001.506,93 | 5.023,95 | 0,00 | -1,00 | 5.006.529,88 |
| 2. Technische Anlagen und Maschinen | 10.688.385,08 | 243.331,48 | 547.876,24 | -3,00 | 11.479.589,80 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 1.591.921,26 | 31.780,88 | 0,00 | -15,00 | 1.623.687,14 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 547.876,24 | 170.342,20 | -547.876,24 | 0,00 | 170.342,20 |
| | 17.829.689,51 | 450.478,51 | 0,00 | -19,00 | 18.280.149,02 |
| III. Finanzanlagen | | | | | |
| 1. Anteile an verbundenen Unternehmen | 16.780.024,17 | 1.250.018,80 | 0,00 | 0,00 | 18.030.042,97 |
| | 34.778.142,82 | 1.700.781,73 | 0,00 | -19,00 | 36.478.905,55 |

| **Abschreibungen** | **01.04.2024 €** | **Zugänge €** | **Abgänge €** | **31.03.2025 €** |
| --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | |
| entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte u.ä. Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 121.011,16 | 38.375,73 | 0,00 | 159.386,89 |
| II. Sachanlagen | | | | |
| 1. Grundstücke, grundstücksgleiche Rechte und Bauten | 507.021,63 | 112.409,80 | 0,00 | 619.431,43 |
| 2. Technische Anlagen und Maschinen | 7.543.621,80 | 399.300,98 | 0,00 | 7.942.922,78 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 1.118.569,12 | 94.672,08 | 0,00 | 1.213.241,20 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 0,00 | 0,00 | 0,00 | 0,00 |
| | 9.169.212,55 | 606.382,86 | 0,00 | 9.775.595,41 |
| III. Finanzanlagen | | | | |
| 1. Anteile an verbundenen Unternehmen | 0,00 | 0,00 | 0,00 | 0,00 |
| | 9.290.223,71 | 644.758,59 | 0,00 | 9.934.982,30 |

| **Restbuchwerte** | **31.03.2025 €** | **31.03.2024 €** |
| --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | |
| entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte u.ä. Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 9.326,67 | 47.417,98 |
| II. Sachanlagen | | |
| 1. Grundstücke, grundstücksgleiche Rechte und Bauten | 4.387.098,45 | 4.494.485,30 |
| 2. Technische Anlagen und Maschinen | 3.536.667,02 | 3.144.763,28 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 410.445,94 | 473.352,14 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 170.342,20 | 547.876,24 |
| | 8.504.553,61 | 8.660.476,96 |
| III. Finanzanlagen | | |
| 1. Anteile an verbundenen Unternehmen | 18.030.042,97 | 16.780.024,17 |
| | 26.543.923,25 | 25.487.919,11 |"""

# ── Krug_2024 (item 76) — fiscal year 01.07.2023–30.06.2024. Several opening
#    balances were merged INTO the wrapped label text in the source; moved back
#    into the "01.07.2023" column (verified: opening +/- movements = closing). ──
CLEAN[76] = """\
Anlagevermögen
Die Entwicklung des Anlagevermögens im Geschäftsjahr ist nachfolgend dargestellt:
Anlagespiegel

| **Anschaffungs- und Herstellungskosten** | **01.07.2023 Euro** | **Zugänge Euro** | **Abgänge Euro** | **Umbuchung** | **30.06.2024 Euro** |
| --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | |
| 1. entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 1.125.409,24 | 88.003,00 | 64.148,54 | 11.000,00 | 1.160.263,70 |
| 2. Geschäfts- oder Firmenwert | 3.196.829,02 | 0,00 | 0,00 | | 3.196.829,02 |
| 3. Geleistete Anzahlungen | 11.000,00 | 0,00 | 0,00 | -11.000,00 | 0,00 |
| Summe I. | 4.333.238,26 | 88.003,00 | 64.148,54 | 0,00 | 4.357.092,72 |
| II. Sachanlagen | | | | | |
| 1. Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 294.704,40 | 0,00 | 0,00 | 0,00 | 294.704,40 |
| 2. technische Anlagen und Maschinen | 17.923.042,87 | 802.674,49 | 79.609,79 | 0,00 | 18.646.107,57 |
| 3. andere Anlagen, Betriebs- und Geschäftsausstattung | 2.503.046,09 | 233.682,13 | 381.741,25 | 0,00 | 2.354.986,97 |
| 4. geleistete Anzahlungen und Anlagen im Bau | 0,00 | 40.759,45 | 0,00 | 0,00 | 40.759,45 |
| Summe II. | 20.720.793,36 | 1.077.116,07 | 461.351,04 | 0,00 | 21.336.558,39 |
| Summe I. + II. | 25.054.031,62 | 1.165.119,07 | 525.499,58 | 0,00 | 25.693.651,11 |

| **Abschreibungen** | **01.07.2023 Euro** | **Geschäftsjahr Euro** | **Abgänge Euro** | **30.06.2024 Euro** |
| --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | |
| 1. entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 1.045.722,24 | 51.524,00 | 64.146,54 | 1.033.099,70 |
| 2. Geschäfts- oder Firmenwert | 3.196.828,02 | 0,00 | 0,00 | 3.196.828,02 |
| 3. Geleistete Anzahlungen | 0,00 | 0,00 | 0,00 | 0,00 |
| Summe I. | 4.242.550,26 | 51.524,00 | 64.146,54 | 4.229.927,72 |
| II. Sachanlagen | | | | |
| 1. Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 286.622,90 | 2.068,00 | 0,00 | 288.690,90 |
| 2. technische Anlagen und Maschinen | 13.849.765,47 | 741.977,99 | 79.602,79 | 14.512.140,67 |
| 3. andere Anlagen, Betriebs- und Geschäftsausstattung | 2.173.991,08 | 122.988,63 | 381.726,25 | 1.915.253,46 |
| 4. geleistete Anzahlungen und Anlagen im Bau | 0,00 | 0,00 | 0,00 | 0,00 |
| Summe II. | 16.310.379,45 | 867.034,62 | 461.329,04 | 16.716.085,03 |
| Summe I. + II. | 20.552.929,71 | 918.558,62 | 525.475,58 | 20.946.012,75 |

| **Buchwert** | **30.06.2024 Euro** | **30.06.2023 Euro** |
| --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | |
| 1. entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 127.164,00 | 79.687,00 |
| 2. Geschäfts- oder Firmenwert | 1,00 | 1,00 |
| 3. Geleistete Anzahlungen | 0,00 | 11.000,00 |
| Summe I. | 127.165,00 | 90.688,00 |
| II. Sachanlagen | | |
| 1. Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 6.013,50 | 8.081,50 |
| 2. technische Anlagen und Maschinen | 4.133.966,90 | 4.073.277,40 |
| 3. andere Anlagen, Betriebs- und Geschäftsausstattung | 439.733,51 | 329.055,01 |
| 4. geleistete Anzahlungen und Anlagen im Bau | 40.759,45 | 0,00 |
| Summe II. | 4.620.473,36 | 4.410.413,91 |
| Summe I. + II. | 4.747.638,36 | 4.501.101,91 |"""

# ── WN24_2024 (item 141) — each section-header row in the source carried the
#    PREVIOUS section's subtotal; shifted back to its own row (cross-checked
#    against the column sums). ──────────────────────────────────────────────────
CLEAN[141] = """\
## Entwicklung des Anlagevermögens zum 31.12.2024

| **Anschaffungs- und Herstellungskosten** | **1.1.2024 EUR** | **Zugänge EUR** | **Abgänge EUR** | **Umbuchungen EUR** | **31.12.2024 EUR** |
| --- | --- | --- | --- | --- | --- |
| Immaterielle Vermögensgegenstände | | | | | |
| Rechte und Lizenzen | 16.941.838,20 | 360.912,11 | 0,00 | 18.539,21 | 17.321.289,52 |
| Geleistete Anzahlungen | 12.639,21 | 0,00 | 0,00 | -12.639,21 | 0,00 |
| | 16.954.477,41 | 360.912,11 | 0,00 | 5.900,00 | 17.321.289,52 |
| Sachanlagen | | | | | |
| Grundstücke und Gebäude | 1.899.305,73 | 0,00 | 0,00 | 0,00 | 1.899.305,73 |
| Technische Anlagen und Maschinen | 30.546.261,63 | 2.834,00 | 0,00 | 0,00 | 30.549.095,63 |
| Andere Anlagen, Betriebs- und Geschäftsausstattung | 8.000.409,52 | 1.198.350,12 | 397.994,53 | 27.567,63 | 8.828.332,74 |
| Geleistete Anzahlungen und Anlagen im Bau | 5.900,00 | 27.567,63 | 0,00 | -33.467,63 | 0,00 |
| | 40.451.876,88 | 1.228.751,75 | 397.994,53 | -5.900,00 | 41.276.734,10 |
| Finanzanlagen | | | | | |
| Anteile an verbundenen Unternehmen | 9.985.730,56 | 15.814.098,00 | 25.774.828,56 | 0,00 | 25.000,00 |
| Beteiligungen | 1.624.856,44 | 0,00 | 0,00 | 0,00 | 1.624.856,44 |
| | 11.610.587,00 | 15.814.098,00 | 25.774.828,56 | 0,00 | 1.649.856,44 |
| | 69.016.941,29 | 17.403.761,86 | 26.172.823,09 | 0,00 | 60.247.880,06 |

| **Kumulierte Abschreibungen** | **1.1.2024 EUR** | **Zugänge EUR** | **Abgänge EUR** | **31.12.2024 EUR** |
| --- | --- | --- | --- | --- |
| Immaterielle Vermögensgegenstände | | | | |
| Rechte und Lizenzen | 13.814.532,20 | 1.474.287,13 | 0,00 | 15.288.819,33 |
| Geleistete Anzahlungen | 0,00 | 0,00 | 0,00 | 0,00 |
| | 13.814.532,20 | 1.474.287,13 | 0,00 | 15.288.819,33 |
| Sachanlagen | | | | |
| Grundstücke und Gebäude | 1.899.305,73 | 0,00 | 0,00 | 1.899.305,73 |
| Technische Anlagen und Maschinen | 15.303.635,63 | 5.061.154,00 | 0,00 | 20.364.789,63 |
| Andere Anlagen, Betriebs- und Geschäftsausstattung | 4.861.330,31 | 838.852,96 | 377.123,06 | 5.323.060,21 |
| Geleistete Anzahlungen und Anlagen im Bau | 0,00 | 0,00 | 0,00 | 0,00 |
| | 22.064.271,67 | 5.900.006,96 | 377.123,06 | 27.587.155,57 |
| Finanzanlagen | | | | |
| Anteile an verbundenen Unternehmen | 8.862.174,46 | 0,00 | 8.862.174,46 | 0,00 |
| Beteiligungen | 632.770,69 | 52.616,86 | 0,00 | 685.387,55 |
| | 9.494.945,15 | 52.616,86 | 8.862.174,46 | 685.387,55 |
| | 45.373.749,02 | 7.426.910,95 | 9.239.297,52 | 43.561.362,45 |

| **Buchwerte** | **31.12.2024 EUR** | **31.12.2023 EUR** |
| --- | --- | --- |
| Immaterielle Vermögensgegenstände | | |
| Rechte und Lizenzen | 2.032.470,19 | 3.127.306,00 |
| Geleistete Anzahlungen | 0,00 | 12.639,21 |
| | 2.032.470,19 | 3.139.945,21 |
| Sachanlagen | | |
| Grundstücke und Gebäude | 0,00 | 0,00 |
| Technische Anlagen und Maschinen | 10.184.306,00 | 15.242.626,00 |
| Andere Anlagen, Betriebs- und Geschäftsausstattung | 3.505.272,53 | 3.139.079,21 |
| Geleistete Anzahlungen und Anlagen im Bau | 0,00 | 5.900,00 |
| | 13.689.578,53 | 18.387.605,21 |
| Finanzanlagen | | |
| Anteile an verbundenen Unternehmen | 25.000,00 | 1.123.556,10 |
| Beteiligungen | 939.468,89 | 992.085,75 |
| | 964.468,89 | 2.115.641,85 |
| | 16.686.517,61 | 23.643.192,27 |"""

# ── Zollern_2024 (item 180) — Konzernanlagenspiegel. AHK and Abschreibungen were
#    each split across two page-halves in the source; merged row-by-row into one
#    table per section (verified: Vortrag +Zug. +Umb. -Abg. = 31.12.). One stray
#    number (82.176,94, on the Abschr. Finanzanlagen header line) had no column
#    and was dropped — VERIFY against PDF. ─────────────────────────────────────
CLEAN[180] = """\
## Entwicklung des Konzernanlagevermögens im Geschäftsjahr 2024

| **Anschaffungs- und Herstellungskosten** | **1.1.2024 EUR** | **Währungsdifferenz EUR** | **Vortrag 1.1.2024 EUR** | **Zugänge EUR** | **Umbuchung EUR** | **Abgang EUR** | **31.12.2024 EUR** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | | | |
| 1. Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 9.557.191,88 | 20.457,29 | 9.577.649,17 | 602.532,08 | 10.705,00 | 382.941,51 | 9.807.944,74 |
| 2. Geschäfts- oder Firmenwert | 1.657.371,13 | 0,00 | 1.657.371,13 | 0,00 | 0,00 | 0,00 | 1.657.371,13 |
| 3. Geleistete Anzahlungen auf immaterielle Vermögensgegenstände | 59.234,48 | 0,00 | 59.234,48 | 208.681,78 | -12.866,94 | 0,00 | 255.049,32 |
| | 11.273.797,49 | 20.457,29 | 11.294.254,78 | 811.213,86 | -2.161,94 | 382.941,51 | 11.720.365,19 |
| II. Sachanlagen | | | | | | | |
| 1. Grundstücke und Bauten | 95.028.791,30 | 401.502,77 | 95.430.294,07 | 26.414,77 | -15.176,98 | 211.325,95 | 95.230.205,91 |
| 2. Technische Anlagen und Maschinen | 202.556.911,91 | 103.664,54 | 202.660.576,45 | 5.342.448,57 | 5.674.949,48 | 7.611.585,83 | 206.066.388,67 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 67.525.850,15 | 127.947,44 | 67.653.797,59 | 4.999.024,00 | 332.034,80 | 2.853.042,66 | 70.131.813,73 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 6.015.522,38 | 0,00 | 6.015.522,38 | 7.047.959,00 | -5.989.645,36 | 0,00 | 7.073.836,02 |
| | 371.127.075,74 | 633.114,75 | 371.760.190,49 | 17.415.846,34 | 2.161,94 | 10.675.954,44 | 378.502.244,33 |
| III. Finanzanlagen | | | | | | | |
| 1. Beteiligungen an assoziierten Unternehmen | 41.925.443,36 | 0,00 | 41.925.443,36 | 6.932.708,05 | 0,00 | 48.858.151,41 | 0,00 |
| 2. Beteiligungen | 294.745,44 | 0,00 | 294.745,44 | 0,00 | 0,00 | 0,00 | 294.745,44 |
| | 42.220.188,80 | 0,00 | 42.220.188,80 | 6.932.708,05 | 0,00 | 48.858.151,41 | 294.745,44 |
| | 424.621.062,03 | 653.572,04 | 425.274.634,07 | 25.159.768,25 | 0,00 | 59.917.047,36 | 390.517.354,96 |

| **Kumulierte Abschreibungen** | **1.1.2024 EUR** | **Währungsdifferenz EUR** | **Vortrag 1.1.2024 EUR** | **Abschreibungen des Geschäftsjahres EUR** | **Abgänge EUR** | **31.12.2024 EUR** |
| --- | --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | | |
| 1. Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 8.747.840,98 | 16.322,35 | 8.764.163,33 | 533.460,49 | 382.941,51 | 8.914.682,31 |
| 2. Geschäfts- oder Firmenwert | 1.657.371,13 | 0,00 | 1.657.371,13 | 0,00 | 0,00 | 1.657.371,13 |
| 3. Geleistete Anzahlungen auf immaterielle Vermögensgegenstände | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| | 10.405.212,11 | 16.322,35 | 10.421.534,46 | 533.460,49 | 382.941,51 | 10.572.053,44 |
| II. Sachanlagen | | | | | | |
| 1. Grundstücke und Bauten | 58.106.472,26 | 205.073,30 | 58.311.545,56 | 2.379.350,86 | 203.969,95 | 60.486.926,47 |
| 2. Technische Anlagen und Maschinen | 162.341.053,16 | 101.705,27 | 162.442.758,43 | 9.389.000,88 | 7.609.344,38 | 164.222.414,93 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 51.958.383,80 | 108.361,71 | 52.066.745,51 | 4.105.458,88 | 2.780.463,17 | 53.391.741,22 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| | 272.405.909,22 | 415.140,28 | 272.821.049,50 | 15.873.810,62 | 10.593.777,50 | 278.101.082,62 |
| III. Finanzanlagen | | | | | | |
| 1. Beteiligungen an assoziierten Unternehmen | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| 2. Beteiligungen | 294.745,44 | 0,00 | 294.745,44 | 0,00 | 0,00 | 294.745,44 |
| | 294.745,44 | 0,00 | 294.745,44 | 0,00 | 0,00 | 294.745,44 |
| | 283.105.866,77 | 431.462,63 | 283.537.329,40 | 16.407.271,11 | 10.976.719,01 | 288.967.881,50 |

| **Buchwerte** | **31.12.2024 EUR** | **31.12.2023 EUR** |
| --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | |
| 1. Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 893.262,43 | 809.350,90 |
| 2. Geschäfts- oder Firmenwert | 0,00 | 0,00 |
| 3. Geleistete Anzahlungen auf immaterielle Vermögensgegenstände | 255.049,32 | 59.234,48 |
| | 1.148.311,75 | 868.585,38 |
| II. Sachanlagen | | |
| 1. Grundstücke und Bauten | 34.743.279,44 | 36.922.319,04 |
| 2. Technische Anlagen und Maschinen | 41.843.973,74 | 40.215.858,75 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 16.740.072,51 | 15.567.466,35 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 7.073.836,02 | 6.015.522,38 |
| | 100.401.161,71 | 98.721.166,52 |
| III. Finanzanlagen | | |
| 1. Beteiligungen an assoziierten Unternehmen | 0,00 | 41.925.443,36 |
| 2. Beteiligungen | 0,00 | 0,00 |
| | 0,00 | 41.925.443,36 |
| | 101.549.473,46 | 141.515.195,26 |"""

# ── Hoberg_2024 (item 50) — Konzernanlagenspiegel, split across page-halves and
#    merged. NOTE: the "Grundstücke und Bauten" rows are EMPTY in the source
#    extraction (≈168 Mio fehlen laut Zwischensumme) — left blank, VERIFY vs PDF.
#    Two source glitches preserved verbatim: Immat.-Wechselkurs-Zwischensumme
#    "5.586,27" (statt -5.586,27) und Finanz-Beteiligung-Buchwert "5.158,55"
#    (statt 75.158,55). ─────────────────────────────────────────────────────────
CLEAN[50] = """\
Das Anlagevermögen und die Abschreibungen haben sich im Berichtsjahr wie folgt entwickelt:

## Konzernanlagenspiegel zum 31. Dezember 2024

| **Anschaffungs- / Herstellungskosten** | **Stand 31.12.2023 €** | **Wechselkursdifferenzen €** | **Stand 01.01.2024 €** | **Zugänge €** | **Umbuchungen €** | **Abgänge €** | **Stand 31.12.2024 €** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | | | |
| 1. Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 30.748.709,66 | -8.933,26 | 30.739.776,40 | 451.564,23 | 524.495,00 | 471.167,78 | 31.244.667,85 |
| 2. Geschäfts- oder Firmenwert | 48.746.800,88 | 0,00 | 48.746.800,88 | 1.474.627,97 | 0,00 | 0,00 | 50.221.428,85 |
| 3. Geleistete Anzahlungen | 627.267,78 | 0,00 | 627.267,78 | 160.967,95 | -524.495,00 | 40.732,66 | 223.008,07 |
| | 80.122.778,32 | -8.933,29 | 80.113.845,06 | 2.087.160,15 | 0,00 | 511.900,44 | 81.689.104,77 |
| II. Sachanlagen | | | | | | | |
| 1. Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | | | | | | | |
| 2. Technische Anlagen und Maschinen | 80.073.038,67 | 46.647,50 | 80.119.686,17 | 2.904.451,27 | 3.922.134,08 | 3.799.800,89 | 83.146.470,63 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 62.810.951,54 | 116.869,30 | 62.927.820,84 | 2.671.047,91 | 1.233.297,55 | 4.673.016,07 | 62.159.150,23 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 7.127.664,10 | -36.494,67 | 7.091.169,43 | 2.855.014,19 | -6.709.902,14 | 118.929,11 | 3.117.352,37 |
| | 318.048.327,93 | 1.072.713,88 | 319.121.041,81 | 8.733.867,93 | -518.545,10 | 15.136.265,29 | 312.200.099,35 |
| III. Finanzanlagen | | | | | | | |
| 1. Beteiligungen | 75.158,55 | 0,00 | 75.158,55 | 0,00 | 0,00 | 0,00 | 75.158,55 |
| 2. Sonstige Ausleihungen | 145.247,01 | 0,00 | 145.247,01 | 787,41 | 0,00 | 3.532,56 | 142.501,86 |
| | 220.405,56 | 0,00 | 220.405,56 | 787,41 | 0,00 | 3.532,56 | 217.660,41 |
| | 398.391.511,81 | 1.063.780,62 | 399.455.292,43 | 10.821.815,49 | -518.545,10 | 15.651.698,29 | 394.106.864,53 |

| **Wertberichtigungen** | **Stand 31.12.2023 €** | **Wechselkursdifferenzen €** | **Stand 01.01.2024 €** | **Abschreibungen des Geschäftsjahres €** | **Umbuchungen €** | **Abschreibungen auf Abgänge €** | **31.12.2024 €** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | | | |
| 1. Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 27.078.339,23 | -5.586,27 | 27.072.752,96 | 1.269.154,23 | 0,00 | 471.167,78 | 27.870.739,41 |
| 2. Geschäfts- oder Firmenwert | 29.401.448,98 | 0,00 | 29.401.448,98 | 3.187.051,04 | 0,00 | 0,00 | 32.588.500,02 |
| 3. Geleistete Anzahlungen | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| | 56.479.788,21 | 5.586,27 | 56.474.201,94 | 4.456.205,27 | 0,00 | 471.167,78 | 60.459.239,43 |
| II. Sachanlagen | | | | | | | |
| 1. Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | | | | | | | |
| 2. Technische Anlagen und Maschinen | 50.638.535,50 | 53.836,27 | 50.692.371,77 | 5.493.521,59 | -198.159,65 | 3.158.176,41 | 52.829.557,30 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 43.375.306,12 | 121.893,16 | 43.497.199,28 | 5.326.630,52 | 0,00 | 4.193.658,65 | 44.630.171,15 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| | 149.385.596,42 | 631.906,40 | 150.017.502,82 | 15.369.365,14 | -326.550,17 | 8.862.378,46 | 156.197.939,33 |
| III. Finanzanlagen | | | | | | | |
| 1. Beteiligungen | 70.000,00 | 0,00 | 70.000,00 | 0,00 | 0,00 | 0,00 | 70.000,00 |
| 2. Sonstige Ausleihungen | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| | 70.000,00 | 0,00 | 70.000,00 | 0,00 | 0,00 | 0,00 | 70.000,00 |
| | 205.935.384,63 | 626.320,13 | 206.561.704,76 | 19.825.570,41 | -326.550,17 | 9.333.546,24 | 216.727.178,76 |

| **Buchwerte** | **Stand 31.12.2024 €** | **Stand 31.12.2023 €** |
| --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | |
| 1. Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 3.373.928,44 | 3.670.370,43 |
| 2. Geschäfts- oder Firmenwert | 17.632.928,83 | 19.345.351,90 |
| 3. Geleistete Anzahlungen | 223.008,07 | 627.267,78 |
| | 21.229.865,34 | 23.642.990,11 |
| II. Sachanlagen | | |
| 1. Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | | |
| 2. Technische Anlagen und Maschinen | 30.316.913,33 | 29.434.503,17 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 17.528.979,08 | 19.435.645,42 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 3.117.352,37 | 7.127.664,10 |
| | 156.002.160,02 | 168.662.731,51 |
| III. Finanzanlagen | | |
| 1. Beteiligungen | 5.158,55 | 5.158,55 |
| 2. Sonstige Ausleihungen | 142.501,86 | 145.247,01 |
| | 147.660,41 | 150.405,56 |
| | 177.379.685,77 | 192.456.127,18 |"""

# ── Pfizer_2024 (item 102) — leading Bilanz-Aktiva excerpt (Einzel/Summe columns)
#    then the Anlagenspiegel (AHK split; value 14.438.943,29 was misplaced onto
#    the "I. Immaterielle" header line and moved into its row). ─────────────────
CLEAN[102] = """\
Aktiva

| **Aktiva** | **Anhang Ziffer** | **30.11.2024 EUR** | **EUR** | **30.11.2023 EUR** | **EUR** |
| --- | --- | --- | --- | --- | --- |
| A. Anlagevermögen | (1) | | | | |
| I. Immaterielle Vermögensgegenstände | | | | | |
| 1. Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | | 353.869,85 | | 1.551.505,32 | |
| 2. Geleistete Anzahlungen | | 4.915.178,85 | 5.269.048,70 | 4.070.149,32 | 5.621.654,64 |
| II. Sachanlagen | | | | | |
| 1. Bauten auf fremden Grundstücken | | 7.872.955,97 | | 40.808.376,41 | |
| 2. Technische Anlagen und Maschinen | | 3.031.741,97 | | 21.178.433,27 | |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | | 19.214.011,30 | | 15.041.787,70 | |
| 4. Geleistete Anzahlungen und Anlagen im Bau | | 217.609,83 | 30.336.319,07 | 4.744.583,35 | 81.773.180,73 |
| | | | 35.605.367,77 | | 87.394.835,37 |

Entwicklung des Anlagevermögens im Geschäftsjahr 2023/2024

| **Anschaffungskosten** | **1.12.2023 EUR** | **Zugänge EUR** | **Umbuchungen EUR** | **Abgänge EUR** | **30.11.2024 EUR** |
| --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | |
| 1. Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 14.879.618,02 | 226.164,20 | 11.348,64 | -678.187,57 | 14.438.943,29 |
| 2. Geschäfts- oder Firmenwert | 1.938.504,62 | 0,00 | 0,00 | 0,00 | 1.938.504,62 |
| 3. Geleistete Anzahlungen | 4.070.149,32 | 845.029,53 | 0,00 | 0,00 | 4.915.178,85 |
| | 20.888.271,96 | 1.071.193,73 | 11.348,64 | -678.187,57 | 21.292.626,76 |
| II. Sachanlagen | | | | | |
| 1. Bauten auf fremden Grundstücken | 65.916.047,62 | 236.942,13 | 1.395.933,05 | -28.998.604,01 | 38.550.318,79 |
| 2. Technische Anlagen und Maschinen | 37.649.489,23 | 133.123,51 | 1.479.283,77 | -18.746.906,73 | 20.514.989,78 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 33.512.761,84 | 9.871.664,84 | 1.858.017,89 | -8.065.562,26 | 37.176.882,31 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 4.744.583,35 | 217.609,83 | -4.744.583,35 | 0,00 | 217.609,83 |
| | 141.822.882,04 | 10.459.340,31 | -11.348,64 | -55.811.073,00 | 96.459.800,71 |
| | 162.711.154,00 | 11.530.534,04 | 0,00 | -56.489.260,57 | 117.752.427,47 |

| **Kumulierte Abschreibungen** | **1.12.2023 EUR** | **Zugänge EUR** | **Umbuchungen EUR** | **Abgänge EUR** | **30.11.2024 EUR** |
| --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | |
| 1. Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | -13.328.112,70 | -1.435.068,65 | -79,67 | 678.187,58 | -14.085.073,44 |
| 2. Geschäfts- oder Firmenwert | -1.938.504,62 | 0,00 | 0,00 | 0,00 | -1.938.504,62 |
| 3. Geleistete Anzahlungen | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| | -15.266.617,32 | -1.435.068,65 | -79,67 | 678.187,58 | -16.023.578,06 |
| II. Sachanlagen | | | | | |
| 1. Bauten auf fremden Grundstücken | -25.107.671,21 | -20.570.198,02 | 0,00 | 15.000.506,41 | -30.677.362,82 |
| 2. Technische Anlagen und Maschinen | -16.471.055,96 | -10.881.037,71 | 236,42 | 9.868.609,44 | -17.483.247,81 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | -18.470.974,14 | -6.934.655,52 | -156,75 | 7.442.915,40 | -17.962.871,01 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| | -60.049.701,31 | -38.385.891,25 | 79,67 | 32.312.031,25 | -66.123.481,64 |
| | -75.316.318,63 | -39.820.959,90 | 0,00 | 32.990.218,83 | -82.147.059,70 |

| **Buchwerte** | **30.11.2024 EUR** | **1.12.2023 EUR** |
| --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | |
| 1. Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 353.869,85 | 1.551.505,32 |
| 2. Geschäfts- oder Firmenwert | 0,00 | 0,00 |
| 3. Geleistete Anzahlungen | 4.915.178,85 | 4.070.149,32 |
| | 5.269.048,70 | 5.621.654,64 |
| II. Sachanlagen | | |
| 1. Bauten auf fremden Grundstücken | 7.872.955,97 | 40.808.376,41 |
| 2. Technische Anlagen und Maschinen | 3.031.741,97 | 21.178.433,27 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 19.214.011,30 | 15.041.787,70 |
| 4. Geleistete Anzahlungen und Anlagen im Bau | 217.609,83 | 4.744.583,35 |
| | 30.336.319,07 | 81.773.180,73 |
| | 35.605.367,77 | 87.394.835,37 |"""

# ── BoschMS_2024 (item 24) — opening balances were injected into wrapped labels
#    (e.g. "Schutz- 208.125,00 rechte") and moved into the "Stand 01.01.2024"
#    column; hyphenated label wraps rejoined. ──────────────────────────────────
CLEAN[24] = """\
| **Anschaffungs- bzw. Herstellungskosten** | **Stand am 01.01.2024 €** | **Zugänge €** | **Umbuchungen €** | **Abgänge €** | **Stand am 31.12.2024 €** |
| --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | |
| Entgeltlich erworbene gewerbliche Schutzrechte und ähnliche Rechte sowie Lizenzen an solchen Rechten | 555.000,00 | 0,00 | 0,00 | 0,00 | 555.000,00 |
| | 555.000,00 | 0,00 | 0,00 | 0,00 | 555.000,00 |
| II. Sachanlagen | | | | | |
| Andere Anlagen, Betriebs- und Geschäftsausstattung | 564,90 | 0,00 | 0,00 | 0,00 | 564,90 |
| | 564,90 | 0,00 | 0,00 | 0,00 | 564,90 |
| III. Finanzanlagen | | | | | |
| Anteile an verbundenen Unternehmen | 110.496,81 | 0,00 | 0,00 | 0,00 | 110.496,81 |
| | 110.496,81 | 0,00 | 0,00 | 0,00 | 110.496,81 |
| | 666.061,71 | 0,00 | 0,00 | 0,00 | 666.061,71 |

| **Kumulierte Abschreibungen** | **Stand am 01.01.2024 €** | **Zugänge €** | **Abgänge €** | **Stand am 31.12.2024 €** |
| --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | |
| Entgeltlich erworbene gewerbliche Schutzrechte und ähnliche Rechte sowie Lizenzen an solchen Rechten | 208.125,00 | 69.375,00 | 0,00 | 277.500,00 |
| | 208.125,00 | 69.375,00 | 0,00 | 277.500,00 |
| II. Sachanlagen | | | | |
| Andere Anlagen, Betriebs- und Geschäftsausstattung | 66,00 | 66,00 | 0,00 | 132,00 |
| | 66,00 | 66,00 | 0,00 | 132,00 |
| III. Finanzanlagen | | | | |
| Anteile an verbundenen Unternehmen | 0,00 | 0,00 | 0,00 | 0,00 |
| | 0,00 | 0,00 | 0,00 | 0,00 |
| | 208.191,00 | 69.441,00 | 0,00 | 277.632,00 |

| **Restbuchwerte** | **Stand am 31.12.2024 €** | **Stand am 31.12.2023 €** |
| --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | |
| Entgeltlich erworbene gewerbliche Schutzrechte und ähnliche Rechte sowie Lizenzen an solchen Rechten | 277.500,00 | 346.875,00 |
| | 277.500,00 | 346.875,00 |
| II. Sachanlagen | | |
| Andere Anlagen, Betriebs- und Geschäftsausstattung | 432,90 | 498,90 |
| | 432,90 | 498,90 |
| III. Finanzanlagen | | |
| Anteile an verbundenen Unternehmen | 110.496,81 | 110.496,81 |
| | 110.496,81 | 110.496,81 |
| | 388.429,71 | 457.870,71 |"""

# ── Schrott_2024 (item 115) — opening balances injected into labels; the
#    Abschreibungen + Buchwert columns were split across page-halves and merged. ─
CLEAN[115] = """\
ANLAGENSPIEGEL Schrott-Bosch GmbH Dettingen zum 31. Dezember 2024

| **Anschaffungs-/Herstellungskosten** | **Anfangswerte 01.01.2024 EUR** | **Zugänge EUR** | **Abgänge EUR** | **Endbestand 31.12.2024 EUR** |
| --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | |
| Sonstige immaterielle Vermögensgegenstände | 218.888,67 | 2.063,47 | 0,00 | 220.952,14 |
| II. Sachanlagen | | | | |
| 1. Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 15.905.156,82 | 157.712,95 | 267.900,00 | 15.794.969,77 |
| 2. Technische Anlagen und Maschinen | 12.898.324,97 | 0,00 | 0,00 | 12.898.324,97 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 4.287.124,55 | 358.222,16 | 68.425,53 | 4.576.921,18 |
| | 33.090.606,34 | 515.935,11 | 336.325,53 | 33.270.215,92 |
| III. Finanzanlagen | | | | |
| 1. Anteile an verbundenen Unternehmen | 480.055,00 | 4.546.182,57 | 0,00 | 5.026.237,57 |
| 2. Beteiligungen | 28.778,23 | 0,00 | 0,00 | 28.778,23 |
| 3. Sonstige Finanzanlagen | 745.034,06 | 0,00 | 0,00 | 745.034,06 |
| | 1.253.867,29 | 4.546.182,57 | 0,00 | 5.800.049,86 |
| | 34.563.362,30 | 5.064.181,15 | 336.325,53 | 39.291.217,92 |

| **Kumulierte Abschreibungen** | **Stand 01.01.2024 EUR** | **Geschäftsjahr EUR** | **Abgänge EUR** | **Zuschreibung EUR** | **Stand 31.12.2024 EUR** | **Buchwert 31.12.2024 EUR** |
| --- | --- | --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | | | |
| Sonstige immaterielle Vermögensgegenstände | 196.595,67 | 9.447,47 | 0,00 | 0,00 | 206.043,14 | 14.909,00 |
| II. Sachanlagen | | | | | | |
| 1. Grundstücke, grundstücksgleiche Rechte und Bauten einschließlich der Bauten auf fremden Grundstücken | 4.022.623,81 | 103.723,95 | 19.534,00 | 0,00 | 4.106.813,76 | 11.688.156,01 |
| 2. Technische Anlagen und Maschinen | 12.140.055,97 | 165.621,00 | 0,00 | 0,00 | 12.305.676,97 | 592.648,00 |
| 3. Andere Anlagen, Betriebs- und Geschäftsausstattung | 3.448.093,87 | 283.788,16 | 68.421,53 | 0,00 | 3.663.460,50 | 913.460,68 |
| | 19.610.773,65 | 553.133,11 | 87.955,53 | 0,00 | 20.075.951,23 | 13.194.264,69 |
| III. Finanzanlagen | | | | | | |
| 1. Anteile an verbundenen Unternehmen | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 5.026.237,57 |
| 2. Beteiligungen | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 28.778,23 |
| 3. Sonstige Finanzanlagen | 49.868,40 | 0,00 | 0,00 | 49.868,40 | 0,00 | 745.034,06 |
| | 49.868,40 | 0,00 | 0,00 | 49.868,40 | 0,00 | 5.800.049,86 |
| | 19.857.237,72 | 562.580,58 | 87.955,53 | 49.868,40 | 20.281.994,37 | 19.009.223,55 |"""

# ── HTG_2024 (item 37) — values 1.249.586,00 / 3.900.000,00 floated outside the
#    Buchwert table and were placed into their rows; one number (157.348.866,66)
#    was split across a "[...]" separator and rejoined (see ALLOW_ADDED). ───────
CLEAN[37] = """\
## Anlagenspiegel zum 31. Dezember 2024

| **Anschaffungs-, Herstellungskosten** | **01.01.2024 EUR** | **Zugänge EUR** | **Abgänge EUR** | **31.12.2024 EUR** |
| --- | --- | --- | --- | --- |
| A. Anlagevermögen | | | | |
| I. Immaterielle Vermögensgegenstände | | | | |
| 1. Selbst geschaffene gewerbliche Schutzrechte und ähnliche Rechte und Werte | 14.745.018,17 | 5.518.398,00 | 0,00 | 20.263.416,17 |
| 2. Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 277.699,70 | 0,00 | 0,00 | 277.699,70 |
| Summe Immaterielle Vermögensgegenstände | 15.022.717,87 | 5.518.398,00 | 0,00 | 20.541.115,87 |
| II. Sachanlagen | | | | |
| Andere Anlagen, Betriebs- und Geschäftsausstattung | 2.482.710,46 | 64.974,71 | 3.793,10 | 2.543.892,07 |
| Summe Sachanlagen | 2.482.710,46 | 64.974,71 | 3.793,10 | 2.543.892,07 |
| III. Finanzanlagen | | | | |
| 1. Anteile an verbundenen Unternehmen | 178.415.357,29 | 16.852.342,66 | 165.260,00 | 195.102.439,95 |
| 2. Ausleihungen an verbundene Unternehmen | 1.019.936,37 | 4.200.000,00 | 1.019.936,37 | 4.200.000,00 |
| Summe Finanzanlagen | 179.435.293,66 | 21.052.342,66 | 1.185.196,37 | 199.302.439,95 |
| Summe Anlagevermögen | 196.940.721,99 | 26.635.715,37 | 1.188.989,47 | 222.387.447,89 |

| **Kumulierte Abschreibung** | **01.01.2024 EUR** | **Abschreibung Geschäftsjahr EUR** | **Abgänge EUR** | **31.12.2024 EUR** |
| --- | --- | --- | --- | --- |
| I. Immaterielle Vermögensgegenstände | | | | |
| 1. Selbst geschaffene gewerbliche Schutzrechte und ähnliche Rechte und Werte | 5.153.805,50 | 2.820.826,99 | 0,00 | 7.974.632,49 |
| 2. Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 55.205,30 | 5.833,00 | 0,00 | 61.038,30 |
| Summe Immaterielle Vermögensgegenstände | 5.209.010,80 | 2.826.659,99 | 0,00 | 8.035.670,79 |
| II. Sachanlagen | | | | |
| Andere Anlagen, Betriebs- und Geschäftsausstattung | 1.065.355,46 | 232.491,68 | 3.541,07 | 1.294.306,07 |
| Summe Sachanlagen | 1.065.355,46 | 232.491,68 | 3.541,07 | 1.294.306,07 |
| III. Finanzanlagen | | | | |
| 1. Anteile an verbundenen Unternehmen | 22.086.427,00 | 5.047.000,00 | 0,00 | 27.133.427,00 |
| 2. Ausleihungen an verbundene Unternehmen | 0,00 | 300.000,00 | 0,00 | 300.000,00 |
| Summe Finanzanlagen | 22.086.427,00 | 5.347.000,00 | 0,00 | 27.433.427,00 |
| Summe Anlagevermögen | 28.360.793,26 | 8.406.151,67 | 3.541,07 | 36.763.403,86 |

| **Buchwert** | **31.12.2024 EUR** | **31.12.2023 EUR** |
| --- | --- | --- |
| A. Anlagevermögen | | |
| I. Immaterielle Vermögensgegenstände | | |
| 1. Selbst geschaffene gewerbliche Schutzrechte und ähnliche Rechte und Werte | 12.288.783,68 | 9.591.212,67 |
| 2. Entgeltlich erworbene Konzessionen, gewerbliche Schutzrechte und ähnliche Rechte und Werte sowie Lizenzen an solchen Rechten und Werten | 216.661,40 | 222.494,40 |
| Summe Immaterielle Vermögensgegenstände | 12.505.445,08 | 9.813.707,07 |
| II. Sachanlagen | | |
| Andere Anlagen, Betriebs- und Geschäftsausstattung | 1.249.586,00 | 1.417.355,00 |
| Summe Sachanlagen | 1.249.586,00 | 1.417.355,00 |
| III. Finanzanlagen | | |
| 1. Anteile an verbundenen Unternehmen | 167.969.012,95 | 156.328.930,29 |
| 2. Ausleihungen an verbundene Unternehmen | 3.900.000,00 | 1.019.936,37 |
| Summe Finanzanlagen | 171.869.012,95 | 157.348.866,66 |
| Summe Anlagevermögen | 185.624.044,03 | 168.579.928,73 |"""

ALLOW_ADDED[37] = {"157.348.866,66"}
