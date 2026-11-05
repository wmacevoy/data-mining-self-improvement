import sys; sys.path.insert(0,'/tmp/pk-s1/work')
import prep, pandas as pd, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
FEATS=['b6','b5','b3','b0','fill6','capacity','dow','month','prev_y','prev_ymin','rate14','rate60','b6_prev','temp6','rain_to6']
SEEDS=[0,1,2,3,4]
STOP, MISS, CREW = 40, 90, 8

def fit_predict(tr, te, seed):
    m = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, random_state=seed)
    m.fit(tr[FEATS], tr.y); return m.predict_proba(te[FEATS])[:,1]

def policy_value(te, p, thr=STOP/MISS, k=CREW):
    """Net $ vs doing nothing, per day: stop at the top-k stations with p>thr; assumes a stop prevents that stockout."""
    t = te.assign(p=p)
    tot = 0.0; stops = 0
    for _, g in t.groupby('date'):
        c = g[g.p > thr].nlargest(k, 'p')
        tot += (MISS*c.y - STOP).sum(); stops += len(c)
    days = t.date.nunique()
    return tot/days, stops/days

def oracle(te):
    tot=0
    for _, g in te.groupby('date'):
        tot += MISS*min(CREW,int(g.y.sum())) - STOP*min(CREW,int(g.y.sum()))
    return tot/te.date.nunique()

def prep_split(d):
    d = d[(d.dow<5)&d.y.notna()&d.b6.notna()].copy(); return d

if __name__=='__main__':
    d = prep_split(prep.build('/tmp/pk-s1/data/status.csv'))
    folds=[('2025-07-01','2025-10-01'),('2025-10-01','2026-01-01'),('2026-01-01','2026-04-01'),('2026-04-01','2026-07-01')]
    for a,b in folds:
        tr=d[d.date<a]; te=d[(d.date>=a)&(d.date<b)]
        if len(tr)<2000: continue
        ps=np.mean([fit_predict(tr,te,s) for s in SEEDS],0)
        aucs=[roc_auc_score(te.y,fit_predict(tr,te,s)) for s in SEEDS]
        base=te.rate60.fillna(tr.y.mean()).values
        pers=1-te.b6.clip(upper=10)/10
        v,st=policy_value(te,ps); vb,sb=policy_value(te,base); vp,sp=policy_value(te,pers.values)
        print(a,len(te),'rate',round(te.y.mean(),3),'AUC',round(roc_auc_score(te.y,ps),3),'seedsd',round(np.std(aucs),4),
          'AP',round(average_precision_score(te.y,ps),3),'brier',round(brier_score_loss(te.y,ps),3),'| base AUC',round(roc_auc_score(te.y,base),3),
          'b6 AUC',round(roc_auc_score(te.y,pers),3))
        print('   $/day model',round(v,1),'stops',round(st,1),'| rate60',round(vb,1),round(sb,1),'| b6',round(vp,1),round(sp,1),'| oracle',round(oracle(te),1))
