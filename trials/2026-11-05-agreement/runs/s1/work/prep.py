"""Build station-day table. Controller clock is UTC (verified: commute drop shifts 1h with DST); convert to America/Denver."""
import pandas as pd, numpy as np

def load_status(path):
    s = pd.read_csv(path)
    s['ts'] = pd.to_datetime(s['ts'])
    # DST glitches duplicate/miss readings on the controller; keep the last reading per (ts, station)
    s = s.drop_duplicates(['ts', 'station_id'], keep='last')
    loc = s['ts'].dt.tz_localize('UTC').dt.tz_convert('America/Denver')
    s['date'] = loc.dt.tz_localize(None).dt.normalize()
    s['hour'] = loc.dt.hour
    return s

def station_days(s, w, st):
    """One row per station-day (weekday). Features use readings at local hour <= 6; label uses local hours 7,8,9."""
    s = s.copy()
    # OFFLINE rows report 0 bikes; that is not a stockout, so treat as missing
    s.loc[s.status == 'OFFLINE', 'bikes_available'] = np.nan
    piv = s.pivot_table(index=['station_id', 'date'], columns='hour', values='bikes_available', aggfunc='last')
    off = s[s.status == 'OFFLINE'].groupby(['station_id', 'date']).size().rename('n_off')
    d = pd.DataFrame(index=piv.index)
    for h in (0, 3, 5, 6):
        d[f'b{h}'] = piv.get(h)
    d['y_min'] = piv[[7, 8, 9]].min(axis=1, skipna=True)
    d['y_n'] = piv[[7, 8, 9]].notna().sum(axis=1)
    d['y'] = (d['y_min'] <= 0).astype(float)
    d.loc[d['y_n'] < 3, 'y'] = np.nan  # window not fully observed (offline / missing): label unknown
    d['off_morning'] = piv[[5, 6]].isna().any(axis=1)
    d = d.reset_index()
    # capacity effective on the date
    st = st.sort_values('effective_from')
    d = d.sort_values('date')
    d = pd.merge_asof(d, st[['station_id', 'capacity', 'effective_from', 'district']].assign(
        effective_from=pd.to_datetime(st.effective_from)).sort_values('effective_from'),
        left_on='date', right_on='effective_from', by='station_id')
    d = d.sort_values(['station_id', 'date']).reset_index(drop=True)
    d['fill6'] = d['b6'] / d['capacity']
    d['dow'] = d['date'].dt.day_of_week
    d['month'] = d['date'].dt.month
    # history: previous days' outcomes only (shifted), known by 7am today
    g = d.groupby('station_id')
    d['prev_y'] = g['y'].shift(1)
    d['prev_ymin'] = g['y_min'].shift(1)
    d['rate14'] = g['y'].transform(lambda x: x.shift(1).rolling(14, min_periods=3).mean())
    d['rate60'] = g['y'].transform(lambda x: x.shift(1).rolling(60, min_periods=10).mean())
    d['b6_prev'] = g['b6'].shift(1)
    # weather observed through 06:00 local (no forecast available in the data)
    w = w.copy()
    w['ts_local'] = pd.to_datetime(w['ts_local'])
    w['temp_c'] = w['temp_c'].where(w['temp_c'] > -100)  # -999 sentinel
    w['date'] = w['ts_local'].dt.normalize(); w['h'] = w['ts_local'].dt.hour
    w6 = w[w.h == 6].set_index('date')['temp_c'].rename('temp6')
    rain = w[w.h <= 6].groupby('date')['rain_mm'].sum().rename('rain_to6')
    d = d.merge(w6, on='date', how='left').merge(rain, on='date', how='left')
    return d

def build(status_path, root='/tmp/pk-s1/data'):
    s = load_status(status_path)
    w = pd.read_csv(f'{root}/weather.csv'); st = pd.read_csv(f'{root}/stations.csv')
    return station_days(s, w, st)
