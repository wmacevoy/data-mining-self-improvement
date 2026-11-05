import pandas as pd, numpy as np, json, sys
from sklearn.ensemble import HistGradientBoostingClassifier as HGB
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
F=['b6','b6f','b5','capacity','y_prev1','y_roll14','y_roll60','dow','month','temp6','rain6']
CREW,STOP,OUT=8,40,90
def usable(d): return d[(d.n_off==0)&d.b6.notna()]   # label known, 06:00 reading present
def cost(d,score,thr=None):
    """per-day cost: restock top-CREW stations with score>thr; assumes a restock prevents the stockout (K4)."""
    tot=0;days=0;rows=[]
    for _,g in d.assign(sc=score).groupby('date'):
        pick=g.nlargest(CREW,'sc');
        if thr is not None: pick=pick[pick.sc>thr]
        c=STOP*len(pick)+OUT*(g.y.sum()-pick.y.sum()); rows.append(c);
    return np.mean(rows)
def fit(tr,kind):
    if kind=='hgb': m=HGB(max_iter=150,learning_rate=0.05,max_depth=3,min_samples_leaf=40,random_state=0)
    else:
        from sklearn.pipeline import make_pipeline; from sklearn.impute import SimpleImputer; from sklearn.preprocessing import StandardScaler
        m=make_pipeline(SimpleImputer(),StandardScaler(),LogisticRegression(C=0.3,max_iter=500))
    return m.fit(tr[F],tr.y)
if __name__=='__main__':
    d=pd.read_pickle('train_days.pkl');u=usable(d)
    tr=u[u.date<'2026-01-01'];va=u[u.date>='2026-01-01']
    print(len(tr),len(va),tr.y.mean(),va.y.mean())
    ledger=[]
    out={}
    def rep(name,sc,thr=None):
        r=dict(name=name,auc=roc_auc_score(va.y,sc),ap=average_precision_score(va.y,sc),cost=cost(va,sc,thr));print(r);ledger.append(r)
    nodays=va.groupby('date').y.sum().mean()*OUT; print('never restock cost/day',nodays,'stockouts/day',va.groupby('date').y.sum().mean())
    rep('persist_yesterday',va.y_prev1.fillna(0).values+1e-3*(1-va.b6f.values),0.5)
    rep('low_bikes_rule(b6<=2)',(-va.b6).values, -2.5)
    rep('low_bikes_frac',(1-va.b6f).values,None)
    for k in ['logit','hgb']:
        m=fit(tr,k);p=m.predict_proba(va[F])[:,1]
        rep(k+'_top8',p,None);rep(k+'_top8_p>.444',p,0.444)
        out[k]=p
    json.dump(ledger,open('ledger_dev.json','w'),indent=1)
    va.assign(p=out['hgb']).to_pickle('va_pred.pkl')
