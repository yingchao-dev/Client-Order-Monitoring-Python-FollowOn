"""
Zweck: Erkennt Marktauftraege, deren Ausfuehrungsverzoegerung (Execution Time minus Timestamp)
       mehr als 2 Standardabweichungen vom rollierenden Mittelwert (gruppiert nach Instrument Type,
       Fenstergroesse je Kategorie unterschiedlich: Equity=50, Bond=20, Structured Product=15,
       ETF=10) abweicht - Weiterentwicklung der in Layer② (VBA-Projekt MonitorExecutionDelay)
       verwendeten festen, nach Instrument Type gestaffelten Zeitschwelle.
       [https://github.com/yingchao-dev/Client-Order-DataCleaning-Monitoring-RiskExposure-Tool/blob/main/01_Source_Code/03_OrderMonitoring.bas].
       Analog zur Preisabweichung wird der aktuelle Wert beim Rolling-Window ausgeschlossen.
       Nur Marktauftraege werden bewertet, da bei Limitauftraegen die Wartezeit bis zum Erreichen
       des Limitpreises keine Systemverzoegerung darstellt.
Input: cleaned_orders_snapshot_20260912.csv (Spalte Instrument Type, Timestamp, Execution
       Time, Status, Order Type)
Output: DataFrame mit zusaetzlicher Spalte 'is_statistical_delay_outlier'
Bekannte Einschraenkung: Fenstergroesse je Instrument Type ist empirisch anhand der verfuegbaren
        Datenmenge gewaehlt (deutlich kleiner als die jeweilige Gesamtzahl), nicht statistisch
        optimiert. Bei Instrument Types mit weniger als 5 vorherigen Ausfuehrungen (min_periods)
        kann noch kein rollierender Durchschnitt berechnet werden; diese Zeilen werden als NA
        markiert und nicht bewertet.
"""
import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 0)

df = pd.read_csv("../data/cleaned_orders_snapshot_20260912.csv", sep=";", decimal=",", encoding="utf-8-sig")
                                                                # pd.read_csv gibt grundsaetzlich immer den Typ DataFrame zurueck; echte Leerstellen
df = df[                                                        # in der Rohdatei werden beim Einlesen automatisch mit einem Platzhalter (NaN) befuellt.
    (df['Status'].isin(['Executed', 'Partially Executed'])) &
    (df['Order Type'] == 'Market Order') &       # Jede Klammer ist eine Bedingung (True/False je Zeile);
    (df['Timestamp'].notna()) &                  # df[...] darum filtert danach die Zeilen.
    (df['MarketPhase'] == 'Continuous') &
    (df['Execution Time'].notna())
].copy()                                         # .copy() ist ab Pandas 3.0 (Copy-on-Write) nicht mehr zwingend, dient hier aber der Klarheit.
print("Rows after filtering:", len(df))

df['Timestamp'] = pd.to_datetime(df['Timestamp'], dayfirst=True)           # Bei diesem Datensatz ist die Datumsspalte die einzige, die nach dem Einlesen noch
df['Execution Time'] = pd.to_datetime(df['Execution Time'], dayfirst=True) # konvertiert werden muss (Zahlen/Booleans werden automatisch erkannt, der Rest bleibt str).
df['Delay Seconds'] = (df['Execution Time'] - df['Timestamp']).dt.total_seconds()
df = df.sort_values('Execution Time').reset_index(drop=True)

window_by_type = {
    'Equity': 50,
    'Bond': 20,
    'Structured Product': 15,
    'ETF': 10
}
df['rolling_mean_delay'] = np.nan  # DataFrames erlauben keine leeren Spalten (Struktur erfordert einen Wert pro Zeile, bedingt durch die zugrunde liegende
df['rolling_std_delay'] = np.nan   # numpy-Array-Struktur) - np.nan fuellt daher vorab jede Zeile und legt gleichzeitig den Spaltentyp auf float64 fest.
                                   # Theoretisch nicht zwingend: Die Spaltennamen koennten auch erst in der Schleife unten, beim ersten Befuellen, implizit festgelegt werden.

for instrument_type, window in window_by_type.items():     # Schleife ueber ein Dictionary (dict): .items() gibt bei jedem Durchlauf
    mask = df['Instrument Type'] == instrument_type        # Schluessel (instrument_type) und Wert (window) gemeinsam zurueck.
    df.loc[mask, 'rolling_mean_delay'] = df.loc[mask, 'Delay Seconds'].shift(1).rolling(window=window, min_periods=5).mean()
    df.loc[mask, 'rolling_std_delay'] = df.loc[mask, 'Delay Seconds'].shift(1).rolling(window=window, min_periods=5).std()
                                                                    # .shift(1) verschiebt anhand der tatsaechlichen Position innerhalb der gefilterten Reihe，
                                                                    # nicht anhand der (nach dem Filtern luecken-behafteten) urspruenglichen Indexnummern
df['upper_bound_delay'] = df['rolling_mean_delay'] + 2 * df['rolling_std_delay']
                                                                # k=2 statt 3: Die tatsaechlich riskanten Faelle fallen selten exakt in den engsten
is_valid = df['rolling_mean_delay'].notna()                     # Bereich, daher bewusst breiter gefasst, um sie nicht zu uebersehen.
is_too_slow = df['Delay Seconds'] > df['upper_bound_delay'] # Zahl vs NaN (>/<): Ergebnis ist immer False, nie NaN - IEEE-754-Standard.
df['is_statistical_delay_outlier'] = is_too_slow.where(is_valid, other=pd.NA).astype("boolean")
                                                                   # Feste Regel von.where(): Wo die Bedingung erfuellt ist, bleibt der urspruengliche Wert
                                                                   # erhalten; wo nicht, wird er durch den bei other angegebenen Wert ersetzt.
print("\n=== Delay outlier count per Instrument Type ===")         # Alternative: Grossgeschriebenes Float64 ab Beginn der Kette wuerde.where() ueberfluessig
for instrument_type in window_by_type:                             # machen (NA bleibt automatisch erhalten)
    mask = df['Instrument Type'] == instrument_type
    n_outliers = df.loc[mask, 'is_statistical_delay_outlier'].sum()
    n_valid = df.loc[mask, 'is_statistical_delay_outlier'].notna().sum()
    print(f"{instrument_type}: {n_outliers} of {n_valid} valid rows")

"""
Abschliessende Bemerkung: Sowohl diese Datei als auch price_deviation.py verwenden
ausschliesslich .shift(1) + rollierende Fenster auf bereits vergangenen Daten - im
Gegensatz zur VBA-Version, die den gesamten Datensatz (inkl. zukuenftiger Werte)
einbezieht. Beide Python-Implementierungen sind dadurch grundsaetzlich fuer eine
Echtzeitueberwachung einsetzbar, auch wenn sie hier als Batch-Analyse auf einem
statischen Snapshot laufen - waehrend die VBA-Methode aufgrund ihrer In-Sample-
Berechnung strukturell auf nachtraegliche Pruefung beschraenkt bleibt.
"""