"""Build one row per (station, local weekday). Clock: controller ts is UTC (see REPORT); local = America/Los_Angeles.
Features use only readings with local time < 07:00 on the day (prediction point 07:00)."""
import pandas as pd, numpy as np, sys
D='/tmp/pk-r6/data/'
def load_status(paths):
    s=pd.concat([pd.read_csv(p,parse_dates=['ts']) for p in paths])
    s=s.drop_duplicates(['ts','station_id'],keep='first')  # DST-day dups; first kept
    s['loc']=s.ts.dt.tz_localize('UTC').dt.tz_convert('America/Los_Angeles').dt.tz_localize(None)
    s['date']=s['loc'].dt.normalize(); s['lh']=s['loc'].dt.hour
    return s
def caps():
    c=pd.read_csv(D+'stations.csv',parse_dates=['effective_from']).sort_values('effective_from')
    return c[['station_id','capacity','effective_from']]
def build(paths):
    s=load_status(paths)
    # label: OK reading with 0 bikes at local 7,8,9 ; unknown if any OFFLINE and no zero seen
    w=s[s.lh.isin([7,8,9])]
    g=w.groupby(['station_id','date'])
    lab=pd.DataFrame({'stockout':g.apply(lambda x:int(((x.status=='OK')&(x.bikes_available==0)).any())),
                      'win_offline':g.apply(lambda x:int((x.status=='OFFLINE').any())),
                      'win_n':g.size()}).reset_index()
    # features from local hours <7
    p=s[s.lh<7].copy()
    p['b']=p.bikes_available.where(p.status=='OK')
    pv=p.pivot_table(index=['station_id','date'],columns='lh',values='b',aggfunc='first')
    pv.columns=[f'b{h}' for h in pv.columns]; pv=pv.reset_index()
    pv['n_off_pre']=p.groupby(['station_id','date']).status.apply(lambda x:(x=='OFFLINE').sum()).values if False else 0
    df=lab.merge(pv,on=['station_id','date'],how='left')
    df=df.sort_values(['station_id','date'])
    # capacity as-of date
    df=pd.merge_asof(df.sort_values('date'),caps().sort_values('effective_from'),left_on='date',right_on='effective_from',by='station_id').sort_values(['station_id','date'])
    # prior-day history (strictly before today): yesterday's window outcome, rolling rates
    df['lab_known']=((df.stockout==1)|(df.win_offline==0)).astype(int)
    y=df.stockout.where(df.lab_known==1)
    gs=df.groupby('station_id')
    df['prev_so']=y.groupby(df.station_id).shift(1)
    df['rate7']=y.groupby(df.station_id).transform(lambda x:x.shift(1).rolling(7,min_periods=3).mean())
    df['rate28']=y.groupby(df.station_id).transform(lambda x:x.shift(1).rolling(28,min_periods=7).mean())
    df['fill6']=df.b6/df.capacity
    df['dow']=df.date.dt.dayofweek; df['month']=df.date.dt.month
    # weather (local naive), hours <7 only
    wx=pd.read_csv(D+'weather.csv',parse_dates=['ts_local']); wx.loc[wx.temp_c<-100,'temp_c']=np.nan
    wx['date']=wx.ts_local.dt.normalize(); wx['h']=wx.ts_local.dt.hour
    pre=wx[wx.h<7].groupby('date').agg(temp6=('temp_c','last'),rain_pre=('rain_mm','sum')).reset_index()
    df=df.merge(pre,on='date',how='left')
    # trucks: a visit yesterday (log clock = controller UTC -> local date)
    r=pd.read_csv(D+'rebalancing_log.csv',parse_dates=['ts'])
    r['date']=r.ts.dt.tz_localize('UTC').dt.tz_convert('America/Los_Angeles').dt.tz_localize(None).dt.normalize()
    rv=set(zip(r.station_id,r.date))
    df['visit_prev']=[int((a,d-pd.Timedelta(days=1)) in rv) for a,d in zip(df.station_id,df.date)]
    return df
if __name__=='__main__':
    tr=build([D+'status.csv']); tr.to_pickle('train.pkl')
    print(tr.shape, tr.stockout.mean(), tr.win_offline.mean(), tr.win_n.value_counts().to_dict())
