"""Build one row per (station, weekday) as of 07:00 America/Denver. Reads only data/ (never data/holdout)."""
import pandas as pd, numpy as np
D='/tmp/pk-s4/data/'
def load():
    s=pd.read_csv(D+'status.csv',parse_dates=['ts'])
    # controller clock is UTC (nightly reset lands at local midnight in both DST regimes);
    # 52 duplicate (ts,station) rows on the two spring-forward days: keep the last.
    n0=len(s); s=s.drop_duplicates(['ts','station_id'],keep='last')
    s['loc']=s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Denver').dt.tz_localize(None)
    s['date']=s['loc'].dt.normalize(); s['h']=s['loc'].dt.hour
    s.loc[s.status!='OK',['bikes_available','docks_available']]=np.nan  # OFFLINE zeros are not stockouts
    w=pd.read_csv(D+'weather.csv',parse_dates=['ts_local'])
    w.loc[w.temp_c<-100,'temp_c']=np.nan  # -999 sentinel
    st=pd.read_csv(D+'stations.csv',parse_dates=['effective_from']).sort_values('effective_from')
    return s,w,st
def build(s,w,st):
    s=s[s.date.dt.dayofweek<5]
    p=s.pivot_table(index=['station_id','date'],columns='h',values='bikes_available',aggfunc='last',dropna=False)
    off=s.assign(o=(s.status!='OK')).pivot_table(index=['station_id','date'],columns='h',values='o',aggfunc='max')
    df=pd.DataFrame(index=p.index)
    # label: OK reading of 0 bikes at local 07,08,09; NaN if no OK reading in window
    win=p[[7,8,9]]
    df['y']=np.where(win.notna().any(axis=1),(win==0).any(axis=1).astype(float),np.nan)
    # features: strictly before 07:00 local (reading at 06:00 is the latest)
    df['b6']=p[6]; df['b5']=p[5]; df['b0']=p[0]
    df['d6']=p[6]-p[3]
    df['off_pre']=off[[0,1,2,3,4,5,6]].sum(axis=1)
    df=df.reset_index().sort_values(['station_id','date'])
    # as-of capacity
    cap=[]
    for sid,g in df.groupby('station_id'):
        c=st[st.station_id==sid][['effective_from','capacity']]
        cap.append(pd.merge_asof(g.sort_values('date'),c,left_on='date',right_on='effective_from')['capacity'].set_axis(g.index))
    df['cap']=pd.concat(cap); df['f6']=df.b6/df.cap
    # trailing history, shifted so only previous days count
    g=df.groupby('station_id')
    df['y_prev']=g.y.shift(1)
    df['rate28']=g.y.transform(lambda x:x.shift(1).rolling(28,min_periods=5).mean())
    df['mb6_28']=g.f6.transform(lambda x:x.shift(1).rolling(28,min_periods=5).mean())
    df['dow']=df.date.dt.dayofweek; df['month']=df.date.dt.month
    ww=w.set_index('ts_local'); df['t6']=ww.temp_c.reindex(df.date+pd.Timedelta(hours=6)).values
    df['rain6']=ww.rain_mm.reindex(df.date+pd.Timedelta(hours=6)).values
    df['rain_prev3']=[ww.rain_mm.get(t,np.nan) for t in df.date+pd.Timedelta(hours=6)]  # placeholder replaced below
    df=df.drop(columns='rain_prev3')
    return df
if __name__=='__main__':
    s,w,st=load(); df=build(s,w,st); df.to_pickle('/tmp/pk-s4/work/rows.pkl')
    print(len(df),df.y.isna().sum(),df.y.mean(), df.isna().sum().to_dict())
    print(df.groupby(df.date.dt.to_period('M')).y.agg(['mean','count']).T.round(2).to_string())
