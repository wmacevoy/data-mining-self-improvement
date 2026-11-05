"""Build station-day table. Controller ts is UTC-like (fixed offset); local = US Eastern (inferred from
demand shift on 2025-03-09 / 2025-11-02 / 2026-03-08). Label window: local 07:00-09:00 readings."""
import pandas as pd, numpy as np, sys
D='/tmp/pk-r5/data/'
def load_status(path):
    s=pd.read_csv(path,parse_dates=['ts'])
    s=s.drop_duplicates(['ts','station_id'],keep='last')   # DST-day duplicates
    s['loc_t']=s.ts.dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.tz_localize(None)
    return s
def build(path):
    s=load_status(path)
    st=pd.read_csv(D+'stations.csv',parse_dates=['effective_from']).sort_values('effective_from')
    s=s.sort_values('loc_t')
    s=pd.merge_asof(s,st[['station_id','district','capacity','effective_from']],left_on='loc_t',right_on='effective_from',by='station_id')
    s['date']=s.loc_t.dt.normalize();s['h']=s.loc_t.dt.hour
    s=s[s.date.dt.dayofweek<5]
    w=s[s.h.isin([7,8,9])]
    lab=w.groupby(['station_id','date']).apply(lambda g:pd.Series({
        'n_win':len(g),'n_off':(g.status!='OK').sum(),
        'y':int(((g.status=='OK')&(g.bikes_available==0)).any())}),include_groups=False).reset_index()
    # features known at 06:00 local
    f=s[s.h==6][['station_id','date','bikes_available','status','capacity','district']].rename(columns={'bikes_available':'b6','status':'st6'})
    f5=s[s.h==5][['station_id','date','bikes_available','status']].rename(columns={'bikes_available':'b5','status':'st5'})
    f=f.merge(f5,on=['station_id','date'],how='left')
    d=lab.merge(f,on=['station_id','date'],how='left')
    return d
def add_feats(d,w):
    d=d.sort_values(['station_id','date']).copy()
    d['b6f']=d.b6/d.capacity
    d.loc[d.st6!='OK',['b6','b6f']]=np.nan
    d['dow']=d.date.dt.dayofweek;d['month']=d.date.dt.month
    # previous-days outcome (known by 07:00 today); use strictly earlier rows, skip unknown
    yy=d.y.where(d.n_off==0)
    g=yy.groupby(d.station_id)
    d['y_prev1']=g.shift(1)
    d['y_roll14']=g.transform(lambda x:x.shift(1).rolling(14,min_periods=3).mean())
    d['y_roll60']=g.transform(lambda x:x.shift(1).rolling(60,min_periods=10).mean())
    # weather up to 06:00 local
    w=w.copy();w['date']=w.ts_local.dt.normalize();w['h']=w.ts_local.dt.hour
    w.loc[w.temp_c<-100,'temp_c']=np.nan
    w6=w[w.h<=6].groupby('date').agg(temp6=('temp_c','last'),rain6=('rain_mm','sum')).reset_index()
    return d.merge(w6,on='date',how='left')
if __name__=='__main__':
    w=pd.read_csv(D+'weather.csv',parse_dates=['ts_local'])
    d=add_feats(build(D+'status.csv'),w)
    d.to_pickle('/tmp/pk-r5/work/train_days.pkl');print(d.describe(include='all').T.to_string())
