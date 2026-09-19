"""
Zweck: Visualisiert die statistische Ausreisserkennung aus price_deviation.py und
       execution_delay.py. Preisabweichung: tatsaechlicher Kursverlauf je ISIN,
       rollierender Mittelwert und obere/untere Grenze, mit markierten Ausreissern.
       Ausfuehrungsverzoegerung: tatsaechliche Verzoegerung je Instrument Type,
       rollierender Mittelwert und obere Grenze, mit markierten Ausreissern.
       X-Achse (beide Diagramme): echte Ausfuehrungszeit (nicht Reihenfolge), damit
       die Steigung zwischen zwei Punkten die tatsaechliche Geschwindigkeit einer
       Preis- bzw. Verzoegerungsaenderung widerspiegelt. Achsengroesse bewusst fuer
       alle Diagramme konstant gehalten (kein individuelles Banking je ISIN): So
       bleibt die Volatilitaet zwischen verschiedenen Wertpapieren im selben Zeitraum
       objektiv vergleichbar - ein individuell angepasstes Seitenverhaeltnis wuerde
       diesen Vergleich verzerren.
Input: cleaned_orders_snapshot_20260912.csv (gleiche Datenbasis wie price_deviation.py
       und execution_delay.py)
Output: Diagramme (PNG-Dateien im Visualization-Ordner)
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv("../data/cleaned_orders_snapshot_20260912.csv", sep=";", decimal=",", encoding="utf-8-sig")

df = df[
    (df['Status'].isin(['Executed', 'Partially Executed'])) &
    (df['Eligible_For_Price_Check'] == 'Yes') &
    (df['Execution Price'].notna()) &
    (df['Execution Time'].notna())
].copy()

df['Execution Time'] = pd.to_datetime(df['Execution Time'], dayfirst=True)
df = df.sort_values('Execution Time').reset_index(drop=True)

df['rolling_mean_price'] = df.groupby('ISIN')['Execution Price'].transform(
    lambda x: x.shift(1).rolling(window=20, min_periods=5).mean()
)
df['rolling_std_price'] = df.groupby('ISIN')['Execution Price'].transform(
    lambda x: x.shift(1).rolling(window=20, min_periods=5).std()
)
df['upper_bound'] = df['rolling_mean_price'] + 2 * df['rolling_std_price']
df['lower_bound'] = df['rolling_mean_price'] - 2 * df['rolling_std_price']

is_valid = df['rolling_mean_price'].notna()
is_outside_bounds = (
    (df['Execution Price'] > df['upper_bound']) |
    (df['Execution Price'] < df['lower_bound'])
)
df['is_statistical_outlier'] = is_outside_bounds.where(is_valid, other=pd.NA).astype("boolean")    # Bis hierhin identisch zur Logik in price_deviation.py

isin_list = ['DE000BAS0726', 'DE0005810055', 'DE0008430026']

for target_isin in isin_list:
    chart_df = df[df['ISIN'] == target_isin].reset_index(drop=True)

    plt.figure(figsize=(14, 6))

    plt.plot(chart_df['Execution Time'], chart_df['Execution Price'], label='Execution Price', color='black', linewidth=1) # Preislinie: tatsaechlicher Ausfuehrungspreis
    plt.plot(chart_df['Execution Time'], chart_df['rolling_mean_price'], label='Rolling Mean', color='blue', linewidth=1) # Mittelwertlinie: rollierender Durchschnitt
    plt.fill_between(chart_df['Execution Time'], chart_df['lower_bound'], chart_df['upper_bound'], color='blue', alpha=0.15, label='±2 Std Dev')# Farbflaeche: Normalbereich (obere/untere Grenze)

    outlier_rows = chart_df[chart_df['is_statistical_outlier'] == True]
    plt.scatter(outlier_rows['Execution Time'], outlier_rows['Execution Price'], color='red', label='Flagged Outlier', zorder=5)# Farbflaeche: Normalbereich (obere/untere Grenze)

    plt.title(f'Price Deviation Detection - {target_isin}')
    plt.xlabel('Execution Time')
    plt.ylabel('Execution Price')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'../visualizations/price_deviation_{target_isin}.png')
    plt.close()

delay_df = pd.read_csv("../data/cleaned_orders_snapshot_20260912.csv", sep=";", decimal=",", encoding="utf-8-sig")

delay_df = delay_df[
    (delay_df['Status'].isin(['Executed', 'Partially Executed'])) &
    (delay_df['Order Type'] == 'Market Order') &
    (delay_df['MarketPhase'] == 'Continuous') &
    (delay_df['Timestamp'].notna()) &
    (delay_df['Execution Time'].notna())
].copy()

delay_df['Timestamp'] = pd.to_datetime(delay_df['Timestamp'], dayfirst=True)
delay_df['Execution Time'] = pd.to_datetime(delay_df['Execution Time'], dayfirst=True)
delay_df['Delay Seconds'] = (delay_df['Execution Time'] - delay_df['Timestamp']).dt.total_seconds()
delay_df = delay_df.sort_values('Execution Time').reset_index(drop=True)

window_by_type = {
    'Equity': 50,
    'Bond': 20,
    'Structured Product': 15,
    'ETF': 10
}
delay_df['rolling_mean_delay'] = np.nan
delay_df['rolling_std_delay'] = np.nan

for instrument_type, window in window_by_type.items():
    mask = delay_df['Instrument Type'] == instrument_type
    delay_df.loc[mask, 'rolling_mean_delay'] = delay_df.loc[mask, 'Delay Seconds'].shift(1).rolling(window=window, min_periods=5).mean()
    delay_df.loc[mask, 'rolling_std_delay'] = delay_df.loc[mask, 'Delay Seconds'].shift(1).rolling(window=window, min_periods=5).std()

delay_df['upper_bound_delay'] = delay_df['rolling_mean_delay'] + 2 * delay_df['rolling_std_delay']

is_valid = delay_df['rolling_mean_delay'].notna()
is_too_slow = delay_df['Delay Seconds'] > delay_df['upper_bound_delay']
delay_df['is_statistical_delay_outlier'] = is_too_slow.where(is_valid, other=pd.NA).astype("boolean")

target_type = 'Equity'
chart_delay_df = delay_df[delay_df['Instrument Type'] == target_type].reset_index(drop=True)

plt.figure(figsize=(14, 6))

plt.plot(chart_delay_df['Execution Time'], chart_delay_df['Delay Seconds'], label='Delay Seconds', color='black', linewidth=1)
plt.plot(chart_delay_df['Execution Time'], chart_delay_df['rolling_mean_delay'], label='Rolling Mean', color='blue', linewidth=1)
plt.fill_between(chart_delay_df['Execution Time'], 0, chart_delay_df['upper_bound_delay'], color='blue', alpha=0.15, label='Normal Range')

outlier_rows = chart_delay_df[chart_delay_df['is_statistical_delay_outlier'] == True]
plt.scatter(outlier_rows['Execution Time'], outlier_rows['Delay Seconds'], color='red', label='Flagged Outlier', zorder=5)

plt.title(f'Execution Delay Detection - {target_type}')
plt.xlabel('Execution Time')
plt.ylabel('Delay Seconds')
plt.legend()
plt.tight_layout()
plt.savefig(f'../visualizations/execution_delay_{target_type}.png')
plt.close()
