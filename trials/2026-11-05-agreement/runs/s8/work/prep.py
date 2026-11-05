"""Build one row per (station, weekday-local-date): features known at 07:00 local, label = stockout 7-9am local.
Usage: python -I prep.py DATA_DIR STATUS_FILE OUT.csv  (status file is a parameter so the holdout is never opened by accident)"""
import sys, pandas as pd, numpy as np
d, sf, out = sys.argv[1:4]
s = pd.read_csv(sf, parse_dates=['ts'])
# ts is UTC (overnight reset lands at 07:00 in Jan, 06:00 in Jul = local midnight)
s['ts'] = s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Denver').dt.tz_localize(None)
# DST-glitch duplicates (52 rows) : keep last
s = s.drop_duplicates(['ts','station_id'], keep='last')
s['date'] = s.ts.dt.normalize(); s['h'] = s.ts.dt.hour
s.loc[s.status=='OFFLINE','bikes_available'] = np.nan   # offline reports 0: not a real stockout
b = s.pivot_table(index=['station_id','date'], columns='h', values='bikes_available')
off = s[s.status=='OFFLINE'].groupby(['station_id','date']).size().rename('offline_n')
b = b.reindex(columns=range(24))
df = pd.DataFrame(index=b.index)
win = b[[7,8,9]]
df['y'] = (win.min(axis=1)==0).astype(float)
df.loc[win.isna().all(axis=1),'y'] = np.nan             # no valid reading in window
df['n_win_obs'] = win.notna().sum(axis=1)
df = df.reset_index()
# capacity as of date
st = pd.read_csv(f'{d}/stations.csv', parse_dates=['effective_from']).sort_values('effective_from')
df = pd.merge_asof(df.sort_values('date'), st[['station_id','district','capacity','effective_from']], left_on='date', right_on='effective_from', by='station_id')
b = b.reset_index()
for h in (0,3,5,6): df = df.merge(b[['station_id','date',h]].rename(columns={h:f'b{h}'}), on=['station_id','date'], how='left')
df = df.sort_values(['station_id','date'])
for c in ('b0','b3','b5','b6'): df[c+'_f'] = df[c]/df.capacity
# yesterday's evening / history, all before today's 00:00 local
dd = b.copy(); dd['pdate'] = dd.date + pd.Timedelta(days=1)
dd['prev_min_day'] = dd[list(range(7,24))].min(axis=1); dd['prev_b18']=dd[18]
df = df.merge(dd[['station_id','pdate','prev_min_day','prev_b18']].rename(columns={'pdate':'date'}), on=['station_id','date'], how='left')
df['yprev'] = df.groupby('station_id').y.shift(1)   # NB shift by row: gaps possible, checked below
df['gap'] = df.groupby('station_id').date.diff().dt.days
df.loc[df.gap!=1,'yprev'] = np.nan
g = df.groupby('station_id').y
df['rate28'] = g.transform(lambda x: x.shift(1).rolling(28, min_periods=7).mean())
df['rate_all'] = g.transform(lambda x: x.shift(1).expanding(min_periods=7).mean())
df['dow'] = df.date.dt.dayofweek
df['month'] = df.date.dt.month
# weather up to 06:00 local today, plus yesterday's rain; -999 sentinel -> NaN
w = pd.read_csv(f'{d}/weather.csv', parse_dates=['ts_local'])
w.loc[w.temp_c<=-99,'temp_c'] = np.nan
w['date']=w.ts_local.dt.normalize(); w['h']=w.ts_local.dt.hour
t6 = w[w.h==6].set_index('date').temp_c.rename('temp6')
r_prev = w.groupby('date').rain_mm.sum().shift(1, freq='D').rename('rain_prev_day')
r6 = w[w.h<=6].groupby('date').rain_mm.sum().rename('rain_to6')
df = df.merge(t6, left_on='date', right_index=True, how='left').merge(r_prev, left_on='date', right_index=True, how='left').merge(r6, left_on='date', right_index=True, how='left')
df['n_off_prev'] = 0
df = df[df.dow<5].drop(columns=['effective_from'])
df.to_csv(out, index=False)
print(len(df), df.y.isna().sum(), df.y.mean(), df.b6.isna().mean(), df.temp6.isna().mean())
