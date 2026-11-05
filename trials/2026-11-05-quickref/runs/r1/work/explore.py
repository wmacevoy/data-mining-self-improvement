import pandas as pd,numpy as np
from prep import *
D='/tmp/pk-r1/data/'
s=load_status(D+'status.csv');st=stations(D+'stations.csv');w=pd.read_csv(D+'weather.csv')
d=build(s,st,w);d.to_pickle('dev.pkl')
print(len(d),d.stockout.isna().sum(),d.stockout.mean())
print(d.groupby(d.date.dt.to_period('Q')).stockout.agg(['mean','count']))
print(d.groupby('dow').stockout.mean().round(3).to_dict())
print(d.groupby('station_id').stockout.mean().round(3).sort_values().to_string())
print(d[['b06','b00','aft_min','temp_c']].isna().mean())
print(d.groupby(d.b06.fillna(-1).clip(-1,8)).stockout.agg(['mean','count']))
