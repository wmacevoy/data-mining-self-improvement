import pandas as pd, numpy as np, sys
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, average_precision_score
from build import build
df=build(); df.to_pickle('df.pkl')
df=df[(df.dow<5)&df.valid].copy()
F=['b0','b5','b6','min_0_6','off6','cap','fill6','rate28','rate_dow','prev_y','dow','temp6','rain6','month']
FN=[f for f in F if f!='month']  # month dropped: summer-only holdout, avoid leaning on season calendar
def fit(tr,feats):
    return H(max_iter=200,learning_rate=0.05,max_depth=4,min_samples_leaf=40,random_state=0).fit(tr[feats],tr.y)
def econ(d,p,cap=8,thr=40/90):
    # per day: restock top-k stations with p>thr. Assume restock prevents the stockout (optimistic).
    d=d.assign(p=p); tot=0; none=0; n=0
    for _,g in d.groupby('date'):
        pick=g[g.p>thr].nlargest(cap,'p')
        tot+=40*len(pick)+90*(g.y.sum()-pick.y.sum()); none+=90*g.y.sum(); n+=1
    return tot/n, none/n
def rep(name,d,p):
    c,n=econ(d,p)
    print(f"{name:28s} AUC {roc(d.y,p):.3f} AP {average_precision_score(d.y,p):.3f} Brier {brier_score_loss(d.y,np.clip(p,0,1)):.3f}  $/day {c:7.1f} (do-nothing {n:.1f})")
def roc(y,p): return roc_auc_score(y,p)
if __name__=='__main__':
    tr=df[df.date<'2026-04-01']; va=df[(df.date>='2026-04-01')&(df.date<'2026-07-01')]
    ho=df[df.date>='2026-07-01']
    print(len(tr),len(va),len(ho),'base rate',tr.y.mean(),va.y.mean(),ho.y.mean())
    mode=sys.argv[1] if len(sys.argv)>1 else 'val'
    if mode=='val':
        T,E=tr,va
    else:
        T,E=df[df.date<'2026-07-01'],ho
    for nm,f in (('gbm all',F),('gbm no month',FN),('gbm no hist',['b0','b5','b6','min_0_6','off6','cap','fill6','dow','temp6','rain6'])):
        m=fit(T,f); rep(nm,E,m.predict_proba(E[f])[:,1])
    rep('rule: b6<=k best',E,np.clip(1-E.b6.fillna(E.b6.median())/10,0,1))
    rep('trailing rate28',E,E.rate28.fillna(T.y.mean()))
    rep('prev_y',E,E.prev_y.fillna(0))
    rep('const base',E,np.full(len(E),T.y.mean()))
