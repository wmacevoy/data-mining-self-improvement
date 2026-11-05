import pandas as pd,numpy as np
from sklearn.metrics import roc_auc_score
from model import decide,log
v=pd.read_pickle('val_pred.pkl'); r=pd.read_pickle('dev.pkl')
v['e7']=(v.b7==0)
print('positives',v.label.sum(),'already 0 at 7:',v[v.label==1].e7.sum(),'7am offline',v.off7.sum())
n=v[~v.e7]; print('not-empty-at-7 subset: n',len(n),'rate',n.label.mean(),'auc',roc_auc_score(n.label,n.p))
print('decide on all',decide(v,v.p.values)); 
# harder: only count stations not already empty at 7 (empty-at-7 ones still get a stop)
# bootstrap by day
days=v.date.unique(); rng=np.random.default_rng(0)
per=v.assign(s=v.p).groupby('date').apply(lambda g:(lambda c:90*c.label.sum()-40*len(c))(g[g.s>40/130].nlargest(8,'s'))).values
bs=[rng.choice(per,len(per)).mean() for _ in range(2000)]
print('usd/day %.0f CI %.0f..%.0f over %d days'%(per.mean(),*np.percentile(bs,[2.5,97.5]),len(per)))
print('days with net loss',(per<0).mean(),'worst',per.min())
# calibration shift 2025 vs 2026 and days with >8 candidates
print('days where >8 stations above thr',(v.groupby('date').p.apply(lambda s:(s>40/130).sum())>8).mean())
# stability across split: train through 2025-09, val 2025-10..12
