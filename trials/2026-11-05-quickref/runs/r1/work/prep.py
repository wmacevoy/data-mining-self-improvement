"""Shared pure functions: build station-day table (label + features known at 07:00 local).
Assumption (K4, evidenced by diurnal restock jump): status.ts is UTC; local = America/Denver."""
import pandas as pd, numpy as np
TZ='America/Denver'
def load_status(path):
    s=pd.read_csv(path,parse_dates=['ts'])
    n0=len(s)
    s=s.drop_duplicates(['ts','station_id'],keep='first')  # DST-day dupes, conflicting values; keep first
    s['loc_ts']=s.ts.dt.tz_localize('UTC').dt.tz_convert(TZ).dt.tz_localize(None)
    s['date']=s.loc_ts.dt.normalize(); s['hr']=s.loc_ts.dt.hour
    return s
def stations(path):
    st=pd.read_csv(path,parse_dates=['effective_from']).sort_values('effective_from')
    return st
def build(s,st,w):
    ok=s.status=='OK'
    # label: any OK reading with 0 bikes at local 07,08,09
    win=s[s.hr.isin([7,8,9])]
    g=win.groupby(['station_id','date'])
    lab=pd.DataFrame({'n_ok':g.apply(lambda d:(d.status=='OK').sum()),
                      'stockout':g.apply(lambda d:int(((d.status=='OK')&(d.bikes_available==0)).any()))}).reset_index()
    lab.loc[lab.n_ok==0,'stockout']=np.nan   # no observation => unknown, not 0
    # features at/before 06:00 local reading (decision lead), OK readings only
    pre=s[ok&(s.hr<=6)]
    f6=pre[pre.hr==6][['station_id','date','bikes_available']].rename(columns={'bikes_available':'b06'})
    f0=pre[pre.hr==0][['station_id','date','bikes_available']].rename(columns={'bikes_available':'b00'})
    f3=pre[pre.hr==3][['station_id','date','bikes_available']].rename(columns={'bikes_available':'b03'})
    d=lab.merge(f6,how='left',on=['station_id','date']).merge(f0,how='left',on=['station_id','date']).merge(f3,how='left',on=['station_id','date'])
    assert len(d)==len(lab)
    # history: previous days' window outcomes (shifted so only past), per station
    d=d.sort_values(['station_id','date']).reset_index(drop=True)
    gg=d.groupby('station_id')
    d['prev_so']=gg.stockout.shift(1)
    # previous-day stockout rate over trailing 28 *calendar-ordered rows* excluding today
    d['so_rate28']=gg.stockout.transform(lambda x:x.shift(1).rolling(28,min_periods=7).mean())
    d['so_rate7']=gg.stockout.transform(lambda x:x.shift(1).rolling(7,min_periods=3).mean())
    # previous afternoon trough (yesterday's 13-17 local min) known by 7am
    aft=s[ok&s.hr.between(13,17)].groupby(['station_id','date']).bikes_available.min().rename('aft_min').reset_index()
    aft['date']=aft.date+pd.Timedelta(days=1)
    d=d.merge(aft,how='left',on=['station_id','date'])
    # capacity as-of date
    cap=pd.merge_asof(d.sort_values('date'),st[['station_id','capacity','effective_from','district']].sort_values('effective_from'),left_on='date',right_on='effective_from',by='station_id',direction='backward')
    d=cap.drop(columns='effective_from')
    d['b06_frac']=d.b06/d.capacity; d['b00_frac']=d.b00/d.capacity
    # weather at 06:00 local (known), forecast not available => use observed 06:00
    w=w.copy(); w.loc[w.temp_c<-100,'temp_c']=np.nan
    w['ts_local']=pd.to_datetime(w.ts_local); w['date']=w.ts_local.dt.normalize()
    w6=w[w.ts_local.dt.hour==6][['date','temp_c','rain_mm']]
    d=d.merge(w6,how='left',on='date')
    d['dow']=d.date.dt.dayofweek; d['month']=d.date.dt.month
    return d.sort_values(['date','station_id']).reset_index(drop=True)
FEATS=['b06','b00','b03','b06_frac','capacity','prev_so','so_rate28','so_rate7','aft_min','temp_c','rain_mm','dow','month']
