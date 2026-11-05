import pandas as pd, numpy as np
D='/tmp/pk-r4/data/'
def load(p):
    s=pd.read_csv(p,parse_dates=['ts']).drop_duplicates(['ts','station_id'],keep='last')
    s['loct']=s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Denver').dt.tz_localize(None)
    s['date']=s.loct.dt.normalize(); s['h']=s.loct.dt.hour
    return s
def weather():
    w=pd.read_csv(D+'weather.csv',parse_dates=['ts_local']);w.loc[w.temp_c<-100,'temp_c']=np.nan
    return w.rename(columns={'ts_local':'lt'}).set_index('lt')
def build(s,w,cap):
    ok=s[s.status=='OK']
    # label: any OK reading with 0 bikes at local 7,8,9
    tgt=ok[ok.h.between(7,9)].groupby(['station_id','date']).bikes_available.min().rename('minb').reset_index()
    tgt['y']=(tgt.minb==0).astype(int)
    # features from readings at local 00..06 only
    p=s[s.h<=6].copy()
    p['b']=p.bikes_available.where(p.status=='OK')
    g=p.groupby(['station_id','date'])
    f=g.b.agg(b0='first').join(g.b.last().rename('b6')).join(g.b.min().rename('bmin')).join(g.status.apply(lambda x:(x=='OFFLINE').sum()).rename('off_n'))
    f=f.reset_index()
    f['b5']=p[p.h==5].set_index(['station_id','date']).b.reindex(pd.MultiIndex.from_frame(f[['station_id','date']])).values
    f['b1']=p[p.h==1].set_index(['station_id','date']).b.reindex(pd.MultiIndex.from_frame(f[['station_id','date']])).values
    d=tgt.merge(f,on=['station_id','date'])
    d['cap']=[cap(a,b) for a,b in zip(d.station_id,d.date)]
    d['fill']=d.b6/d.cap
    d['dow']=d.date.dt.dayofweek; d['month']=d.date.dt.month
    ww=w[w.index.hour<=6].groupby(w[w.index.hour<=6].index.normalize()).agg(t6=('temp_c','last'),rain_n=('rain_mm','sum'))
    d=d.join(ww,on='date')
    return d
def capfn():
    st=pd.read_csv(D+'stations.csv',parse_dates=['effective_from']).sort_values('effective_from')
    m={k:g for k,g in st.groupby('station_id')}
    def cap(sid,date):
        g=m[sid];g=g[g.effective_from<=date];return g.capacity.iloc[-1] if len(g) else g.capacity.iloc[0] if False else m[sid].capacity.iloc[0]
    return cap
