import sys, json, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier as H
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
FE=['cap','b0','b3','b5','b6','last','off6','frac','y_l1','y_l7m','y_l28m','dow','month','sid']
def prep(f):
    f=f[(f.dow<5)&f.y.notna()].copy(); f['sid']=f.station_id.str[1:].astype(int); return f
def fit(tr,seed=0,feats=FE):
    return H(max_iter=200,learning_rate=0.05,max_depth=4,min_samples_leaf=40,random_state=seed).fit(tr[feats],tr.y)
def value(d,p,k=8,thr=40/90):
    """net $ vs doing nothing: per day restock top-k stations with p>thr; assumes a restock prevents the stockout."""
    d=d.assign(p=p); tot=0;n=0
    for _,g in d.groupby('date'):
        t=g[g.p>thr].nlargest(k,'p'); tot+=90*t.y.sum()-40*len(t); n+=1
    return tot/n
def base_value(d,k=8): # oracle & naive
    return None
def report(name,d,p):
    d=d.assign(p=p)
    return dict(name=name,auc=roc_auc_score(d.y,p) if np.ptp(p)>0 else .5,brier=brier_score_loss(d.y,np.clip(p,0,1)),value_per_day=value(d,p),
      stockouts_per_day=d.groupby('date').y.sum().mean())
def baselines(tr,te):
    st=tr.groupby('station_id').y.mean(); dm=tr.groupby(['station_id','dow']).y.mean()
    return {'station_rate':te.station_id.map(st).fillna(tr.y.mean()).values,
            'yesterday':te.y_l1.fillna(0).values,'last28':te.y_l28m.fillna(0).values,
            'b6_zero_or_low':(te['last']<=2).astype(float).values}
if __name__=='__main__':
    f=prep(pd.read_pickle('train.pkl'))
    rows=[]
    for a,b in [('2025-07-01','2025-10-01'),('2025-10-01','2026-01-01'),('2026-01-01','2026-04-01'),('2026-04-01','2026-07-02')]:
        tr=f[f.date<a]; te=f[(f.date>=a)&(f.date<b)]
        m=fit(tr); p=m.predict_proba(te[FE])[:,1]
        r=[report('gbm',te,p)]+[report(k,te,v) for k,v in baselines(tr,te).items()]
        for x in r: x['fold']=a; rows.append(x)
        print(a,len(tr),len(te),flush=True)
    R=pd.DataFrame(rows); print(R.round(3).to_string()); print(R.groupby('name')[['auc','brier','value_per_day']].mean().round(3))
    R.to_csv('dev_results.csv',index=False)
