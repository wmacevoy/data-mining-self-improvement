"""Build one row per (station, weekday-morning): features known at 07:00 local, target = stockout in window."""
import pandas as pd, numpy as np
D='/tmp/pk-s6/data/'
def load_status(path):
    s=pd.read_csv(path,parse_dates=['ts'])
    # ts is controller clock = UTC (inferred: commute dip lands at 15/16h, tracks DST). Convert once, here.
    s['ts']=s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Denver')
    s=s.drop_duplicates(['ts','station_id'],keep='last')   # 52 DST-night duplicate rows
    return s
def load_weather():
    w=pd.read_csv(D+'weather.csv')
    w['ts']=pd.to_datetime(w.ts_local).dt.tz_localize('America/Denver',ambiguous='NaT',nonexistent='NaT')
    w=w.dropna(subset=['ts'])
    w.loc[w.temp_c<-100,'temp_c']=np.nan   # -999 sentinel
    return w.set_index('ts')
def capacity_asof():
    st=pd.read_csv(D+'stations.csv',parse_dates=['effective_from']).sort_values('effective_from')
    return st
def build(s):
    w=load_weather(); st=capacity_asof()
    s=s.copy(); s['date']=s.ts.dt.normalize(); s['h']=s.ts.dt.hour
    s=s[s.date.dt.dayofweek<5]
    ok=s.status=='OK'
    win=s[s.h.isin([7,8,9])]
    tgt=win.assign(zero=(win.bikes_available==0)&(win.status=='OK'),on=win.status=='OK').groupby(['station_id','date']).agg(y=('zero','max'),n_ok=('on','sum')).reset_index()
    tgt=tgt[tgt.n_ok>0]   # window fully offline: outcome unknown, drop (counted in report)
    piv=s[s.h<=6].pivot_table(index=['station_id','date'],columns='h',values='bikes_available',aggfunc='last')
    off=s[s.h<=6].assign(o=lambda d:d.status=='OFFLINE').pivot_table(index=['station_id','date'],columns='h',values='o',aggfunc='last')
    X=piv.copy(); X.columns=[f'b{h}' for h in X.columns]
    X['off6']=off[6].astype(float); X['off_any']=off.max(axis=1).astype(float)
    X=X.reset_index()
    X['b6']=X.b6.where(X.off6!=1)  # an OFFLINE 0 is not a real 0
    d=tgt.merge(X,on=['station_id','date'],how='left')
    # capacity as of date
    d=d.sort_values('date'); st=st.rename(columns={'effective_from':'date'})
    st['date']=st.date.dt.tz_localize('America/Denver')
    d=pd.merge_asof(d,st[['station_id','date','capacity','district']].sort_values('date'),on='date',by='station_id')
    d['fill6']=d.b6/d.capacity
    d['dow']=d.date.dt.dayofweek; d['month']=d.date.dt.month
    # prior-days history for the same station: stockout rate over previous 28 weekdays (shifted so no same-day info)
    d=d.sort_values(['station_id','date'])
    g=d.groupby('station_id')
    d['prev_y']=g.y.shift(1).astype(float)
    d['rate28']=g.y.transform(lambda x:x.shift(1).rolling(28,min_periods=5).mean())
    d['b6_mean28']=g.fill6.transform(lambda x:x.shift(1).rolling(28,min_periods=5).mean())
    # weather: observed up to 06:00 local
    wk=w.copy(); 
    t6=wk.temp_c.reindex(d.date+pd.DateOffset(hours=6)).values
    r=wk.rain_mm.rolling(6,min_periods=1).sum().reindex(d.date+pd.DateOffset(hours=6)).values
    d['temp6']=t6; d['rain6h']=r
    d['y']=d.y.astype(int)
    return d
