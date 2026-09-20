# Python Execution Quality Project — README

*Statistische Weiterentwicklung von Layer② des VBA-Projekts*

**Autor:** Yingchao Li

**Stand:** 25.09.2026

**Struktur:** 3 unabhaengige Module (price_deviation / execution_delay / visualization), keine feste Ausfuehrungsreihenfolge

Dieses Projekt verwendet die bereinigten Daten aus `Cleaned_Data` (Layer ① des VBA-Projekts) als Eingabedatenquelle. Der Fokus liegt auf einer statistisch vertieften Behandlung der festen Schwellenwertmethoden aus der VBA-Regelueberwachungsschicht (Layer ②) — konkret der Preisabweichungsschwelle von 5% sowie der nach Instrumententyp gestaffelten Ausfuehrungsverzoegerungsschwellen —, wobei die urspruenglich statischen Regeln durch dynamische Baselines auf Basis gleitender Fenster (rolling window) und adaptive, standardabweichungsbasierte Schwellenwerte ersetzt werden.

## Wichtige Dateien

| Ordner/Datei | Inhalt |
|---|---|
| `data/` | Fixe CSV-Momentaufnahme von `Cleaned_Data` (Layer① des VBA-Projekts). |
| `src/price_deviation.py` | Statistische Vertiefung der Preisabweichungsschwelle je ISIN mittels Rolling Window und k-facher Standardabweichung, inkl. Parameter-Sensitivitaetstests (Fenstergroesse 10/20/50, k=2/3) |
| `src/execution_delay.py` | Statistische Vertiefung der nach Instrumententyp gestaffelten Ausfuehrungsverzoegerungsschwelle mittels instrumentenspezifischer Rolling-Window-Groessen |
| `src/visualization.py` | Generierung der Diagramme in `analysis/visualizations/` zur Veranschaulichung der Schwellenwert-Logik |
| `analysis/findings.md` | Aus den Diagrammen abgeleitete methodische Erkenntnisse, die ueber die reinen Tabellendaten hinausgehen (Masking-Effekt, Cold-Start-Blind-Spot) |
| `analysis/visualizations/` | Die in `findings.md` referenzierten Diagramme |

## Lokale Ausfuehrung

1. Es sollte der gesamte Ordner heruntergeladen werden (nicht einzelne Dateien), da die Skripte ueber relative Pfade auf die Daten in `data/` zugreifen. Beim Herunterladen nur einzelner Dateien wird `data/` nicht gefunden und es kommt zu einem Fehler.
2. Zum Ausfuehren werden Python sowie die Bibliotheken pandas, numpy und matplotlib benoetigt. Bei bevorzugter Installation ueber die Kommandozeile optional: `pip install -r requirements.txt`
3. Bei Ausfuehrung ueber die Kommandozeile muss zunaechst in den Ordner `src/` gewechselt werden, danach das Skript ausfuehren, z. B.:

```
cd src
python price_deviation.py
```

## Warum Python?

VBA koennte die rollierenden Fenster und Standardabweichungsberechnungen durchaus manuell mittels Schleifen umsetzen, doch diese Implementierung waere entwicklungsineffizient, fehleranfaellig und liesse sich nur schwer auf nachfolgende Visualisierungen und komplexere statistische Methoden erweitern. Die Entscheidung, diese Schicht in Python neu zu implementieren, dient einerseits dazu, mittels etablierter Werkzeuge wie pandas die kognitive Last von der Frage "wie wird es umgesetzt" hin zur "Gestaltung der fachlichen Logik" zu verlagern, und andererseits dazu, sich an den in der vektorisierten Datenanalyse etablierten Standard-Werkzeugstack anzunaehern.

Der Unterschied zwischen der VBA- und der Python-Implementierung liegt nicht nur in der Schwellenwertmethode (statisch vs. dynamisch), sondern in der grundlegenden Analyseperspektive: Die VBA-Version berechnet den Referenzwert unter Einbeziehung des gesamten historischen Datensatzes (In-Sample / retrospektive Analyse) und eignet sich daher fuer eine nachtraegliche Pruefung. Die Python-Version verwendet ausschliesslich Daten, die zum Zeitpunkt der jeweiligen Ausfuehrung bereits vorlagen (Out-of-Sample / Echtzeit-Perspektive) und bildet damit realistischer ab, wie eine tatsaechliche Ueberwachung im Handelsbetrieb funktionieren wuerde, bei der zukuenftige Daten naturgemaess nicht verfuegbar sind.

Das bedeutet jedoch nicht, dass der im VBA-Projekt gewaehlte Ansatz dem Python-Ansatz unterlegen ist. Die feste Schwellenwertmethode hat naemlich einen klaren Vorteil — eine extrem kurze Cold-Start-Phase: Bereits ab der zweiten Ausfuehrung je Wertpapier steht ein referenzierbarer historischer Basiswert zur Verfuegung. Zwar passt sich die Schwelle nicht an das tatsaechliche Niveau der einzelnen Wertpapiere an, doch es gibt so gut wie keine "durchzustehende" Leerlaufphase. Die rollierende Schwellenwertmethode im Python-Projekt verhaelt sich genau umgekehrt: Da erst ab mindestens 5 vorherigen Ausfuehrungen ueberhaupt ein Basiswert berechnet wird, befinden sich von den 1020 in der Praxis bewerteten gueltigen Datenpunkten ueber 160 Ausfuehrungen im Preisabweichungs-Experiment in dieser Cold-Start-bedingten "nicht bewertbaren" Risikozone — ein nicht unerheblicher Anteil. Im Gegenzug gewinnt man dadurch Adaptivitaet und Flexibilitaet, doch der Preis dafuer ist ebenso deutlich: eine laengere und risikobehaftetere Cold-Start-Phase. Beide Methoden eignen sich daher fuer unterschiedliche Einsatzszenarien — in der Praxis stehen sie meist nicht in Konkurrenz zueinander, sondern ergaenzen sich gegenseitig.
