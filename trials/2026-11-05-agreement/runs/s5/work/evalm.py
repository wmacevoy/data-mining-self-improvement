import json, sys, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss

F = ['bikes6','bikes3','bikes0','night_min','offline6','capacity','fill6','temp6','rain_pre','dow','month','rate14','rate60','dist_North','dist_East']
FOLDS = [('2025-10-01','2026-01-01'),('2026-01-01','2026-04-01'),('2026-04-01','2026-07-01')]
CAP=8; P_THR=40/90

def models(seed):
    return {'logit': make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000)),
            'hgb': H(max_iter=200, learning_rate=0.05, max_depth=4, min_samples_leaf=40, random_state=seed)}

def net_value(day, p):
    """per day: visit stations with p>40/90, at most 8, highest p first. Assumes a visit prevents the stockout.
    value = $90*caught - $40*visits  (vs. doing nothing)"""
    tot=0; n=0
    for _, g in day.assign(p=p).groupby('date'):
        top = g.sort_values('p', ascending=False).head(CAP); top = top[top.p > P_THR]
        tot += 90*top.y.sum() - 40*len(top); n+=1
    return tot/n

def run(d, ledger):
    d = d[d.known]; out = {}
    for lo, hi in FOLDS:
        tr = d[d.date < lo]; te = d[(d.date >= lo) & (d.date < hi)]
        preds = {'base_rate14': te.rate14.fillna(tr.y.mean()).values,
                 'rule_bikes6<=2': ((te.bikes6 <= 2).astype(float)).values}
        for name in ('logit','hgb'):
            ps = []
            for seed in range(5):
                m = models(seed)[name]; m.fit(tr[F], tr.y); ps.append(m.predict_proba(te[F])[:,1])
                if name=='logit': break
            preds[name] = np.mean(ps,axis=0)
        for k,p in preds.items():
            r = dict(fold=hi, model=k, n=len(te), base=te.y.mean(), auc=roc_auc_score(te.y,p), brier=brier_score_loss(te.y,np.clip(p,0,1)), value_per_day=net_value(te,p))
            ledger.append(r); out[(hi,k)] = r
    return out
if __name__=='__main__':
    d = pd.read_pickle('dev.pkl'); L=[]; run(d,L)
    pd.DataFrame(L).to_csv('ledger.csv', index=False)
    print(pd.DataFrame(L).round(3).to_string())
