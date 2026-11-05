import pandas as pd, numpy as np
D='/tmp/pk-r8/data/'
def load(f):
    s=pd.read_csv(f,parse_dates=['ts']).drop_duplicates(['ts','station_id'],keep='last')
    s['loc']=s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Denver').dt.tz_localize(None)
    return s
def build():
    s=pd.concat([load(D+'status.csv'),load(D+'holdout/status_2026Q3.csv')]).drop_duplicates(['ts','station_id'],keep='last')
    st=pd.read_csv(D+'stations.csv',parse_dates=['effective_from']).sort_values('effective_from')
    s=s.sort_values('loc')
    s=pd.merge_asof(s,st[['station_id','capacity','district','effective_from']].rename(columns={'effective_from':'ef'}),left_on='loc',right_on='ef',by='station_id')
    s['date']=s['loc'].dt.normalize(); s['h']=s['loc'].dt.hour
    s['ok']=(s.status=='OK')
    s['b']=s.bikes_available.where(s.ok)
    p=s.pivot_table(index=['station_id','date'],columns='h',values='b',aggfunc='first')
    off=s.pivot_table(index=['station_id','date'],columns='h',values='ok',aggfunc='first')
    df=pd.DataFrame(index=p.index)
    for h in (0,3,5,6): df[f'b{h}']=p[h]
    df['min_0_6']=p[[0,1,2,3,4,5,6]].min(axis=1)
    df['off6']=(off[6]==False).astype(int)
    df['cap']=s.groupby(['station_id','date']).capacity.last()
    df['fill6']=df.b6/df.cap
    tgt=p[[7,8,9]]; offt=off[[7,8,9]]
    df['n_obs_t']=tgt.notna().sum(axis=1)
    df['y']=(tgt==0).any(axis=1).astype(float)
    df['any_off_t']=(offt==False).any(axis=1)
    df=df.reset_index()
    # prior-day morning outcome and trailing rate (only past, lagged >=1 day)
    df=df.sort_values(['station_id','date'])
    df['valid']=(df.y==1)|(df.n_obs_t==3)
    yy=df.y.where(df.valid)
    df['yy']=yy
    g=df.groupby('station_id')
    df['prev_y']=g.yy.shift(1)
    df['rate28']=g.yy.transform(lambda x:x.shift(1).rolling(28,min_periods=7).mean())
    df['rate_dow']=df.groupby(['station_id',df.date.dt.dayofweek]).yy.transform(lambda x:x.shift(1).rolling(8,min_periods=3).mean())
    df['dow']=df.date.dt.dayofweek
    df['month']=df.date.dt.month
    w=pd.read_csv(D+'weather.csv',parse_dates=['ts_local']).replace(-999,np.nan)
    w=w.set_index('ts_local')
    w['temp_c']=w.temp_c.where(w.temp_c>-60)
    w['rain6']=w.rain_mm.rolling(6,min_periods=1).sum()
    w['temp_ma']=w.temp_c
    k=w.reindex(df.date+pd.Timedelta(hours=6))
    df['temp6']=k.temp_c.values; df['rain6']=k.rain6.values
    df['district']=df.station_id.map(st.drop_duplicates('station_id').set_index('station_id').district)
    return df
if __name__=='__main__':
    df=build(); print(df.shape); print(df.isna().sum()); print(df.groupby(df.date.dt.year).agg(n=('y','size'),y=('y','mean'),off=('any_off_t','mean')))
    print(df[df.dow<5].y.mean(), df.n_obs_t.value_counts().to_dict())
    df.to_pickle('/tmp/pk-r8/work/df.pkl')
