import pandas as pd, numpy as np
D='/tmp/pk-r3/data/'
def load(p):
    s=pd.read_csv(p,parse_dates=['ts']).drop_duplicates(['ts','station_id'],keep='last')
    s['loc']=s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Denver').dt.tz_localize(None)
    s['date']=s['loc'].dt.normalize(); s['h']=s['loc'].dt.hour
    return s
def cap_table():
    c=pd.read_csv(D+'stations.csv',parse_dates=['effective_from']).sort_values('effective_from'); return c
def build(s):
    c=cap_table()
    s=s.sort_values('loc'); 
    s=pd.merge_asof(s,c[['station_id','capacity','effective_from','district']],left_on='loc',right_on='effective_from',by='station_id')
    ok=s.status=='OK'
    s['bk']=s.bikes_available.where(ok)  # OFFLINE zeros are not observations
    p=s.pivot_table(index=['station_id','date'],columns='h',values='bk',aggfunc='last',dropna=False)
    # label: bikes==0 at an OK reading at 7,8,9 local
    lab=(p[[7,8,9]]==0).any(axis=1); known=p[[7,8,9]].notna().any(axis=1)
    cap=s.groupby(['station_id','date']).capacity.last()
    dist=s.groupby('station_id').district.last()
    f=pd.DataFrame(index=p.index)
    f['y']=lab.astype(float).where(known)
    f['n_known']=p[[7,8,9]].notna().sum(axis=1)
    f['cap']=cap
    # features knowable at 07:00: readings up to 06:00 local same day, plus past days' outcomes
    f['b0']=p[0];f['b3']=p[3];f['b5']=p[5];f['b6']=p[6]
    f['last']=p[[0,1,2,3,4,5,6]].ffill(axis=1)[6]
    f['off6']=p[6].isna().astype(int)
    f['frac']=f['last']/f['cap']
    f=f.reset_index(); f['district']=f.station_id.map(dist)
    f=f.sort_values(['station_id','date'])
    g=f.groupby('station_id')
    f['y_l1']=g.y.shift(1); 
    f['y_l7m']=g.y.transform(lambda x:x.shift(1).rolling(7,min_periods=3).mean())
    f['y_l28m']=g.y.transform(lambda x:x.shift(1).rolling(28,min_periods=7).mean())
    f['dow']=f.date.dt.dayofweek; f['month']=f.date.dt.month
    return f
