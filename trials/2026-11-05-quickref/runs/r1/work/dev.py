import pandas as pd,numpy as np
from evalh import *
d=pd.read_pickle('dev.pkl');d=d[(d.dow<5)&d.stockout.notna()].reset_index(drop=True)
tr=d[d.date<'2026-01-01'];va=d[d.date>='2026-01-01'].reset_index(drop=True)
print(len(tr),len(va),tr.stockout.mean(),va.stockout.mean())
rows=[];P={}
for k in ['none','yesterday','rate28','rule_b06','logit','gbm']:
    P[k]=fit_predict(tr,va,k);rows.append(report(k,va,P[k]))
print(pd.DataFrame(rows).round(3).to_string())
# seeds spread gbm
print([round(roc_auc_score(va.stockout,fit_predict(tr,va,'gbm',s)),4) for s in range(5)])
# slices: capacity changed stations / district
va['p']=P['gbm']
for c in ['district']:
    print(va.groupby(c).apply(lambda g:pd.Series(dict(n=len(g),rate=g.stockout.mean(),auc=roc_auc_score(g.stockout,g.p)))).round(3))
print(va.groupby(va.date.dt.month).apply(lambda g:pd.Series(dict(rate=g.stockout.mean(),pred=g.p.mean(),auc=roc_auc_score(g.stockout,g.p)))).round(3))
