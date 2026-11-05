# usage: python -I predict.py YYYY-MM-DD  -> fits on labeled days strictly before that date, ranks stations by P(stockout 8-9am)
# Reads work/feat.pkl (built by build.py). Uses only data known at 7:00 local on that date.
import sys, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier as H
p=pd.read_pickle('feat.pkl'); day=pd.Timestamp(sys.argv[1])
F=['b7','b6','b5','b7_frac','d67','d56','night_min','capacity','temp_c','rain_mm','dow','prior_rate','prior_rate28','y_prev','sid']
p['sid']=p.station_id.str[1:].astype(int)
tr=p[(p.date<day)&p.y.notna()]; te=p[p.date==day]
m=H(max_iter=200,learning_rate=0.05,max_depth=4,random_state=0,categorical_features=[F.index('sid')]).fit(tr[F],tr.y)
te=te.assign(p_stockout=m.predict_proba(te[F])[:,1]).sort_values('p_stockout',ascending=False)
print(te[['station_id','b7','p_stockout']].head(8).to_string(index=False))
print('others above break-even 0.44:',(te.p_stockout.iloc[8:]>0.444).sum())
