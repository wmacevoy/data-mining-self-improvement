import pandas as pd, numpy as np
D='/tmp/pk-s7/data/'
s=pd.read_csv(D+'status.csv',parse_dates=['ts'])
s=s.drop_duplicates(['ts','station_id'],keep='first')   # 52 DST-fold duplicates
s['loc']=s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Denver').dt.tz_localize(None)  # controller clock is UTC
s['date']=s['loc'].dt.normalize(); s['h']=s['loc'].dt.hour
s.loc[s.status!='OK',['bikes_available','docks_available']]=np.nan   # OFFLINE 0s are sentinels
p=s.pivot_table(index=['station_id','date'],columns='h',values='bikes_available',aggfunc='first')
p.columns=[f'b{c}' for c in p.columns]; p=p.reset_index()
st=pd.read_csv(D+'stations.csv',parse_dates=['effective_from']).sort_values('effective_from')
p=p.sort_values('date')
p=pd.merge_asof(p,st[['station_id','district','capacity','effective_from']],left_on='date',right_on='effective_from',by='station_id')
w=pd.read_csv(D+'weather.csv',parse_dates=['ts_local']); w.loc[w.temp_c<-90,'temp_c']=np.nan
w['date']=w.ts_local.dt.normalize(); w['h']=w.ts_local.dt.hour
wp=w[w.h==6].set_index('date')[['temp_c','rain_mm']]   # 6am: safely known at 7am
p=p.join(wp,on='date')
p['dow']=p.date.dt.dayofweek
p=p[p.dow<5].copy()
p['y']=((p.b8==0)|(p.b9==0)).astype(float).where(p.b8.notna()&p.b9.notna())
p['b7_frac']=p.b7/p.capacity; p['b6_frac']=p.b6/p.capacity
p['d67']=p.b7-p.b6; p['d56']=p.b6-p.b5
p['night_min']=p[['b0','b1','b2','b3','b4','b5']].min(axis=1)
p=p.sort_values(['station_id','date'])
g=p.groupby('station_id').y
p['prior_rate']=g.transform(lambda x:x.shift(1).expanding().mean())   # strictly earlier days
p['prior_rate28']=g.transform(lambda x:x.shift(1).rolling(28,min_periods=5).mean())
p['y_prev']=g.shift(1)
p.to_pickle('/tmp/pk-s7/work/feat.pkl')
print(len(p),p.y.mean(),p.y.isna().sum(),p.b7.isna().sum(),p.date.min(),p.date.max())
print(p.groupby('station_id').y.mean().round(2).describe())
