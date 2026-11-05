import pandas as pd, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
F=['b0','b1','b2','b3','b4','b5','b6','capacity','fill6','prev_so','rate7','rate28','dow','month','temp6','rain_pre','visit_prev']
def wk(d): return d[(d.dow<5)&(d.lab_known==1)].copy()
def fit(tr,seed=0):
    return H(max_iter=150,learning_rate=0.05,max_depth=3,min_samples_leaf=40,l2_regularization=1.0,random_state=seed).fit(tr[F],tr.stockout)
def cost(d,p,k=8,thr=40/90,col='stockout'):
    """per-day: restock up to k stations with p>thr; assume restock prevents the stockout (K4)."""
    d=d.assign(p=p); tot=0;stops=0;miss=0
    for _,g in d.groupby('date'):
        sel=g[g.p>thr].nlargest(k,'p'); stops+=len(sel)
        miss+=g.drop(sel.index)[col].sum()
    return dict(stops=stops,missed=int(miss),cost=40*stops+90*miss,none=90*d[col].sum(),days=d.date.nunique())
if __name__=='__main__':
    d=wk(pd.read_pickle('train.pkl'))
    tr=d[d.date<'2026-01-01']; va=d[d.date>='2026-01-01']
    print(len(tr),len(va),tr.stockout.mean(),va.stockout.mean())
    ps=[fit(tr,s).predict_proba(va[F])[:,1] for s in range(5)]
    p=np.mean(ps,0)
    print('AUC seeds',[round(roc_auc_score(va.stockout,q),4) for q in ps])
    base={'persist(prev_so)':va.prev_so.fillna(0).values*0.9,'b6<=3':(va.b6.fillna(0)<=3).astype(float).values,'rate28':va.rate28.fillna(0).values}
    for n,q in base.items(): print(n,roc_auc_score(va.stockout,q),cost(va,q,thr=0.4))
    print('model',roc_auc_score(va.stockout,p),brier_score_loss(va.stockout,p),cost(va,p))
    print('model no cap',cost(va,p,k=99))
    # calibration
    print(va.assign(p=p).groupby(pd.cut(p,[0,.1,.2,.3,.45,.6,.8,1])).agg(n=('p','size'),pred=('p','mean'),obs=('stockout','mean')).round(3))
    # slices
    va=va.assign(p=p)
    print(va.groupby(va.station_id>='S025').apply(lambda g:pd.Series(dict(n=len(g),auc=roc_auc_score(g.stockout,g.p),obs=g.stockout.mean(),pred=g.p.mean()))))
    print(va.groupby(va.win_n).apply(lambda g:pd.Series(dict(n=len(g),obs=g.stockout.mean(),pred=g.p.mean()))))
