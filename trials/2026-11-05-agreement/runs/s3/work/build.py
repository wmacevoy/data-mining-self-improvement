"""Raw -> one row per (station, weekday) with 7:00 local features and the 7-9am stockout label.
status.csv ts is UTC (verified: restock/commute jumps shift 1h at US DST dates), so convert."""
import pandas as pd, numpy as np
D='/tmp/pk-s3/data/'
def load_status(path):
    s=pd.read_csv(path,parse_dates=['ts'])
    n0=len(s); s=s.drop_duplicates(['ts','station_id'],keep='last')  # 52 DST-day duplicate rows
    s['l']=s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Denver').dt.tz_localize(None)
    s['date']=s.l.dt.normalize(); s['hr']=s.l.dt.hour
    return s
def build(status_path=D+'status.csv'):
    s=load_status(status_path)
    st=pd.read_csv(D+'stations.csv',parse_dates=['effective_from'])
    w=pd.read_csv(D+'weather.csv',parse_dates=['ts_local'])
    w.loc[w.temp_c==-999,'temp_c']=np.nan  # sentinel
    w=w.set_index('ts_local')
    rb=pd.read_csv(D+'rebalancing_log.csv',parse_dates=['ts'])
    # OFFLINE reads 0 bikes: unknown, not empty
    s.loc[s.status=='OFFLINE','bikes_available']=np.nan
    p=s.pivot_table(index=['station_id','date'],columns='hr',values='bikes_available',dropna=False)
    ok=s.pivot_table(index=['station_id','date'],columns='hr',values='status',aggfunc='first')
    rows=p[[h for h in range(0,10)]].copy(); rows.columns=[f'b{h}' for h in rows.columns]
    rows=rows.reset_index()
    rows=rows[rows.date.dt.dayofweek<5].copy()
    rows=rows.sort_values(['station_id','date'])
    # label: observed zero at 8:00 or 9:00 (7:00 itself is known at decision time but a 7am empty still needs restocking; include it)
    obs=rows[['b7','b8','b9']]
    rows['label']=(obs.min(axis=1)==0).astype(float)
    rows.loc[obs.isna().all(axis=1),'label']=np.nan   # label unknown: drop
    # features known at 7:00 local
    rows['b7f']=rows.b7.fillna(rows.b6)  # offline at 7 -> last read
    rows['off7']=rows.b7.isna().astype(int)
    rows['b6f']=rows.b6; rows['d1']=rows.b7f-rows.b5
    g=rows.groupby('station_id')
    rows['prev_label']=g.label.shift(1)           # yesterday's morning outcome, known by today 7:00
    rows['prev_min']=g[['b7','b8','b9']].transform(lambda x:x).min(axis=1).groupby(rows.station_id).shift(1)
    # capacity as of date
    st=st.sort_values('effective_from')
    rows=pd.merge_asof(rows.sort_values('date'),st[['station_id','capacity','effective_from','district']],left_on='date',right_on='effective_from',by='station_id')
    rows['fill']=rows.b7f/rows.capacity
    rows['dow']=rows.date.dt.dayofweek; rows['month']=rows.date.dt.month
    # weather at 7:00 local and last 24h rain (all before decision)
    w7=w.reindex(rows.date+pd.Timedelta(hours=7))
    rows['temp7']=w7.temp_c.values; rows['rain7']=w7.rain_mm.values
    r24=w.rain_mm.rolling(24,min_periods=1).sum().reindex(rows.date+pd.Timedelta(hours=7)); rows['rain24']=r24.values
    # restock last evening (log ts local, 16-19h) known by morning
    rb['d']=rb.ts.dt.normalize()
    key=set(zip(rb.station_id,rb.d))
    rows['restocked_prev']=[ (a,d-pd.Timedelta(days=1)) in key or (a,d-pd.Timedelta(days=3)) in key and d.dayofweek==0 for a,d in zip(rows.station_id,rows.date)]
    rows['restocked_prev']=rows.restocked_prev.astype(int)
    return rows.sort_values(['date','station_id']).reset_index(drop=True)
if __name__=='__main__':
    r=build(); print(len(r),r.label.isna().sum(),r.label.mean()); print(r.describe().T.to_string())
    r.to_pickle('/tmp/pk-s3/work/dev.pkl')
