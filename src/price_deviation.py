"""
Zweck: Fuehrt einen Parameter-Sensitivitaetstest durch (Fenstergroesse 10/20/50, k=2/3) und erkennt dabei
       Ausfuehrungen, deren Preis mehr als k Standardabweichungen vom rollierenden Mittelwert (gruppiert
       nach ISIN) abweicht - dynamische Weiterentwicklung der im VBA-Projekt (Layer②/MonitorPriceDeviation)
       verwendeten festen 5%-Schwelle:
       [https://github.com/yingchao-dev/Client-Order-DataCleaning-Monitoring-RiskExposure-Tool/blob/main/01_Source_Code/03_OrderMonitoring.bas]
       Analog zur VBA-Version wird der aktuelle Wert beim Rolling-Window ausgeschlossen.
Input: cleaned_orders_snapshot_20260912.csv (Spalte ISIN, Execution Price, status, Execution Time,
       Eligible_For_Price_Check)
Output: DataFrame mit zusaetzlicher Spalte 'is_statistical_outlier_wXX_kY' fuer jede getestete
        Fenstergroesse-k-Kombination.
Bekannte Einschraenkung: Fenstergroesse und k-Wert sind empirisch plausible Standardwerte, nicht statistisch
        optimiert (keine Ground-Truth-Labels verfuegbar). Bei ISINs mit weniger als 5 vorherigen Ausfuehrungen
        (min_periods) kann noch kein rollierender Durchschnitt berechnet werden; diese Zeilen werden mit
        NA markiert und nicht bewertet. Interpretation der Spalte 'is_statistical_outlier_wXX_kY': Sie
        markiert Kandidaten fuer die manuelle Nachpruefung, keine bestaetigten Anomalien. Im Grenzfall std=0
        (keine Preisschwankung in der Historie) wird bereits jede minimale Abweichung markiert - eine bewusst
        hoch gewaehlte Sensitivitaet, um kein potenzielles Risiko zu uebersehen, kein Bug. Der Algorithmus dient
        als Vorfilter zur Priorisierung, nicht als abschliessende Entscheidungsinstanz - die endgueltige Bewertung
        obliegt den fachlich zustaendigen Mitarbeitenden.
"""
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 0)

df = pd.read_csv("../data/cleaned_orders_snapshot_20260912.csv", sep=";", decimal=",", encoding="utf-8-sig")

df = df[
    (df['Status'].isin(['Executed', 'Partially Executed'])) &
    (df['Eligible_For_Price_Check'] == 'Yes') &  # Hinweis: Die notna()-Filter auf Execution Price/Time sind eine Simulationsbedingte Notloesung - im echten Betrieb wuerden
    (df['Execution Price'].notna()) &            # fehlende Werte hier durch manuelle Nachbearbeitung/Korrektur geschlossen, was dieses Projekt (mangels echtem Backoffice-Prozess)
    (df['Execution Time'].notna())               # nicht abbilden kann. Zeilen mit fehlendem Price oder Time werden vorab entfernt, damit "Zeilenanzahl" und "Anzahl gueltiger
].copy()                                         # Datenpunkte" im nachfolgenden Rolling-Window stets uebereinstimmen und Execution Price und Execution Time in einer
print('Rows after filtering:', len(df))          # Eins-zu-eins-Beziehung stehen - so werden unkontrollierte Verzerrungen der Fensterstatistik durch fehlende Werte vermieden.

df['Execution Time'] = pd.to_datetime(df['Execution Time'], dayfirst=True)
df = df.sort_values('Execution Time').reset_index(drop=True)

def add_outlier_columns(df, window, k):
    suffix = f'w{window}_k{k}'
    mean_col = f'rolling_mean_price_w{window}'
    std_col = f'rolling_std_price_w{window}'

    if mean_col not in df.columns:                         # Berechnung nur beim ersten Aufruf je Fenstergroesse; weitere k-Werte greifen darauf zurueck.
        df[mean_col] = df.groupby('ISIN')['Execution Price'].transform(
            lambda x: x.shift(1).rolling(window=window, min_periods=5).mean()
        )
        df[std_col] = df.groupby('ISIN')['Execution Price'].transform(
            lambda x: x.shift(1).rolling(window=window, min_periods=5).std()
        )                                                          # Zwischenwerte (Mittelwert, Std, Grenzen) werden bewusst als eigene Spalten
                                                                   # gespeichert statt nur temporaer verwendet, damit bei erkannten Ausreissern
    df[f'upper_bound_{suffix}'] = df[mean_col] + k * df[std_col]   # nachvollziehbar bleibt, warum sie als solche eingestuft wurden. Bei deutlich
    df[f'lower_bound_{suffix}'] = df[mean_col] - k * df[std_col]   # mehr Kombinationen wuerde die Spaltenanzahl jedoch stark anwachsen.

    is_valid = df[mean_col].notna()               # is_valid = True bedeutet ausreichende Historie vorhanden (unabhaengig vom Ausreisser-Status)
    is_outside_bounds = (
            (df['Execution Price'] > df[f'upper_bound_{suffix}']) |
            (df['Execution Price'] < df[f'lower_bound_{suffix}'])
    )
    df[f'is_statistical_outlier_{suffix}'] = is_outside_bounds.where(is_valid, other=pd.NA).astype("boolean")
    return df                                                    # is_outside_bounds trennt mit .where(is_valid, other=pd.NA) zwei vormals identische
                                                                 # False-Werte: echtes False (Preis unauffaellig) von False durch fehlende Datenbasis
for window in [10, 20, 50]:                                      # (jetzt korrekt als NA-Platzhalter markiert). df[f'is_statistical_outlier_{suffix}']
    for k in [2, 3]:                                             # enthaelt fuer alle 1020 nach der Vorfilterung verbliebenen Ausfuehrungspreise
        df = add_outlier_columns(df, window=window, k=k)         # jeweils True, False oder NA.

print("\n=== Outlier count per combination ===")
for window in [10, 20, 50]:
    for k in [2, 3]:
        col = f'is_statistical_outlier_w{window}_k{k}'
        n_outliers = df[col].sum()              # sum() zaehlt keine Zeilen, sondern addiert True(+1) und False(0); NA wird automatisch uebersprungen
                                                # ergibt hier je Parameterkombination (von 6) die Anzahl der Ausreisser.
        n_valid = df[col].notna().sum()         # Zaehlt Zeilen mit echtem True/False (NA ausgeschlossen) - also tatsaechlich bewertete Ausfuehrungspreise.
        print(f"window={window}, k={k}: {n_outliers} of {n_valid} valid rows")
"""
Fazit der Parameter-Sensitivitaetstests (Fenstergroesse 10/20/50, k=2/3): Die Anzahl markierter Ausreisser
sinkt tendenziell mit groesserer Fenstergroesse und groesserem k (von 78 bei window=10/k=2 bis 30 bei
window=20/k=3, bei 853 bewertbaren Zeilen). Welche Kombination "richtig" ist, gibt es nicht - das haengt vom
Anwendungsfall ab: eine sensiblere Einstellung (kleines Fenster, k=2) erfasst mehr potenzielle Faelle bei
hoeherer Fehlalarmquote, eine konservativere Einstellung (grosses Fenster, k=3) reduziert Fehlalarme.
Letzteres birgt jedoch ein eigenes Risiko: Ein grosses Fenster stuetzt sich auf weit zurueckliegende Daten,
wodurch der Referenzwert traege auf echte Verschiebungen im Preisverhalten reagiert (Lag-Effekt) - eine
aktuell tatsaechlich auffaellige Ausfuehrung koennte so uebersehen werden, weil sie an einem veralteten,
kuenstlich geglaetteten Massstab gemessen wird. Selbst bei identischem Datensatz fuehren unterschiedliche
Zwecke und Marktbedingungen zu unterschiedlichen sinnvollen Parametern - die Wahl ist nicht durch die Daten
allein festgelegt. In Grenzfaellen koennten zusaetzliche oder andere Parameter noetig werden. Ausserdem
haengen die Ergebnisse somit nicht allein vom gewaehlten Fensterparameter ab, sondern ebenso von der
verfuegbaren Datenmenge je ISIN: Bei begrenzter Historie erreicht ein grosses Fenster fuer viele ISINs nie
seine volle Groesse, und der Referenzwert stuetzt sich dann auf saemtliche bisher vorliegenden Ausfuehrungen
dieser ISIN, da keine aelteren Daten mehr ausgeschlossen werden koennen.
"""
