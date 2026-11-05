import sys;sys.path.insert(0,'/tmp/pk-pilot/work')
import pandas as pd,numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,brier_score_loss
F=['b7','b6','b5','capacity','fill','dow','month','t7','r7','prev_min','prev_b7','prev_y']
def prep(d):
    d=d[d.wkday&d.y.notna()&d.b7.notna()].copy(); d['sid']=d.station_id.str[1:].astype(int); return d
def gbm(tr,te,feats=F+['sid']):
    m=H(max_iter=150,learning_rate=.05,max_depth=3,min_samples_leaf=40,categorical_features=[feats.index('sid')] if 'sid' in feats else None,random_state=0).fit(tr[feats],tr.y)
    return m.predict_proba(te[feats])[:,1]
def value(te,p,k=8,thr=40/90):
    te=te.assign(p=p);tot=0;n=0;caught=0
    for _,g in te.groupby('date'):
        c=g[g.p>thr].nlargest(k,'p'); tot+=90*c.y.sum()-40*len(c); n+=len(c);caught+=c.y.sum()
    return tot,n,caught
def report(name,te,p):
    d=te.date.nunique();t,n,c=value(te,p)
    print(f"{name:14s} AUC {roc_auc_score(te.y,p):.3f} brier {brier_score_loss(te.y,p):.3f} | net/day ${t/d:7.1f} stops/day {n/d:.2f} caught/day {c/d:.2f} (stockouts/day {te.y.sum()/d:.2f})")
def run(tr,te):
    base=np.full(len(te),tr.y.mean()); report('none(const)',te,base*0)
    report('rate',te,base)
    report('rule b7<=2',te,(te.b7<=2).astype(float)*.9)
    report('rule fill<.15',te,(te.fill<.15).astype(float)*.9)
    lg=LogisticRegression(max_iter=2000);X=lambda d:pd.get_dummies(d[['b7','fill','capacity','t7','r7','prev_min']].assign(m=d.month.astype(str)),dtype=float).fillna(0)
    Xt=X(tr);Xe=X(te).reindex(columns=Xt.columns,fill_value=0);report('logit',te,lg.fit(Xt,tr.y).predict_proba(Xe)[:,1])
    report('gbm',te,gbm(tr,te))
    report('gbm noSid',te,gbm(tr,te,F))
