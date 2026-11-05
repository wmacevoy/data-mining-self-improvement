"""Build station-day table. Prediction point = 07:00 local. Features use only data with local ts <= 06:00.
Label = an OK snapshot at local 07,08,09 with bikes==0. (hourly snapshots only: sub-hour stockouts invisible)."""
import pandas as pd, numpy as np, sys
D='/tmp/pk-r2/data/'
def load(path):
    s=pd.read_csv(path,parse_dates=['ts'])
    s=s.drop_duplicates(['ts','station_id'],keep='last')   # 52 dup rows at the 2025/2026 spring-forward instant
    s['loc']=s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Denver').dt.tz_localize(None)  # ts is UTC (inferred, see REPORT)
    s['cap']=s.bikes_available+s.docks_available
    s['ok']=s.status=='OK'
    s.loc[~s.ok,'bikes_available']=np.nan
    s['date']=s['loc'].dt.normalize(); s['h']=s['loc'].dt.hour
    return s
def weather():
    w=pd.read_csv(D+'weather.csv',parse_dates=['ts_local']); w.loc[w.temp_c<=-900,'temp_c']=np.nan
    w['date']=w.ts_local.dt.normalize(); w['h']=w.ts_local.dt.hour; return w
def build(path):
    s=load(path); w=weather()
    cap=s.groupby('station_id').cap.max().rename('capmax')
    win=s[s.h.isin([7,8,9])]
    g=win.groupby(['station_id','date'])
    lab=pd.DataFrame({'zero':g.apply(lambda d:(d.ok&(d.bikes_available==0)).any()),
                      'n':g.size(),'n_off':g.apply(lambda d:(~d.ok).sum())})
    lab['y']=np.where((lab.n==3)&(lab.n_off==0),lab.zero.astype(float),np.nan)  # label only fully observed windows (East stations drop ~30% of hours at random; counting only seen zeros would inflate their rate)
    p=s.pivot_table(index=['station_id','date'],columns='h',values='bikes_available',aggfunc='last')
    f=pd.DataFrame(index=p.index)
    for h in (0,3,6): f[f'b{h}']=p[h]
    pf=p[[0,1,2,3,4,5,6]].ffill(axis=1)
    f['b_last']=pf[6]
    ob=p[[0,1,2,3,4,5,6]].notna()
    f['age_last']=6-ob.mul([0,1,2,3,4,5,6]).where(ob).max(axis=1)
    f['b6_minus_b0']=f.b6-f.b0
    f['b_min_night']=p[[0,1,2,3,4,5,6]].min(axis=1)
    cp=s[s.h==6].set_index(['station_id','date']).cap
    f['cap']=cp.reindex(f.index)
    f['frac6']=f.b6/f.cap; f['frac_last']=f.b_last/f.cap
    off=s[(s.h<=6)&~s.ok].groupby(['station_id','date']).size()
    f['off_night']=off.reindex(f.index).fillna(0)
    f=f.join(lab[['y']]).reset_index()
    f['dow']=f.date.dt.dayofweek
    ww=w[w.h<=6].groupby('date').agg(temp6=('temp_c','last'),rain_night=('rain_mm','sum'))
    f=f.merge(ww,on='date',how='left')
    f['wk']=(f.dow<5).astype(int); f['month']=f.date.dt.month
    # day before: stockout in prior morning window, known at 7am today
    f=f.sort_values(['station_id','date'])
    f['prev_y']=f.groupby('station_id').y.shift(1)   # note: only valid if consecutive day
    f['y_rate28']=f.groupby('station_id').y.transform(lambda x:x.shift(1).rolling(28,min_periods=7).mean())
    return f
if __name__=='__main__':
    a=build(D+'status.csv'); a.to_pickle('dev.pkl')
    h=build(D+'holdout/status_2026Q3.csv'); h.to_pickle('hold_features.pkl')  # not scored until sign-off
    print(a.shape,h.shape); print(a.y.isna().mean(), a.y.mean()); print(a.groupby(a.date.dt.to_period('Q')).y.agg(['mean','count']))
