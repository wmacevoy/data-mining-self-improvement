import pandas as pd, numpy as np
D='/tmp/pk-r7/data/'
def load(path):
    s=pd.read_csv(path,parse_dates=['ts'])
    s=s.drop_duplicates(['ts','station_id'],keep='last')
    # controller = US-Eastern-like standard time (no DST); local = ctrl+1h while DST in effect.
    # Evidence: morning jump is at ctrl 7 (winter) / 6 (summer), restock log hours align with this.
    # Determine DST by local-date rule: 2nd Sun Mar 02:00 -> 1st Sun Nov 02:00 (std clock).
    t=s.ts
    y=t.dt.year
    def nth_sun(y,m,n):
        d=pd.Timestamp(year=y,month=m,day=1); off=(6-d.weekday())%7; return d+pd.Timedelta(days=off+7*(n-1))
    st={yy:(nth_sun(yy,3,2)+pd.Timedelta(hours=2),nth_sun(yy,11,1)+pd.Timedelta(hours=1)) for yy in (2025,2026)}
    dst=pd.Series(False,index=s.index)
    for yy,(a,b) in st.items(): dst|=(t>=a)&(t<b)
    s['local']=t+pd.to_timedelta(dst.astype(int),unit='h')
    return s
