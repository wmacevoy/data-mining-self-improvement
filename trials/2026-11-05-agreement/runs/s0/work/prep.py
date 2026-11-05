"""Build one row per station-day (local weekdays): target + features knowable at 06:00 local.
Usage: python -I prep.py <status.csv> <out.csv>   (holdout is NOT touched by dev scripts)"""
import sys, pandas as pd, numpy as np
D='/tmp/pk-s0/data/'
def build(status_path):
    s=pd.read_csv(status_path,parse_dates=['ts'])
    s=s.drop_duplicates(['ts','station_id'],keep='first')  # DST-repeat rows are identical-ish; keep first
    s['loc']=s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Denver').dt.tz_localize(None)
    s['date']=s['loc'].dt.normalize(); s['h']=s['loc'].dt.hour
    s['off']=(s.status=='OFFLINE')
    s['bk']=s.bikes_available.where(~s.off)   # OFFLINE zeros are not observations
    st=pd.read_csv(D+'stations.csv',parse_dates=['effective_from']).sort_values('effective_from')
    s=pd.merge_asof(s.sort_values('loc'),st[['station_id','capacity','district','effective_from']],left_on='loc',right_on='effective_from',by='station_id')
    s['frac']=s.bk/s.capacity
    wd=s[s.date.dt.dayofweek<5]
    tgt=wd[wd.h.between(7,9)].groupby(['station_id','date']).agg(n_obs=('bk','count'),empty=('bk',lambda x:(x==0).any()),n_off=('off','sum')).reset_index()
    p=s.pivot_table(index=['station_id','date'],columns='h',values='frac')
    f=p[[0,3,6]].rename(columns=lambda h:f'frac_h{h}').reset_index()
    cap=s[s.h==6].groupby(['station_id','date']).capacity.first().rename('capacity').reset_index()
    f=f.merge(cap,how='left')
    f['min_ovn']=p[[0,1,2,3,4,5,6]].min(axis=1).values
    # history: previous days' morning-peak outcomes (all fully in the past by 07:00 today)
    m=s[s.h.between(7,9)].groupby(['station_id','date']).agg(e=('bk',lambda x:float((x==0).any())),mn=('frac','min')).reset_index().sort_values(['station_id','date'])
    g=m.groupby('station_id')
    m['empty_lag1']=g.e.shift(1); m['rate_prev14']=g.e.transform(lambda x:x.shift(1).rolling(14,min_periods=3).mean())
    m['rate_prev60']=g.e.transform(lambda x:x.shift(1).rolling(60,min_periods=10).mean())
    m['minfrac_prev14']=g.mn.transform(lambda x:x.shift(1).rolling(14,min_periods=3).mean())
    # NB shift is by row, so a skipped weekend day is fine: "previous weekday"
    d=tgt.merge(f,how='left').merge(m.drop(columns=['e','mn']),how='left')
    w=pd.read_csv(D+'weather.csv',parse_dates=['ts_local']); w.loc[w.temp_c<-100,'temp_c']=np.nan
    w['date']=w.ts_local.dt.normalize(); w['h']=w.ts_local.dt.hour
    w6=w[w.h==6].groupby('date').agg(temp6=('temp_c','first'))
    r=w[w.h<=6].groupby('date').rain_mm.sum().rename('rain_ovn')
    pr=w[(w.h>=7)&(w.h<=22)].assign(date=lambda x:x.date+pd.Timedelta(days=1)).groupby('date').rain_mm.sum().rename('rain_prevday')
    d=d.merge(w6,on='date',how='left').merge(r,on='date',how='left').merge(pr,on='date',how='left')
    d['dow']=d.date.dt.dayofweek; d['month']=d.date.dt.month
    d['district']=d.station_id.map(st.drop_duplicates('station_id').set_index('station_id').district)
    return d
if __name__=='__main__':
    d=build(sys.argv[1]); d.to_csv(sys.argv[2],index=False); print(d.shape)
