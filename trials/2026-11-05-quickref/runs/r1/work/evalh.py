import pandas as pd,numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,brier_score_loss,average_precision_score
from prep import FEATS
C_TRUCK,C_OUT,CREW=40,90,8
def policy_cost(df,p,cap=CREW,thr=40/90):
    """Per day: restock stations with highest p, up to cap, only if p>thr. Assumes a restock prevents the stockout (K4)."""
    tot=0;n=0;visits=0;prevented=0
    for _,g in df.assign(p=p).groupby('date'):
        g=g.sort_values('p',ascending=False)
        pick=g[g.p>thr].head(cap)
        tot+=C_TRUCK*len(pick)+C_OUT*(g.stockout.sum()-pick.stockout.sum()); visits+=len(pick);prevented+=pick.stockout.sum();n+=1
    return dict(cost_per_day=tot/n,visits=visits/n,caught=prevented/df.stockout.sum())
def report(name,df,p):
    r=dict(model=name,auc=roc_auc_score(df.stockout,p),ap=average_precision_score(df.stockout,p),brier=brier_score_loss(df.stockout,np.clip(p,0,1)))
    r.update(policy_cost(df,p));return r
def boot_cost_diff(df,pa,pb,B=300,seed=0):
    rng=np.random.default_rng(seed);dates=df.date.unique();out=[]
    ca={d:policy_cost(g,pa[g.index.map(df.index.get_loc)])['cost_per_day'] for d,g in df.groupby('date')}
    cb={d:policy_cost(g,pb[g.index.map(df.index.get_loc)])['cost_per_day'] for d,g in df.groupby('date')}
    a=np.array([ca[d] for d in dates]);b=np.array([cb[d] for d in dates])
    for _ in range(B):
        i=rng.integers(0,len(dates),len(dates));out.append((a[i]-b[i]).mean())
    return np.percentile(out,[2.5,50,97.5])
def fit_predict(tr,te,kind,seed=0):
    if kind=='gbm':
        m=H(max_iter=200,learning_rate=0.05,max_depth=4,random_state=seed).fit(tr[FEATS],tr.stockout);return m.predict_proba(te[FEATS])[:,1]
    if kind=='logit':
        X=lambda d:d[['b06_frac','b06','capacity','so_rate28','aft_min']].fillna(d[['b06_frac','b06','capacity','so_rate28','aft_min']].median())
        med=tr[['b06_frac','b06','capacity','so_rate28','aft_min']].median()
        Xt=lambda d:d[['b06_frac','b06','capacity','so_rate28','aft_min']].fillna(med)
        m=LogisticRegression(max_iter=2000,C=1).fit(Xt(tr),tr.stockout);return m.predict_proba(Xt(te))[:,1]
    if kind=='rate28': return te.so_rate28.fillna(tr.stockout.mean()).values
    if kind=='yesterday': return te.prev_so.fillna(0).values.astype(float)
    if kind=='rule_b06': return (te.b06.fillna(0)<=3).astype(float).values
    if kind=='none': return np.zeros(len(te))
