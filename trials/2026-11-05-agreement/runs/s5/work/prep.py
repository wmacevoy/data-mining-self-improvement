"""Build one row per (station, weekday) at the 7:00 America/Denver prediction point.
Reads only data/status.csv, stations.csv, weather.csv (never holdout/, never daily_features.csv)."""
import sys
import numpy as np, pandas as pd

def load(status_path, stations_path, weather_path):
    s = pd.read_csv(status_path, parse_dates=['ts'])
    n0 = len(s)
    s = s.drop_duplicates(['ts', 'station_id'])
    # ts is UTC (verified: commute dip lines up with 6-9am Denver only after conversion)
    loc = s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Denver')
    s['date'] = loc.dt.tz_localize(None).dt.normalize()
    s['hour'] = loc.dt.hour
    # OFFLINE rows report 0 bikes: that is "no reading", not a stockout
    s.loc[s.status == 'OFFLINE', 'bikes_available'] = np.nan
    b = s.pivot_table(index=['station_id', 'date'], columns='hour', values='bikes_available', aggfunc='first')
    b.columns = [f'b{h}' for h in b.columns]
    d = b.reset_index()
    d = d[d.date.dt.dayofweek < 5].copy()
    # target: reading of 0 bikes at 7, 8 or 9 local; unknown if no reading in the window
    w = d[['b7', 'b8', 'b9']]
    d['known'] = w.notna().any(axis=1)
    d['y'] = (w.min(axis=1) == 0).astype(int)
    # features: only readings strictly before 7:00 local
    d['bikes6'] = d.b6; d['bikes3'] = d.b3; d['bikes0'] = d.b0
    d['night_min'] = d[['b0','b1','b2','b3','b4','b5','b6']].min(axis=1)
    d['offline6'] = d.b6.isna().astype(int)
    st = pd.read_csv(stations_path, parse_dates=['effective_from']).sort_values('effective_from')
    d = d.sort_values('date')
    d = pd.merge_asof(d, st[['station_id','effective_from','capacity','district']], left_on='date',
                      right_on='effective_from', by='station_id')
    d['fill6'] = d.bikes6 / d.capacity
    wx = pd.read_csv(weather_path)
    wx.loc[wx.temp_c <= -900, 'temp_c'] = np.nan   # -999 sentinel
    wx['date'] = pd.to_datetime(wx.ts_local.str[:10]); wx['hour'] = wx.ts_local.str[11:13].astype(int)
    wx = wx[wx.hour <= 6]
    g = wx.groupby('date').agg(temp6=('temp_c', 'last'), rain_pre=('rain_mm', 'sum')).reset_index()
    d = d.merge(g, on='date', how='left')
    d['dow'] = d.date.dt.dayofweek; d['month'] = d.date.dt.month
    d = d.sort_values(['station_id', 'date'])
    # history: this station's past stockout rates, shifted so today is never included
    for k in (14, 60):
        d[f'rate{k}'] = d.groupby('station_id').y.transform(lambda x: x.where(d.loc[x.index,'known']).shift(1).rolling(k, min_periods=5).mean())
    d['dist_North'] = (d.district == 'North').astype(int); d['dist_East'] = (d.district == 'East').astype(int)
    return d, n0

if __name__ == '__main__':
    d, n0 = load('../data/status.csv', '../data/stations.csv', '../data/weather.csv')
    print('status rows', n0, '-> station-days', len(d), 'unknown target', (~d.known).sum())
    print(d.date.min(), d.date.max()); print(d.groupby(d.date.dt.to_period('Q')).y.agg(['mean','size']))
    print(d[['bikes6','temp6','rain_pre','rate14']].isna().mean())
    d.to_pickle('dev.pkl')
