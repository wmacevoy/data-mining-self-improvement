import numpy as np, pandas as pd
from evalm import *
from sklearn.inspection import permutation_importance
d=pd.read_pickle('dev.pkl'); d=d[d.known]
tr=d[d.date<'2026-04-01']; te=d[d.date>='2026-04-01']
m=models(0)['hgb'].fit(tr[F],tr.y); p=m.predict_proba(te[F])[:,1]; te=te.assign(p=p)
pi=permutation_importance(m,te[F],te.y,scoring='roc_auc',n_repeats=3,random_state=0)
print(sorted(zip(pi.importances_mean.round(3),F))[::-1][:6])
# feature-free-of-history: drop bikes6/3/0 etc
F2=[f for f in F if not f.startswith('bikes') and f not in('night_min','fill6')]
m2=models(0)['hgb'].fit(tr[F2],tr.y); print('no-bike-state AUC',roc_auc_score(te.y,m2.predict_proba(te[F2])[:,1]))
# slices
for c in ('district','capacity'):
    print(te.groupby(c).apply(lambda g: pd.Series(dict(n=len(g),base=g.y.mean(),auc=roc_auc_score(g.y,g.p) if g.y.nunique()>1 else np.nan,pmean=g.p.mean()))).round(3))
# station-version slice: capacity changed since 2025-09 (moved/rebuilt)
chg=te.station_id.isin(['S001','S005','S009','S013','S017','S021','S025','S029'])
print('changed',te[chg].y.mean(),te[chg].p.mean(),roc_auc_score(te[chg].y,te[chg].p),'| others',te[~chg].y.mean(),te[~chg].p.mean())
# precision at threshold / counts per day
sel=te[te.p>P_THR]; print('flagged/day',len(sel)/te.date.nunique(),'precision',sel.y.mean(),'recall',sel.y.sum()/te.y.sum(),'stockouts/day',te.y.sum()/te.date.nunique())
g=te.groupby('date'); print('days with >8 flagged',(g.p.apply(lambda x:(x>P_THR).sum())>8).mean())
# calibration
te['bin']=pd.cut(te.p,[0,.1,.3,.44,.7,.9,1]); print(te.groupby('bin',observed=True).y.agg(['mean','size']).round(3))
# oracle value
print('oracle/day', np.mean([ (90-40)*min(8,x) for x in g.y.sum()]))
# trace worst misses
print(te.assign(err=(te.y-te.p).abs()).nlargest(5,'err')[['station_id','date','bikes6','night_min','capacity','p','y']])
