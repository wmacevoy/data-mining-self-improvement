import pandas as pd, numpy as np
D='/tmp/pk-r9/data/'
DST=[('2025-03-09 02:00','2025-11-02 01:00'),('2026-03-08 02:00','2026-11-01 01:00')]
def load(f):
    s=pd.read_csv(D+f,parse_dates=['ts'])
    s=s.drop_duplicates(['ts','station_id'],keep='last')  # DST-dup rows
    off=pd.Series(pd.Timedelta(0),index=s.index)
    for a,b in DST:
        off[(s.ts>=a)&(s.ts<b)]=pd.Timedelta('1h')
    s['lts']=s.ts+off   # local time (controller is standard time)
    return s
