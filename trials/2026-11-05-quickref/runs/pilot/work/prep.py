import pandas as pd,numpy as np
D='/tmp/pk-pilot/data/'
def load(path):
    s=pd.read_csv(path,parse_dates=['ts'])
    s=s.drop_duplicates(['ts','station_id'],keep='last')
    s['loc']=s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Denver').dt.tz_localize(None)
    return s
def build(path):
    s=load(path)
    s['date']=s['loc'].dt.normalize(); s['h']=s['loc'].dt.hour
    ok=s[s.status=='OK']
    p=ok.pivot_table(index=['station_id','date'],columns='h',values='bikes_available')
    off=s[(s.h.between(7,9))].assign(o=lambda d:d.status=='OFFLINE').groupby(['station_id','date']).o.max()
    df=pd.DataFrame(index=p.index)
    df['b7']=p.get(7); df['b6']=p.get(6); df['b5']=p.get(5)
    df['y']=(p[[7,8,9]].min(axis=1)==0).astype(float).where(p[[7,8,9]].notna().any(axis=1))
    # NB label includes 7:00 reading itself (already empty at 7 counts as stockout)
    df['y_after7']=(p[[8,9]].min(axis=1)==0).astype(float)
    df['off']=off.reindex(df.index).fillna(False)
    df['prev_min']=p[[7,8,9]].min(axis=1).groupby(level=0).shift(1)  # yesterday's morning min (known)
    df['prev_y']=df.groupby(level=0).y.shift(1)
    df['prev_b7']=df.groupby(level=0).b7.shift(1)
    df['prev_eve']=p[[16,17,18,19,20,21]].min(axis=1).groupby(level=0).shift(1) if all(c in p for c in [16,21]) else np.nan
    df=df.reset_index()
    st=pd.read_csv(D+'stations.csv',parse_dates=['effective_from']).sort_values('effective_from')
    df=pd.merge_asof(df.sort_values('date'),st[['station_id','district','capacity','effective_from']],left_on='date',right_on='effective_from',by='station_id')
    df['fill']=df.b7/df.capacity
    df['dow']=df.date.dt.dayofweek; df['month']=df.date.dt.month
    w=pd.read_csv(D+'weather.csv');w['t']=pd.to_datetime(w.ts_local)
    w.loc[w.temp_c<-100,'temp_c']=np.nan
    w7=w[w.t.dt.hour==7].assign(date=lambda d:d.t.dt.normalize())[['date','temp_c','rain_mm']].rename(columns={'temp_c':'t7','rain_mm':'r7'})
    wd=w[w.t.dt.hour.between(7,9)].assign(date=lambda d:d.t.dt.normalize()).groupby('date').rain_mm.sum().rename('rain79').reset_index()
    df=df.merge(w7,on='date',how='left').merge(wd,on='date',how='left')
    df['wkday']=df.dow<5
    return df.sort_values(['station_id','date']).reset_index(drop=True)
