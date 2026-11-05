"""Train on all pre-holdout data (5 seeds), save model.pkl.
Sign-off (ONE look, human-run, log it): python -I prep.py ../data ../data/holdout/status_2026Q3.csv holdout_feat.csv
  then python -I final.py score holdout_feat.csv   -- NOTE: rate28/yprev for the holdout need Q2 history, so
  concatenate the status files before prep (see REPORT.md)."""
import sys, pickle, pandas as pd, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier as H
F = ['capacity','b0_f','b3_f','b5_f','b6_f','b6','prev_min_day','prev_b18','yprev','rate28','rate_all','dow','month','temp6','rain_to6','rain_prev_day','dist']
def load(p):
    d=pd.read_csv(p,parse_dates=['date']); d['dist']=d.district.map({'Central':0,'East':1,'North':2}); return d
if sys.argv[1]=='train':
    d=load(sys.argv[2]).dropna(subset=['y']); d=d[d.date<'2026-07-01']
    ms=[H(max_iter=200,learning_rate=0.05,max_depth=4,random_state=s).fit(d[F],d.y) for s in range(5)]
    pickle.dump(ms,open('model.pkl','wb')); print('trained on',len(d))
else:
    d=load(sys.argv[2]); ms=pickle.load(open('model.pkl','rb'))
    d['p']=np.mean([m.predict_proba(d[F])[:,1] for m in ms],axis=0)
    for dt,g in d.groupby('date'): print(dt.date(), g.nlargest(8,'p')[['station_id','p']].values.tolist())
