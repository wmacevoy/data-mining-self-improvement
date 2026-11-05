import numpy as np, pandas as pd, pickle
from evalm import *
d=pd.read_pickle('dev.pkl'); d=d[d.known]
te=d[d.date>='2026-04-01']; tr=d[d.date<'2026-04-01']
# seed spread (hgb) on last fold, value/day
vals=[];aucs=[]
for s in range(5):
    p=models(s)['hgb'].fit(tr[F],tr.y).predict_proba(te[F])[:,1]; vals.append(net_value(te,p)); aucs.append(roc_auc_score(te.y,p))
print('seed value',np.round(vals,0),'auc',np.round(aucs,3))
# day-bootstrap CI of value/day and of gain over best baseline (rule bikes6<=2)
p=np.mean([models(s)['hgb'].fit(tr[F],tr.y).predict_proba(te[F])[:,1] for s in range(5)],axis=0)
te=te.assign(p=p, r=(te.bikes6<=2).astype(float))
def day_vals(col):
    o={}
    for dt,g in te.groupby('date'):
        t=g.sort_values(col,ascending=False).head(8); t=t[t[col]>(P_THR if col=='p' else .5)]
        o[dt]=90*t.y.sum()-40*len(t)
    return pd.Series(o)
a,b=day_vals('p'),day_vals('r'); rng=np.random.default_rng(0)
bs=[(a.iloc[i].mean(),(a-b).iloc[i].mean()) for i in (rng.integers(0,len(a),len(a)) for _ in range(2000))]
print('model/day',a.mean(),np.percentile([x[0] for x in bs],[2.5,97.5]),'gain vs rule',(a-b).mean(),np.percentile([x[1] for x in bs],[2.5,97.5]))
print('share of stockouts already empty/offline at 6:', ((te.bikes6==0)|te.bikes6.isna())[te.y==1].mean())
pickle.dump(models(0)['hgb'].fit(d[F],d.y),open('model_dev_through_2026-06.pkl','wb'))
